import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import sqlite3
from datetime import datetime
from config import DB_PATH

st.set_page_config(
    page_title="거시경제 대시보드",
    page_icon="📊",
    layout="wide",
)

st.title("📊 거시경제 대시보드")
st.caption(f"마지막 갱신: {datetime.now().strftime('%Y-%m-%d %H:%M')}")


# ── 데이터 로드 ──────────────────────────────────────────────────────────────

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
    if row:
        return {"value": row[0], "date": row[1], "collected_at": row[2]}
    return None


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
    """금리/달러/환율은 상승=부정(red), 나머지는 상승=긍정(green)"""
    inverted = {"FEDFUNDS", "GS10", "GS2", "10Y2Y_SPREAD", "DX-Y.NYB", "KRW=X"}
    if delta == 0:
        return "off"
    up_is_good = ticker not in inverted
    if (delta > 0 and up_is_good) or (delta < 0 and not up_is_good):
        return "normal"
    return "inverse"


def kpi_card(col, ticker: str, label: str, unit: str):
    latest = load_latest(ticker)
    if latest is None:
        col.metric(label, "데이터 없음")
        return
    hist = load_history(ticker, limit=2)
    delta = None
    if len(hist) >= 2:
        delta = round(hist["value"].iloc[-1] - hist["value"].iloc[-2], 4)
    col.metric(
        label=label,
        value=fmt_value(latest["value"], unit),
        delta=f"{delta:+.4f}" if delta is not None else None,
        delta_color=delta_color(ticker, delta) if delta is not None else "off",
        help=f"기준일: {latest['date']}",
    )


def line_chart(ticker: str, title: str, unit: str, limit: int = 365) -> go.Figure:
    df = load_history(ticker, limit=limit)
    if df.empty:
        return go.Figure()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["value"],
        mode="lines", name=title,
        line=dict(width=2),
    ))
    fig.update_layout(
        title=title, xaxis_title="날짜", yaxis_title=unit,
        height=300, margin=dict(l=0, r=0, t=40, b=0),
        hovermode="x unified",
    )
    return fig


def multi_line_chart(tickers: list[tuple], title: str, height: int = 350) -> go.Figure:
    fig = go.Figure()
    for ticker, label, unit in tickers:
        df = load_history(ticker, limit=365)
        if df.empty:
            continue
        fig.add_trace(go.Scatter(
            x=df["date"], y=df["value"],
            mode="lines", name=label,
        ))
    fig.update_layout(
        title=title, height=height,
        margin=dict(l=0, r=0, t=40, b=0),
        hovermode="x unified", legend=dict(orientation="h"),
    )
    return fig


# ── 탭 구성 ──────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4 = st.tabs([
    "🌐 글로벌 금융",
    "📈 인플레이션/경기",
    "🇰🇷 한국/원자재",
    "💻 반도체/주식",
])

