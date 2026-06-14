import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import sqlite3
import yfinance as yf
from config import DB_PATH, TICKER_COLORS

st.set_page_config(
    page_title="거시경제 대시보드",
    page_icon="📊",
    layout="wide",
)

st.markdown("""
<style>
.main { background-color: #0F1117; }

[data-testid="metric-container"] {
    background-color: #1A1D27;
    border: 1px solid #2A2D3E;
    border-radius: 12px;
    padding: 20px 24px;
}
[data-testid="metric-container"] label {
    color: #8A8FA8 !important;
    font-size: 13px !important;
    font-weight: 400 !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    font-size: 28px !important;
    font-weight: 600 !important;
    color: #FFFFFF !important;
}

[data-testid="stSidebar"] {
    background-color: #13151F;
    border-right: 1px solid #2A2D3E;
}
[data-testid="stSidebar"] .stRadio label {
    padding: 8px 12px;
    border-radius: 8px;
    cursor: pointer;
    font-size: 14px;
    color: #8A8FA8;
}
[data-testid="stSidebar"] .stRadio label:hover {
    background-color: #2A2D3E;
    color: #FFFFFF;
}

.js-plotly-plot {
    background-color: #1A1D27 !important;
    border-radius: 12px;
    border: 1px solid #2A2D3E;
}

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ── 차트 높이 상수 ─────────────────────────────────────────────────────────────

CHART_HEIGHT_SM = 280
CHART_HEIGHT_MD = 340
CHART_HEIGHT_LG = 400


# ── 데이터 로드 ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_history(ticker: str, limit: int = 365) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT date, value FROM indicators WHERE ticker=? ORDER BY date ASC LIMIT ?",
        conn, params=(ticker, limit),
    )
    conn.close()
    df["date"] = pd.to_datetime(df["date"])
    return df


@st.cache_data(ttl=3600)
def load_latest(ticker: str) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT value, date, collected_at FROM indicators WHERE ticker=? ORDER BY date DESC LIMIT 1",
        (ticker,),
    ).fetchone()
    conn.close()
    return {"value": row[0], "date": row[1], "collected_at": row[2]} if row else None


@st.cache_data(ttl=3600)
def load_all_latest() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        """SELECT ticker, name, category, value, date
           FROM indicators
           WHERE (ticker, date) IN (
               SELECT ticker, MAX(date) FROM indicators GROUP BY ticker
           )
           ORDER BY category, ticker""",
        conn,
    )
    conn.close()
    return df


@st.cache_data(ttl=3600)
def load_recent(ticker: str, limit: int = 14) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT date, value FROM indicators WHERE ticker=? ORDER BY date DESC LIMIT ?",
        conn, params=(ticker, limit),
    )
    conn.close()
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


@st.cache_data(ttl=3600)
def get_yoy_pct(ticker: str) -> float | None:
    df = load_recent(ticker, 14)
    if len(df) < 13:
        return None
    current = df["value"].iloc[-1]
    year_ago = df["value"].iloc[-13]
    if year_ago == 0:
        return None
    return round((current / year_ago - 1) * 100, 2)


@st.cache_data(ttl=3600)
def calc_changes(ticker: str) -> dict:
    df = load_recent(ticker, 35)
    if df.empty:
        return {"1일(%)": None, "1주(%)": None, "1개월(%)": None}
    latest_val = df["value"].iloc[-1]

    def safe_pct(i: int) -> float | None:
        if len(df) <= i:
            return None
        past = df["value"].iloc[-(i + 1)]
        if past == 0:
            return None
        return round((latest_val / past - 1) * 100, 2)

    gap = (df["date"].iloc[-1] - df["date"].iloc[-2]).days if len(df) >= 2 else 30
    if gap <= 3:
        return {"1일(%)": safe_pct(1), "1주(%)": safe_pct(5), "1개월(%)": safe_pct(22)}
    else:
        return {"1일(%)": 0.0, "1주(%)": 0.0, "1개월(%)": safe_pct(1)}


@st.cache_data(ttl=604800)
def load_financials(ticker: str):
    try:
        stock = yf.Ticker(ticker)
        fin = stock.quarterly_income_stmt
        bs  = stock.quarterly_balance_sheet
        return fin, bs
    except Exception:
        return None, None


def get_last_collected() -> str:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT MAX(collected_at) FROM indicators").fetchone()
    conn.close()
    return row[0][:16] if row and row[0] else "알 수 없음"


# ── 포매팅 ───────────────────────────────────────────────────────────────────

def fmt_value(value: float, unit: str) -> str:
    if unit == "%":
        return f"{value:.2f}%"
    elif unit == "KRW":
        return f"₩{value:,.0f}"
    elif unit == "USD":
        return f"${value:,.2f}"
    elif unit == "index":
        return f"{value:,.2f}"
    return f"{value:,.2f}"


def delta_color(ticker: str, delta: float) -> str:
    inverted = {"FEDFUNDS", "GS10", "GS2", "10Y2Y_SPREAD", "DX-Y.NYB", "KRW=X"}
    if delta == 0:
        return "off"
    up_is_good = ticker not in inverted
    if (delta > 0 and up_is_good) or (delta < 0 and not up_is_good):
        return "normal"
    return "inverse"


# ── 신호등 시스템 ─────────────────────────────────────────────────────────────

SIGNAL_RULES: dict = {
    "10Y2Y_SPREAD": lambda v: "🔴" if v < 0    else ("🟡" if v < 0.5  else "🟢"),
    "CPIAUCSL":     lambda v: "🔴" if v > 4    else ("🟡" if v > 2.5  else "🟢"),
    "UNRATE":       lambda v: "🔴" if v > 5    else ("🟡" if v > 4.5  else "🟢"),
    "FEDFUNDS":     lambda v: "🟡" if v > 4    else "🟢",
    "DX-Y.NYB":     lambda v: "🟡" if v > 104  else "🟢",
    "KRW=X":        lambda v: "🔴" if v > 1400 else ("🟡" if v > 1350 else "🟢"),
    "CL=F":         lambda v: "🔴" if v > 90   else ("🟡" if v > 75   else "🟢"),
    "^KS11":        lambda v: "🟡" if v < 2400 else "🟢",
}


def get_signal(ticker: str) -> str:
    rule = SIGNAL_RULES.get(ticker)
    if rule is None:
        return "⚪"
    if ticker == "CPIAUCSL":
        yoy = get_yoy_pct("CPIAUCSL")
        return rule(yoy) if yoy is not None else "⚪"
    latest = load_latest(ticker)
    return rule(latest["value"]) if latest else "⚪"


def tab_signal(tickers: list[str]) -> str:
    signals = [get_signal(t) for t in tickers if load_latest(t)]
    if "🔴" in signals:
        return "🔴"
    if "🟡" in signals:
        return "🟡"
    if signals:
        return "🟢"
    return "⚪"


# ── 지표 설명 ─────────────────────────────────────────────────────────────────

INDICATOR_HELP: dict = {
    "FEDFUNDS": (
        "Fed 정책금리. 모든 금융시장의 기준점.\n"
        "📈 인상: 달러강세·주식 하락 압력\n"
        "📉 인하: 위험자산 선호·신흥국 자금 유입\n"
        "연관: GS10 GS2 DX-Y.NYB CPIAUCSL"
    ),
    "GS10": (
        "시장이 결정하는 장기금리. 인플레·성장 기대치 직접 반영.\n"
        "기준금리보다 낮아지면 장단기 역전 → 경기침체 신호"
    ),
    "GS2": (
        "기준금리 방향을 가장 민감하게 선반영.\n"
        "10년물보다 높으면(역전) 경기침체 선행 신호"
    ),
    "10Y2Y_SPREAD": (
        "경기침체 선행지표 (6~18개월 전 신호).\n"
        "양수→정상 / 0근처→경계 / 음수(역전)→침체 신호\n"
        "주의: 역전 해소 직후가 실제 침체 시작인 경우 多"
    ),
    "DX-Y.NYB": (
        "달러 대비 주요 6개 통화 강도 지수. 100이 기준.\n"
        "📈 상승: 원자재 하락·신흥국 자본유출·원화약세\n"
        "104 이상: 강달러 경계"
    ),
    "CPIAUCSL": (
        "소비자 체감 물가. Fed 목표 2%(YoY 기준).\n"
        "> 4%: 강한 긴축 압력\n"
        "2.5~4%: 금리인하 지연 가능성\n"
        "절대값보다 3개월 방향이 중요"
    ),
    "PCEPI": (
        "Fed 공식 물가 지표. 소비 패턴 변화 잘 반영.\n"
        "2% 초과 지속: 긴축 유지 / 2% 이하: 완화 전환 가능\n"
        "CPI와 방향 다를 때 PCE 우선 신뢰"
    ),
    "UNRATE": (
        "경기 후행 지표. 자연실업률 4~4.5% 기준.\n"
        "> 5%: 침체 / 4.5~5%: 둔화 신호\n"
        "역설: 실업률 상승이 '금리인하 기대'로 주가 상승 유발 가능"
    ),
    "UMCSENT": (
        "소비자 경기 낙관도 설문. 100이 역사적 기준선.\n"
        "> 100: 강한 낙관 / 60~80: 소비 위축 우려\n"
        "< 60: 심리 붕괴 수준"
    ),
    "KRW=X": (
        "달러 대비 원화. 숫자 상승 = 원화 약세.\n"
        "원화 약세: 수출기업 유리·수입물가 상승\n"
        "하루 30원 이상 급변: 외부 충격 / 1,400원↑: 개입 경계선"
    ),
    "CL=F": (
        "WTI 원유 가격. 달러와 역상관.\n"
        "📈 상승: 인플레 압력·한국 무역수지 악화·원화 약세\n"
        "중동 분쟁·OPEC+ 감산이 단기 급등락 요인"
    ),
    "GC=F": (
        "안전자산 대표. 금리 상승 시 매력 감소.\n"
        "주식 급락 + 금 상승: 안전자산 도피\n"
        "금 + 주식 동반 상승: 유동성 장세"
    ),
    "722Y001": (
        "한국은행 정책금리.\n"
        "한국 < 미국(역전): 원화약세·자본유출 우려\n"
        "한미 금리차 1%p↑: 외국인 자금 유출 가속"
    ),
    "901Y009": (
        "한국 소비자물가. 한국은행 금리 결정 핵심 근거.\n"
        "원화 약세 + 유가 상승 동시: 수입 인플레 급등 위험"
    ),
    "403Y001": (
        "한국 수출 변화 지수. 반도체 수출 비중 20%↑.\n"
        "SOX와 비교 시 반도체 업황 크로스체크 가능"
    ),
    "^SOX": (
        "글로벌 반도체 기업 30개 업황 바로미터.\n"
        "삼성/하이닉스 주가의 선행지표 역할.\n"
        "SOX 상승 → 2~4주 후 하이닉스/삼성 반응 패턴"
    ),
    "NVDA": (
        "AI 인프라 수요 선행지표.\n"
        "NVDA 호조 → HBM 수요 증가 → 하이닉스/삼성 호재 체인\n"
        "분기 가이던스(다음 분기 전망)가 주가에 더 중요"
    ),
    "005930.KS": (
        "코스피 시총 1위. DS(반도체)+MX(스마트폰)+SDC.\n"
        "DS 부문 HBM4 경쟁력이 2026~2027 핵심\n"
        "하이닉스보다 약세 지속: HBM 점유율 격차 확대 신호"
    ),
    "000660.KS": (
        "HBM3E 선점으로 엔비디아 주요 공급자.\n"
        "순수 메모리 플레이어 → 업황에 삼성보다 민감\n"
        "NVDA 가이던스에 직접 주가 반응"
    ),
    "^GSPC": (
        "미국 대형주 500개. 글로벌 리스크 온/오프 기준.\n"
        "나스닥이 S&P500보다 크게 빠지면: 기술주/금리 민감 국면"
    ),
    "^IXIC": (
        "기술주/성장주 중심. 금리 변화에 가장 민감.\n"
        "나스닥 > S&P500 상승: 기술주 장세·금리 안정 기대"
    ),
    "^KS11": (
        "한국 대형주. 삼성+SK하이닉스 비중 25%↑.\n"
        "달러 강세 → 외국인 이탈 → 코스피 하락 압력"
    ),
    "^KQ11": (
        "한국 중소형/성장주. 바이오/IT 비중 높음.\n"
        "코스닥 > 코스피: 성장주 선호·금리 안정 기대\n"
        "금리에 코스피보다 더 민감"
    ),
}


# ── 경기 사이클 ───────────────────────────────────────────────────────────────

def is_unrate_rising() -> bool:
    df = load_recent("UNRATE", 4)
    if len(df) < 4:
        return False
    v = df["value"].tolist()
    return v[-1] > v[-2] > v[-3]


def get_business_cycle() -> tuple[str, int]:
    spread_d  = load_latest("10Y2Y_SPREAD")
    umcsent_d = load_latest("UMCSENT")
    spread    = spread_d["value"]  if spread_d  else None
    umcsent   = umcsent_d["value"] if umcsent_d else None
    cpi_yoy   = get_yoy_pct("CPIAUCSL")
    unrate_rising = is_unrate_rising()

    if spread is not None and spread < 0:
        return ("침체", 4) if unrate_rising else ("수축", 3)
    if unrate_rising and spread is not None and spread < 0.5:
        return "수축", 3
    if cpi_yoy is not None and cpi_yoy > 3 and umcsent is not None and umcsent > 90:
        return "과열", 2
    return "팽창", 1


def render_cycle_panel(stage: str, stage_num: int):
    stages = ["팽창", "과열", "수축", "침체"]
    colors = ["#22c55e", "#f59e0b", "#f97316", "#ef4444"]
    cols = st.columns(4)
    for i, (s, c) in enumerate(zip(stages, colors)):
        is_current = (i + 1 == stage_num)
        bg         = c if is_current else "#1A1D27"
        text_col   = "white" if is_current else "#6B7280"
        border     = f"2px solid {c}" if is_current else "1px solid #2A2D3E"
        note       = "<br><small>(현재)</small>" if is_current else ""
        cols[i].markdown(
            f'<div style="background:{bg};border:{border};border-radius:8px;'
            f'padding:14px 8px;text-align:center;color:{text_col};font-weight:bold;font-size:15px">'
            f'{"●" if is_current else "○"} {s}{note}</div>',
            unsafe_allow_html=True,
        )


# ── 알림 ─────────────────────────────────────────────────────────────────────

def get_alerts() -> list[tuple]:
    alerts = []
    spread_d = load_latest("10Y2Y_SPREAD")
    cpi_yoy  = get_yoy_pct("CPIAUCSL")
    krw_hist = load_recent("KRW=X", 2)
    sox_hist = load_recent("^SOX", 30)

    if spread_d and spread_d["value"] < 0:
        alerts.append(("error", "🔴 장단기 금리 역전 중 — 경기침체 선행 신호", "10Y2Y_SPREAD"))
    if cpi_yoy is not None and cpi_yoy > 3:
        alerts.append(("warning", f"🟡 미국 CPI YoY {cpi_yoy:.1f}% — 금리 인하 지연 가능성", "CPIAUCSL"))
    if len(krw_hist) >= 2:
        krw_1d = abs(krw_hist["value"].iloc[-1] - krw_hist["value"].iloc[-2])
        if krw_1d > 20:
            alerts.append(("error", f"🚨 원/달러 환율 하루 {krw_1d:.0f}원 급변 — 외부 충격 모니터링", "KRW=X"))
    if len(sox_hist) >= 20:
        sox_1m = (sox_hist["value"].iloc[-1] / sox_hist["value"].iloc[0] - 1) * 100
        if sox_1m > 15:
            alerts.append(("success", f"🟢 SOX 1개월 +{sox_1m:.1f}% — 반도체 업황 강세", "^SOX"))
    if is_unrate_rising():
        alerts.append(("warning", "🟡 실업률 3개월 연속 상승 — 고용 둔화 신호", "UNRATE"))
    return alerts


# ── 다크 테마 차트 헬퍼 ───────────────────────────────────────────────────────

def dark_layout(title: str = "", height: int = CHART_HEIGHT_MD) -> dict:
    return dict(
        title=dict(text=title, font=dict(color="#E0E0E0", size=14)),
        height=height,
        paper_bgcolor="#1A1D27",
        plot_bgcolor="#1A1D27",
        font=dict(color="#8A8FA8", size=12),
        xaxis=dict(
            gridcolor="#2A2D3E",
            linecolor="#2A2D3E",
            tickcolor="#2A2D3E",
            tickfont=dict(color="#8A8FA8"),
        ),
        yaxis=dict(
            gridcolor="#2A2D3E",
            linecolor="#2A2D3E",
            tickcolor="#2A2D3E",
            tickfont=dict(color="#8A8FA8"),
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#2A2D3E", font_color="#E0E0E0"),
        legend=dict(
            orientation="h",
            bgcolor="rgba(0,0,0,0)",
            font=dict(color="#8A8FA8"),
            y=-0.15,
        ),
    )


def dark_yaxis2(title: str = "") -> dict:
    return dict(
        title=title, overlaying="y", side="right", showgrid=False,
        linecolor="#2A2D3E", tickcolor="#2A2D3E",
        tickfont=dict(color="#8A8FA8"),
    )


# ── 페이지 헤더 ───────────────────────────────────────────────────────────────

def page_header(title: str, subtitle: str):
    st.markdown(f"""
    <div style="margin-bottom: 24px;">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 4px;">
            <h1 style="margin: 0; font-size: 28px; font-weight: 600; color: #FFFFFF;">{title}</h1>
            <span style="background-color:#1E3A5F;color:#4A9EFF;padding:2px 10px;
                border-radius:20px;font-size:12px;font-weight:500;">Live Data</span>
        </div>
        <p style="margin: 0; color: #8A8FA8; font-size: 14px;">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


# ── UI 헬퍼 ──────────────────────────────────────────────────────────────────

def kpi_card(col, ticker: str, label: str, unit: str):
    latest = load_latest(ticker)
    if latest is None:
        col.metric(label, "데이터 없음")
        return
    hist  = load_recent(ticker, 2)
    delta = None
    if len(hist) >= 2:
        delta = round(hist["value"].iloc[-1] - hist["value"].iloc[-2], 4)
    signal = get_signal(ticker)
    col.metric(
        label=f"{signal} {label}",
        value=fmt_value(latest["value"], unit),
        delta=f"{delta:+.4f}" if delta is not None else None,
        delta_color=delta_color(ticker, delta) if delta is not None else "off",
        help=INDICATOR_HELP.get(ticker, f"기준일: {latest['date']}"),
    )


def period_slider(key: str) -> int:
    return st.select_slider(
        "조회 기간",
        options=[30, 90, 180, 365, 730],
        value=365,
        format_func=lambda x: f"{x // 30}개월" if x < 365 else f"{x // 365}년",
        key=key,
    )


def line_chart(ticker: str, title: str, unit: str, limit: int = 365) -> go.Figure:
    df = load_history(ticker, limit=limit)
    fig = go.Figure()
    if df.empty:
        return fig
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["value"], mode="lines", name=title,
        line=dict(width=2, color=TICKER_COLORS.get(ticker, "#4A9EFF")),
    ))
    layout = dark_layout(title, CHART_HEIGHT_MD)
    layout["yaxis"]["title"] = unit
    fig.update_layout(**layout)
    return fig


