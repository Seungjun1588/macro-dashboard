import os
from dotenv import load_dotenv

load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY")
ECOS_API_KEY = os.getenv("ECOS_API_KEY")
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

DB_PATH = os.path.join(os.path.dirname(__file__), "db", "macro.db")

FRED_INDICATORS = {
    "FEDFUNDS": {"name": "미국 기준금리", "category": "글로벌 금융", "unit": "%", "freq": "M"},
    "GS10":     {"name": "미국 10년물 국채", "category": "글로벌 금융", "unit": "%", "freq": "M"},
    "GS2":      {"name": "미국 2년물 국채", "category": "글로벌 금융", "unit": "%", "freq": "M"},
    "CPIAUCSL": {"name": "미국 CPI", "category": "인플레이션/경기", "unit": "index", "freq": "M"},
    "PCEPI":    {"name": "미국 PCE", "category": "인플레이션/경기", "unit": "index", "freq": "M"},
    "UNRATE":   {"name": "미국 실업률", "category": "인플레이션/경기", "unit": "%", "freq": "M"},
    "UMCSENT":  {"name": "미시건대 소비자심리", "category": "인플레이션/경기", "unit": "index", "freq": "M"},
}

YFINANCE_INDICATORS = {
    "DX-Y.NYB": {"name": "달러 인덱스", "category": "글로벌 금융", "unit": "index"},
    "KRW=X":    {"name": "원/달러 환율", "category": "한국/원자재", "unit": "KRW"},
    "CL=F":     {"name": "WTI 유가", "category": "한국/원자재", "unit": "USD"},
    "GC=F":     {"name": "금 가격", "category": "한국/원자재", "unit": "USD"},
    "^KS11":    {"name": "코스피", "category": "반도체/주식", "unit": "index"},
    "^KQ11":    {"name": "코스닥", "category": "반도체/주식", "unit": "index"},
    "^GSPC":    {"name": "S&P 500", "category": "반도체/주식", "unit": "index"},
    "^IXIC":    {"name": "나스닥", "category": "반도체/주식", "unit": "index"},
    "^SOX":     {"name": "필라델피아 반도체(SOX)", "category": "반도체/주식", "unit": "index"},
    "005930.KS":{"name": "삼성전자", "category": "반도체/주식", "unit": "KRW"},
    "000660.KS":{"name": "SK하이닉스", "category": "반도체/주식", "unit": "KRW"},
    "NVDA":     {"name": "엔비디아", "category": "반도체/주식", "unit": "USD"},
}

TICKER_COLORS = {
    "FEDFUNDS":     "#E63946",
    "GS10":         "#457B9D",
    "GS2":          "#F4A261",
    "10Y2Y_SPREAD": "#2A9D8F",
    "DX-Y.NYB":     "#6A4C93",
    "CPIAUCSL":     "#4A9EFF",
    "PCEPI":        "#E63946",
    "UNRATE":       "#F59E0B",
    "UMCSENT":      "#2A9D8F",
    "KRW=X":        "#E76F51",
    "CL=F":         "#F4A261",
    "GC=F":         "#FFD700",
    "722Y001":      "#457B9D",
    "901Y009":      "#E76F51",
    "403Y001":      "#34D399",
    "^SOX":         "#264653",
    "NVDA":         "#76C442",
    "005930.KS":    "#1428A0",
    "000660.KS":    "#EA0029",
    "^GSPC":        "#4A9EFF",
    "^IXIC":        "#A78BFA",
    "^KS11":        "#34D399",
    "^KQ11":        "#FBBF24",
}

# 장단기 금리차는 수집 후 자체 계산
SPREAD_INDICATOR = {
    "10Y2Y_SPREAD": {"name": "장단기 금리차(10Y-2Y)", "category": "글로벌 금융", "unit": "%"}
}

ECOS_INDICATORS = {
    "403Y001": {
        "name": "한국 수출금액지수",
        "category": "한국/원자재",
        "unit": "index",
        "freq": "M",
        "item_code": "*AA",
    },
    "722Y001": {
        "name": "한국 기준금리",
        "category": "한국/원자재",
        "unit": "%",
        "freq": "M",
        "item_code": "0101000",
    },
    "901Y009": {
        "name": "한국 CPI",
        "category": "한국/원자재",
        "unit": "index",
        "freq": "M",
        "item_code": "0",
    },
}