# ── 탭 1: 글로벌 금융 ────────────────────────────────────────────────────────
with tab1:
    st.subheader("글로벌 금융 환경")
    c1, c2, c3, c4, c5 = st.columns(5)
    kpi_card(c1, "FEDFUNDS", "미국 기준금리", "%")
    kpi_card(c2, "GS10", "10년물 국채", "%")
    kpi_card(c3, "GS2", "2년물 국채", "%")
    kpi_card(c4, "10Y2Y_SPREAD", "장단기 금리차", "%")
    kpi_card(c5, "DX-Y.NYB", "달러 인덱스", "index")

    st.divider()

    col_l, col_r = st.columns(2)
    with col_l:
        df_gs10 = load_history("GS10", 365)
        df_gs2 = load_history("GS2", 365)
        df_sp = load_history("10Y2Y_SPREAD", 365)
        fig = go.Figure()
        for df, name, color in [
            (df_gs10, "10년물", "royalblue"),
            (df_gs2, "2년물", "orange"),
            (df_sp, "장단기 금리차", "green"),
        ]:
            if not df.empty:
                fig.add_trace(go.Scatter(x=df["date"], y=df["value"], name=name, line=dict(color=color)))
        fig.add_hline(y=0, line_dash="dash", line_color="red", opacity=0.5)
        fig.update_layout(title="미국 국채 금리 추이", height=320, margin=dict(l=0,r=0,t=40,b=0), hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.plotly_chart(line_chart("DX-Y.NYB", "달러 인덱스 (DXY)", "index"), use_container_width=True)

# ── 탭 2: 인플레이션/경기 ────────────────────────────────────────────────────
with tab2:
    st.subheader("인플레이션 & 경기")
    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, "CPIAUCSL", "미국 CPI", "index")
    kpi_card(c2, "PCEPI", "미국 PCE", "index")
    kpi_card(c3, "UNRATE", "실업률", "%")
    kpi_card(c4, "UMCSENT", "소비자심리(미시건)", "index")

    st.divider()

    col_l, col_r = st.columns(2)
    with col_l:
        df_cpi = load_history("CPIAUCSL", 365)
        df_pce = load_history("PCEPI", 365)
        fig = go.Figure()
        for df, name in [(df_cpi, "CPI"), (df_pce, "PCE")]:
            if not df.empty:
                fig.add_trace(go.Scatter(x=df["date"], y=df["value"], name=name))
        fig.update_layout(title="CPI / PCE 추이", height=300, margin=dict(l=0,r=0,t=40,b=0), hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        col_l2, col_r2 = st.columns(2)
        with col_l2:
            st.plotly_chart(line_chart("UNRATE", "실업률 (%)", "%"), use_container_width=True)
        with col_r2:
            st.plotly_chart(line_chart("UMCSENT", "소비자심리지수", "index"), use_container_width=True)

# ── 탭 3: 한국/원자재 ────────────────────────────────────────────────────────
with tab3:
    st.subheader("한국 경제 & 원자재")
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    kpi_card(c1, "KRW=X", "원/달러 환율", "KRW")
    kpi_card(c2, "722Y001", "한국 기준금리", "%")
    kpi_card(c3, "901Y009", "한국 CPI", "index")
    kpi_card(c4, "403Y001", "수출금액지수", "index")
    kpi_card(c5, "CL=F", "WTI 유가", "USD")
    kpi_card(c6, "GC=F", "금 가격", "USD")

    st.divider()

    col_l, col_r = st.columns(2)
    with col_l:
        st.plotly_chart(line_chart("KRW=X", "원/달러 환율", "KRW"), use_container_width=True)
        st.plotly_chart(line_chart("403Y001", "한국 수출금액지수", "index", limit=60), use_container_width=True)
    with col_r:
        df_oil = load_history("CL=F", 365)
        df_gold = load_history("GC=F", 365)
        fig = go.Figure()
        for df, name, color in [(df_oil, "WTI 유가", "orange"), (df_gold, "금 가격", "gold")]:
            if not df.empty:
                fig.add_trace(go.Scatter(x=df["date"], y=df["value"], name=name, line=dict(color=color)))
        fig.update_layout(title="원자재 가격 추이", height=300, margin=dict(l=0,r=0,t=40,b=0), hovermode="x unified", yaxis2=dict(overlaying="y", side="right"))
        st.plotly_chart(fig, use_container_width=True)

        df_krbo = load_history("722Y001", limit=60)
        df_krcpi = load_history("901Y009", limit=60)
        fig2 = go.Figure()
        for df, name in [(df_krbo, "한국 기준금리(%)"), (df_krcpi, "한국 CPI(index)")]:
            if not df.empty:
                fig2.add_trace(go.Scatter(x=df["date"], y=df["value"], name=name))
        fig2.update_layout(title="한국 금리 & CPI", height=300, margin=dict(l=0,r=0,t=40,b=0), hovermode="x unified")
        st.plotly_chart(fig2, use_container_width=True)

# ── 탭 4: 반도체/주식 ────────────────────────────────────────────────────────
with tab4:
    st.subheader("반도체 & 주식시장")

    c1, c2, c3, c4 = st.columns(4)
    kpi_card(c1, "^SOX", "필라델피아 반도체", "index")
    kpi_card(c2, "NVDA", "엔비디아", "USD")
    kpi_card(c3, "005930.KS", "삼성전자", "KRW")
    kpi_card(c4, "000660.KS", "SK하이닉스", "KRW")

    c5, c6, c7, c8 = st.columns(4)
    kpi_card(c5, "^GSPC", "S&P 500", "index")
    kpi_card(c6, "^IXIC", "나스닥", "index")
    kpi_card(c7, "^KS11", "코스피", "index")
    kpi_card(c8, "^KQ11", "코스닥", "index")

    st.divider()

    col_l, col_r = st.columns(2)

    with col_l:
        # 반도체 비교 (정규화)
        semi_tickers = [("^SOX", "SOX"), ("NVDA", "NVDA"), ("005930.KS", "삼성전자"), ("000660.KS", "SK하이닉스")]
        fig = go.Figure()
        for ticker, label in semi_tickers:
            df = load_history(ticker, 365)
            if df.empty:
                continue
            base = df["value"].iloc[0]
            df["norm"] = (df["value"] / base - 1) * 100
            fig.add_trace(go.Scatter(x=df["date"], y=df["norm"], name=label))
        fig.update_layout(title="반도체 관련주 수익률 비교 (%)", height=350, margin=dict(l=0,r=0,t=40,b=0), hovermode="x unified", yaxis_ticksuffix="%")
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        # 글로벌 지수 비교
        idx_tickers = [("^GSPC", "S&P500"), ("^IXIC", "나스닥"), ("^KS11", "코스피"), ("^KQ11", "코스닥")]
        fig2 = go.Figure()
        for ticker, label in idx_tickers:
            df = load_history(ticker, 365)
            if df.empty:
                continue
            base = df["value"].iloc[0]
            df["norm"] = (df["value"] / base - 1) * 100
            fig2.add_trace(go.Scatter(x=df["date"], y=df["norm"], name=label))
        fig2.update_layout(title="글로벌 지수 수익률 비교 (%)", height=350, margin=dict(l=0,r=0,t=40,b=0), hovermode="x unified", yaxis_ticksuffix="%")
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # 등락률 히트맵
    st.subheader("최근 등락률 히트맵")
    latest_df = load_all_latest()
    stock_tickers = ["^SOX", "NVDA", "005930.KS", "000660.KS", "^GSPC", "^IXIC", "^KS11", "^KQ11"]
    heat_data = []
    for ticker in stock_tickers:
        df = load_history(ticker, 30)
        if len(df) < 2:
            continue
        latest_row = latest_df[latest_df["ticker"] == ticker]
        name = latest_row["name"].values[0] if not latest_row.empty else ticker
        chg_1d = (df["value"].iloc[-1] / df["value"].iloc[-2] - 1) * 100 if len(df) >= 2 else 0
        chg_5d = (df["value"].iloc[-1] / df["value"].iloc[-5] - 1) * 100 if len(df) >= 5 else 0
        chg_1m = (df["value"].iloc[-1] / df["value"].iloc[0] - 1) * 100 if len(df) >= 20 else 0
        heat_data.append({"종목": name, "1일(%)": round(chg_1d, 2), "5일(%)": round(chg_5d, 2), "1개월(%)": round(chg_1m, 2)})

    if heat_data:
        heat_df = pd.DataFrame(heat_data).set_index("종목")
        fig_heat = px.imshow(
            heat_df,
            color_continuous_scale="RdYlGn",
            color_continuous_midpoint=0,
            text_auto=True,
            aspect="auto",
        )
        fig_heat.update_layout(height=300, margin=dict(l=0,r=0,t=20,b=0))
        st.plotly_chart(fig_heat, use_container_width=True)