def mini_chart(ticker: str, title: str, limit: int = 180) -> go.Figure:
    df = load_history(ticker, limit=limit)
    fig = go.Figure()
    if df.empty:
        return fig
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["value"], mode="lines", name=title,
        line=dict(width=1.5, color=TICKER_COLORS.get(ticker, "#4A9EFF")),
    ))
    layout = dark_layout(title, 200)
    layout["xaxis"]["showticklabels"] = False
    layout["margin"] = dict(l=0, r=0, t=30, b=0)
    fig.update_layout(**layout)
    return fig


def show_situation_messages(tab: str):
    spread_d = load_latest("10Y2Y_SPREAD")
    dxy_d    = load_latest("DX-Y.NYB")
    krw_d    = load_latest("KRW=X")
    cpi_yoy  = get_yoy_pct("CPIAUCSL")

    if tab == "global":
        if spread_d and spread_d["value"] < 0:
            st.warning("🔴 장단기 금리 역전 중 — 경기침체 선행 신호")
        if dxy_d and dxy_d["value"] > 104:
            st.warning("🟡 달러 강세(DXY>104) — 신흥국 자본 유출 압력")
    elif tab == "inflation":
        if cpi_yoy is not None and cpi_yoy > 3:
            st.warning(f"🟡 미국 CPI YoY {cpi_yoy:.1f}% 초과 — 금리 인하 지연 가능성")
        if is_unrate_rising():
            st.warning("🟡 실업률 3개월 연속 상승 — 고용 둔화 신호")
    elif tab == "korea":
        if krw_d and krw_d["value"] > 1400:
            st.error("🔴 원/달러 1,400원 초과 — 한국은행 개입 경계선")
    elif tab == "semicon":
        sox_hist = load_recent("^SOX", 30)
        if len(sox_hist) >= 20:
            sox_1m = (sox_hist["value"].iloc[-1] / sox_hist["value"].iloc[0] - 1) * 100
            if sox_1m > 15:
                st.success(f"🟢 SOX 1개월 +{sox_1m:.1f}% — 반도체 강세 국면")
            elif sox_1m < -10:
                st.warning(f"🟡 SOX 1개월 {sox_1m:.1f}% — 반도체 업황 둔화 주의")


