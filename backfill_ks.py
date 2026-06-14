"""
삼성전자(005930.KS) / SK하이닉스(000660.KS) 누락 데이터 백필.
rate limit 해제 후 실행: python backfill_ks.py
"""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))

import yfinance as yf
from utils.db import init_db, upsert
from utils.validator import validate

TARGETS = {
    "005930.KS": {"name": "삼성전자", "category": "반도체/주식", "unit": "KRW"},
    "000660.KS": {"name": "SK하이닉스", "category": "반도체/주식", "unit": "KRW"},
}

START = "2026-04-01"  # DB 마지막 날짜 이후부터

def collect_one(ticker: str, meta: dict) -> int:
    df = yf.download(ticker, start=START, auto_adjust=True, progress=False)
    if df.empty:
        print(f"  [{ticker}] 데이터 없음 (rate limit 확인 필요)")
        return 0
    close = df["Close"]
    if hasattr(close, "squeeze"):
        close = close.squeeze()
    close = close.dropna()
    records = [
        (d.strftime("%Y-%m-%d"), round(float(v), 4))
        for d, v in close.items()
        if validate(ticker, float(v))
    ]
    saved = upsert(ticker, meta["name"], meta["category"], meta["unit"], records)
    print(f"  [{ticker}] {saved}건 저장 (최신: {records[-1][0] if records else '-'})")
    return saved

if __name__ == "__main__":
    init_db()
    print(f"백필 시작: {START} 이후 데이터")
    for i, (ticker, meta) in enumerate(TARGETS.items()):
        if i > 0:
            print("  2초 대기...")
            time.sleep(2)
        collect_one(ticker, meta)
    print("완료.")