# ── 전체 지표 목록 ─────────────────────────────────────────────────────────────

ALL_TICKERS = [
    ("FEDFUNDS", "미국 기준금리"), ("GS10", "10년물 국채"), ("GS2", "2년물 국채"),
    ("10Y2Y_SPREAD", "장단기 금리차"), ("DX-Y.NYB", "달러 인덱스"),
    ("CPIAUCSL", "미국 CPI"), ("PCEPI", "미국 PCE"), ("UNRATE", "실업률"),
    ("UMCSENT", "소비자심리"),
    ("KRW=X", "원/달러 환율"), ("722Y001", "한국 기준금리"), ("901Y009", "한국 CPI"),
    ("403Y001", "수출금액지수"), ("CL=F", "WTI 유가"), ("GC=F", "금 가격"),
    ("^SOX", "SOX"), ("NVDA", "엔비디아"),
    ("005930.KS", "삼성전자"), ("000660.KS", "SK하이닉스"),
    ("^GSPC", "S&P500"), ("^IXIC", "나스닥"), ("^KS11", "코스피"), ("^KQ11", "코스닥"),
]


# ── 페이지 함수 ───────────────────────────────────────────────────────────────

def show_overview():
    page_header("Overview", "Key macroeconomic indicators and market data")

    st.subheader("경기 사이클")
    stage, stage_num = get_business_cycle()
    render_cycle_panel(stage, stage_num)
    st.caption("판단 기준: 장단기 금리차 · 실업률 추세 · CPI YoY · 소비자심리")

    st.divider()

    st.subheader("핵심 지표 신호등")
    signal_tickers = [
        ("10Y2Y_SPREAD", "장단기 금리차"),
        ("CPIAUCSL",     "미국 CPI(YoY)"),
        ("UNRATE",       "실업률"),
        ("FEDFUNDS",     "미국 기준금리"),
        ("DX-Y.NYB",     "달러 인덱스"),
        ("KRW=X",        "원/달러 환율"),
        ("CL=F",         "WTI 유가"),
        ("^KS11",        "코스피"),
    ]
    sig_cols = st.columns(4)
    for i, (ticker, label) in enumerate(signal_tickers):
        signal = get_signal(ticker)
        latest = load_latest(ticker)
        val_str = ""
        if latest:
            if ticker == "CPIAUCSL":
                yoy = get_yoy_pct(ticker)
                val_str = f"{yoy:.1f}%" if yoy is not None else "-"
            elif ticker in ("FEDFUNDS", "UNRATE", "10Y2Y_SPREAD", "722Y001"):
                val_str = f"{latest['value']:.2f}%"
            elif ticker == "KRW=X":
                val_str = f"₩{latest['value']:,.0f}"
            elif ticker == "CL=F":
                val_str = f"${latest['value']:.1f}"
            else:
                val_str = f"{latest['value']:,.1f}"
        sig_cols[i % 4].metric(label=f"{signal} {label}", value=val_str)

    st.divider()

    alerts = get_alerts()
    if alerts:
        st.subheader("알림")
        for alert_type, msg, _ in alerts:
            getattr(st, alert_type)(msg)
        st.divider()

    st.subheader("주요 차트")
    alert_tickers = [t for _, _, t in alerts]
    default_charts = [
        ("10Y2Y_SPREAD", "장단기 금리차"),
        ("^SOX",         "SOX 반도체지수"),
        ("KRW=X",        "원/달러 환율"),
    ]
    chart_targets = []
    seen = set()
    for t in alert_tickers:
        if t not in seen:
            for ticker, label in ALL_TICKERS:
                if ticker == t and ticker not in seen:
                    chart_targets.append((ticker, label))
                    seen.add(ticker)
                    break
        if len(chart_targets) >= 3:
            break
    for ticker, label in default_charts:
        if ticker not in seen:
            chart_targets.append((ticker, label))
            seen.add(ticker)
        if len(chart_targets) >= 3:
            break

    mc1, mc2, mc3 = st.columns(3)
    for col, (ticker, label) in zip([mc1, mc2, mc3], chart_targets[:3]):
        col.plotly_chart(mini_chart(ticker, label), use_container_width=True)

    st.divider()

    st.subheader("전체 지표 변화율 히트맵")
    with st.spinner("히트맵 계산 중..."):
        heat_rows = []
        for ticker, label in ALL_TICKERS:
            chg = calc_changes(ticker)
            heat_rows.append({
                "지표": label,
                "1일(%)": chg["1일(%)"],
                "1주(%)": chg["1주(%)"],
                "1개월(%)": chg["1개월(%)"],
            })
        heat_df = pd.DataFrame(heat_rows).set_index("지표").fillna(0)
    fig_heat = px.imshow(
        heat_df,
        color_continuous_scale="RdYlGn",
        color_continuous_midpoint=0,
        text_auto=".2f",
        aspect="auto",
    )
    fig_heat.update_layout(
        height=550,
        paper_bgcolor="#1A1D27",
        plot_bgcolor="#1A1D27",
        font=dict(color="#E0E0E0"),
        margin=dict(l=0, r=0, t=20, b=0),
    )
    st.plotly_chart(fig_heat, use_container_width=True)


def show_markets():
    page_header("Markets", "미국 국채 금리 · 장단기 스프레드 · 달러 인덱스")
    period = period_slider("period_markets")
    show_situation_messages("global")

    c1, c2, c3, c4, c5 = st.columns(5)
    kpi_card(c1, "FEDFUNDS",      "미국 기준금리", "%")
    kpi_card(c2, "GS10",          "10년물 국채",   "%")
    kpi_card(c3, "GS2",           "2년물 국채",    "%")
    kpi_card(c4, "10Y2Y_SPREAD",  "장단기 금리차", "%")
    kpi_card(c5, "DX-Y.NYB",      "달러 인덱스",   "index")

    st.divider()

    col_l, col_r = st.columns(2)
    with col_l:
        df_ff  = load_history("FEDFUNDS",     period)
        df_gs10= load_history("GS10",         period)
        df_gs2 = load_history("GS2",          period)
        df_sp  = load_history("10Y2Y_SPREAD", period)
        fig = go.Figure()
        for df, ticker, name in [
            (df_ff,   "FEDFUNDS",     "기준금리"),
            (df_gs10, "GS10",         "10년물"),
            (df_gs2,  "GS2",          "2년물"),
            (df_sp,   "10Y2Y_SPREAD", "장단기 금리차"),
        ]:
            if not df.empty:
                fig.add_trace(go.Scatter(
                    x=df["date"], y=df["value"], name=name,
                    line=dict(color=TICKER_COLORS.get(ticker, "#4A9EFF")),
                ))
        fig.add_hline(y=0, line_dash="dash", line_color="#ef4444", opacity=0.5)
        fig.update_layout(**dark_layout("미국 국채 금리 추이", CHART_HEIGHT_MD))
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        if load_history("DX-Y.NYB", period).empty:
            st.info("📡 데이터를 불러오는 중이거나 수집되지 않은 지표입니다.")
        else:
            st.plotly_chart(line_chart("DX-Y.NYB", "달러 인덱스 (DXY)", "index", limit=period), use_container_width=True)


def show_macro():
    page_header("Macro Economy", "인플레이션 · 고용 · 소비자심리")
    period = period_slider("period_macro")
    show_situation_messages("inflation")

    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, "CPIAUCSL", "미국 CPI",          "index")
    kpi_card(c2, "PCEPI",    "미국 PCE",          "index")
    kpi_card(c3, "UNRATE",   "실업률",             "%")
    kpi_card(c4, "UMCSENT",  "소비자심리(미시건)", "index")

    st.divider()

    col_l, col_r = st.columns(2)
    with col_l:
        df_cpi = load_history("CPIAUCSL", period)
        df_pce = load_history("PCEPI",    period)
        fig = go.Figure()
        if not df_cpi.empty:
            fig.add_trace(go.Scatter(
                x=df_cpi["date"], y=df_cpi["value"], name="CPI (좌)",
                line=dict(color=TICKER_COLORS.get("CPIAUCSL", "#4A9EFF")),
            ))
        if not df_pce.empty:
            fig.add_trace(go.Scatter(
                x=df_pce["date"], y=df_pce["value"], name="PCE (우)",
                line=dict(color=TICKER_COLORS.get("PCEPI", "#E63946")), yaxis="y2",
            ))
        if df_cpi.empty and df_pce.empty:
            st.info("📡 데이터를 불러오는 중이거나 수집되지 않은 지표입니다.")
        else:
            layout = dark_layout("CPI / PCE 추이", CHART_HEIGHT_MD)
            layout["yaxis"]["title"]  = "CPI"
            layout["yaxis2"]          = dark_yaxis2("PCE")
            layout["margin"]          = dict(l=0, r=50, t=40, b=0)
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True)

    with col_r:
        col_l2, col_r2 = st.columns(2)
        with col_l2:
            if load_history("UNRATE", period).empty:
                st.info("📡 UNRATE 데이터 없음")
            else:
                st.plotly_chart(line_chart("UNRATE", "실업률 (%)", "%", limit=period), use_container_width=True)
        with col_r2:
            if load_history("UMCSENT", period).empty:
                st.info("📡 UMCSENT 데이터 없음")
            else:
                st.plotly_chart(line_chart("UMCSENT", "소비자심리지수", "index", limit=period), use_container_width=True)


def show_korea():
    page_header("한국·원자재", "원화 · 유가 · 금 · 수출 지표")
    period = period_slider("period_korea")
    show_situation_messages("korea")

    c1, c2, c3 = st.columns(3)
    kpi_card(c1, "KRW=X",   "원/달러 환율", "KRW")
    kpi_card(c2, "722Y001", "한국 기준금리", "%")
    kpi_card(c3, "901Y009", "한국 CPI",     "index")

    c4, c5, c6 = st.columns(3)
    kpi_card(c4, "403Y001", "수출금액지수", "index")
    kpi_card(c5, "CL=F",    "WTI 유가",    "USD")
    kpi_card(c6, "GC=F",    "금 가격",     "USD")

    st.divider()

    col_l, col_r = st.columns(2)
    with col_l:
        st.plotly_chart(line_chart("KRW=X", "원/달러 환율", "KRW", limit=period), use_container_width=True)
        st.plotly_chart(
            line_chart("403Y001", "한국 수출금액지수", "index", limit=min(period, 60)),
            use_container_width=True,
        )

    with col_r:
        df_oil  = load_history("CL=F", period)
        df_gold = load_history("GC=F", period)
        fig = go.Figure()
        if not df_oil.empty:
            fig.add_trace(go.Scatter(
                x=df_oil["date"], y=df_oil["value"], name="WTI (좌, USD)",
                line=dict(color=TICKER_COLORS.get("CL=F", "#F4A261")),
            ))
        if not df_gold.empty:
            fig.add_trace(go.Scatter(
                x=df_gold["date"], y=df_gold["value"], name="금 (우, USD)",
                line=dict(color=TICKER_COLORS.get("GC=F", "#FFD700")), yaxis="y2",
            ))
        if df_oil.empty and df_gold.empty:
            st.info("📡 데이터를 불러오는 중이거나 수집되지 않은 지표입니다.")
        else:
            layout = dark_layout("원자재 가격 추이", CHART_HEIGHT_MD)
            layout["yaxis"]["title"] = "WTI (USD)"
            layout["yaxis2"]         = dark_yaxis2("금 (USD)")
            layout["margin"]         = dict(l=0, r=50, t=40, b=0)
            fig.update_layout(**layout)
            st.plotly_chart(fig, use_container_width=True)

        df_krbo  = load_history("722Y001", min(period, 60))
        df_krcpi = load_history("901Y009", min(period, 60))
        fig2 = go.Figure()
        if not df_krbo.empty:
            fig2.add_trace(go.Scatter(
                x=df_krbo["date"], y=df_krbo["value"], name="기준금리 (좌, %)",
                line=dict(color=TICKER_COLORS.get("722Y001", "#457B9D")),
            ))
        if not df_krcpi.empty:
            fig2.add_trace(go.Scatter(
                x=df_krcpi["date"], y=df_krcpi["value"], name="CPI (우, index)",
                line=dict(color=TICKER_COLORS.get("901Y009", "#E76F51")), yaxis="y2",
            ))
        if df_krbo.empty and df_krcpi.empty:
            st.info("📡 데이터를 불러오는 중이거나 수집되지 않은 지표입니다.")
        else:
            layout2 = dark_layout("한국 금리 & CPI", CHART_HEIGHT_MD)
            layout2["yaxis"]["title"] = "금리 (%)"
            layout2["yaxis2"]         = dark_yaxis2("CPI (index)")
            layout2["margin"]         = dict(l=0, r=50, t=40, b=0)
            fig2.update_layout(**layout2)
            st.plotly_chart(fig2, use_container_width=True)


def show_semiconductor():
    page_header("반도체·주식", "반도체 업황 및 주요 종목")
    period = period_slider("period_semi")
    show_situation_messages("semicon")

    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, "^SOX",       "필라델피아 반도체", "index")
    kpi_card(c2, "NVDA",       "엔비디아",          "USD")
    kpi_card(c3, "005930.KS",  "삼성전자",          "KRW")
    kpi_card(c4, "000660.KS",  "SK하이닉스",        "KRW")

    c5, c6, c7, c8 = st.columns(4)
    kpi_card(c5, "^GSPC", "S&P 500", "index")
    kpi_card(c6, "^IXIC", "나스닥",  "index")
    kpi_card(c7, "^KS11", "코스피",  "index")
    kpi_card(c8, "^KQ11", "코스닥",  "index")

    st.divider()

    col_l, col_r = st.columns(2)
    with col_l:
        semi_tickers = [
            ("^SOX",       "SOX"),
            ("NVDA",       "NVDA"),
            ("005930.KS",  "삼성전자"),
            ("000660.KS",  "SK하이닉스"),
        ]
        fig = go.Figure()
        for ticker, label in semi_tickers:
            df = load_history(ticker, period)
            if df.empty:
                continue
            base = df["value"].iloc[0]
            df = df.copy()
            df["norm"] = (df["value"] / base - 1) * 100
            fig.add_trace(go.Scatter(
                x=df["date"], y=df["norm"], name=label,
                line=dict(color=TICKER_COLORS.get(ticker, "#4A9EFF")),
            ))
        layout = dark_layout("반도체 관련주 수익률 비교 (%)", CHART_HEIGHT_LG)
        layout["yaxis"]["ticksuffix"] = "%"
        fig.update_layout(**layout)
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        idx_tickers = [
            ("^GSPC", "S&P500"),
            ("^IXIC", "나스닥"),
            ("^KS11", "코스피"),
            ("^KQ11", "코스닥"),
        ]
        fig2 = go.Figure()
        for ticker, label in idx_tickers:
            df = load_history(ticker, period)
            if df.empty:
                continue
            base = df["value"].iloc[0]
            df = df.copy()
            df["norm"] = (df["value"] / base - 1) * 100
            fig2.add_trace(go.Scatter(
                x=df["date"], y=df["norm"], name=label,
                line=dict(color=TICKER_COLORS.get(ticker, "#4A9EFF")),
            ))
        layout2 = dark_layout("글로벌 지수 수익률 비교 (%)", CHART_HEIGHT_LG)
        layout2["yaxis"]["ticksuffix"] = "%"
        fig2.update_layout(**layout2)
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    st.subheader("최근 등락률 히트맵")
    latest_df = load_all_latest()
    stock_tickers = ["^SOX", "NVDA", "005930.KS", "000660.KS", "^GSPC", "^IXIC", "^KS11", "^KQ11"]
    heat_data = []
    for ticker in stock_tickers:
        df = load_history(ticker, 30)
        if len(df) < 2:
            continue
        latest_row = latest_df[latest_df["ticker"] == ticker]
        name   = latest_row["name"].values[0] if not latest_row.empty else ticker
        chg_1d = (df["value"].iloc[-1] / df["value"].iloc[-2] - 1) * 100 if len(df) >= 2  else 0
        chg_5d = (df["value"].iloc[-1] / df["value"].iloc[-5] - 1) * 100 if len(df) >= 5  else 0
        chg_1m = (df["value"].iloc[-1] / df["value"].iloc[0]  - 1) * 100 if len(df) >= 20 else 0
        heat_data.append({"종목": name, "1일(%)": round(chg_1d, 2), "5일(%)": round(chg_5d, 2), "1개월(%)": round(chg_1m, 2)})
    if heat_data:
        heat_df4 = pd.DataFrame(heat_data).set_index("종목")
        fig_h = px.imshow(
            heat_df4, color_continuous_scale="RdYlGn", color_continuous_midpoint=0,
            text_auto=True, aspect="auto",
        )
        fig_h.update_layout(
            height=300,
            paper_bgcolor="#1A1D27",
            plot_bgcolor="#1A1D27",
            font=dict(color="#E0E0E0"),
            margin=dict(l=0, r=0, t=20, b=0),
        )
        st.plotly_chart(fig_h, use_container_width=True)
    else:
        st.info("📡 주식 데이터를 불러오는 중이거나 수집되지 않은 지표입니다.")


def show_earnings():
    page_header("실적 트래커", "삼성전자 · SK하이닉스 · 엔비디아 분기 실적")
    st.caption("yfinance 분기 재무제표 기준. 데이터 지연 또는 누락이 있을 수 있습니다.")

    EARN_TICKERS = {"삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "엔비디아": "NVDA"}
    selected = st.selectbox("종목 선택", list(EARN_TICKERS.keys()), key="earn_select")
    ticker_e = EARN_TICKERS[selected]
    is_krw   = ticker_e.endswith(".KS")

    with st.spinner("재무 데이터 로딩 중..."):
        fin, bs = load_financials(ticker_e)

    def get_row(df, *keys):
        if df is None:
            return None
        for k in keys:
            if k in df.index:
                return df.loc[k]
        return None

    if fin is None or fin.empty:
        st.info("📡 데이터를 불러오는 중이거나 수집되지 않은 지표입니다.")
        return

    bs_t       = bs.T.sort_index() if bs is not None and not bs.empty else pd.DataFrame()
    scale      = 1e12 if is_krw else 1e9
    unit_label = "조원" if is_krw else "십억 USD"

    rev_series = get_row(fin, "Total Revenue", "Revenue")
    op_series  = get_row(fin, "Operating Income", "EBIT", "Operating Profit")
    inv_series = get_row(bs, "Inventory") if not bs_t.empty else None

    col_l, col_r = st.columns(2)

    with col_l:
        if rev_series is not None:
            rev_df   = rev_series.dropna().sort_index()
            quarters = [str(d)[:10] for d in rev_df.index]
            vals     = rev_df.values / scale

            fig_rev = go.Figure()
            fig_rev.add_trace(go.Bar(
                x=quarters, y=vals, name="매출",
                marker_color=TICKER_COLORS.get(ticker_e, "#4A9EFF"),
            ))
            if len(vals) >= 5:
                yoy_rates = [(vals[i] / vals[i - 4] - 1) * 100 for i in range(4, len(vals))]
                fig_rev.add_trace(go.Scatter(
                    x=quarters[4:], y=yoy_rates,
                    name="YoY(%)", mode="lines+markers",
                    line=dict(color="#E63946"), yaxis="y2",
                ))
            layout_rev = dark_layout(f"{selected} 분기 매출 ({unit_label})", CHART_HEIGHT_MD)
            layout_rev["yaxis"]["title"] = unit_label
            layout_rev["yaxis2"]         = dark_yaxis2("YoY(%)")
            layout_rev["margin"]         = dict(l=0, r=50, t=40, b=0)
            fig_rev.update_layout(**layout_rev)
            st.plotly_chart(fig_rev, use_container_width=True)
        else:
            st.info("매출 데이터 없음")

    with col_r:
        if op_series is not None:
            op_df    = op_series.dropna().sort_index()
            quarters = [str(d)[:10] for d in op_df.index]
            vals_op  = op_df.values / scale

            fig_op = go.Figure()
            colors_op = ["#22c55e" if v >= 0 else "#ef4444" for v in vals_op]
            fig_op.add_trace(go.Bar(x=quarters, y=vals_op, name="영업이익", marker_color=colors_op))

            if rev_series is not None:
                rev_df2    = rev_series.dropna().sort_index()
                common_idx = op_df.index.intersection(rev_df2.index)
                if len(common_idx) > 0:
                    margins = (op_df.loc[common_idx] / rev_df2.loc[common_idx] * 100).values
                    fig_op.add_trace(go.Scatter(
                        x=[str(d)[:10] for d in common_idx],
                        y=margins,
                        name="영업이익률(%)", mode="lines+markers",
                        line=dict(color="#F4A261"), yaxis="y2",
                    ))
            layout_op = dark_layout(f"{selected} 분기 영업이익 ({unit_label})", CHART_HEIGHT_MD)
            layout_op["yaxis"]["title"] = unit_label
            layout_op["yaxis2"]         = dark_yaxis2("영업이익률(%)")
            layout_op["margin"]         = dict(l=0, r=50, t=40, b=0)
            fig_op.update_layout(**layout_op)
            st.plotly_chart(fig_op, use_container_width=True)
        else:
            st.info("영업이익 데이터 없음")

    if inv_series is not None:
        inv_df       = inv_series.dropna().sort_index()
        quarters_inv = [str(d)[:10] for d in inv_df.index]
        vals_inv     = inv_df.values / scale
        fig_inv = go.Figure()
        fig_inv.add_trace(go.Bar(x=quarters_inv, y=vals_inv, name="재고", marker_color="#6A4C93"))
        layout_inv = dark_layout(f"{selected} 분기 재고 수준 ({unit_label})", CHART_HEIGHT_SM)
        layout_inv["yaxis"]["title"] = unit_label
        fig_inv.update_layout(**layout_inv)
        st.plotly_chart(fig_inv, use_container_width=True)
    else:
        st.info("재고 데이터 없음")


# ── 사이드바 네비게이션 ────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 📊 Macro Dash")
    st.divider()

    markets_sig = tab_signal(["FEDFUNDS", "GS10", "10Y2Y_SPREAD", "DX-Y.NYB"])
    macro_sig   = tab_signal(["CPIAUCSL", "UNRATE"])
    korea_sig   = tab_signal(["KRW=X", "CL=F"])
    semi_sig    = tab_signal(["^SOX", "^KS11"])

    page = st.radio(
        label="",
        options=[
            "Overview",
            f"Macro Economy {macro_sig}",
            f"Markets {markets_sig}",
            f"한국·원자재 {korea_sig}",
            f"반도체·주식 {semi_sig}",
            "실적 트래커",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    st.caption(f"마지막 수집: {get_last_collected()}")
    st.caption("Sources: FRED, ECOS, Yahoo Finance")


# ── 페이지 라우팅 ─────────────────────────────────────────────────────────────

if page.startswith("Overview"):
    show_overview()
elif page.startswith("Macro Economy"):
    show_macro()
elif page.startswith("Markets"):
    show_markets()
elif page.startswith("한국·원자재"):
    show_korea()
elif page.startswith("반도체·주식"):
    show_semiconductor()
else:
    show_earnings()
