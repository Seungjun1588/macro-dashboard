import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import time
import yfinance as yf
from datetime import datetime, timedelta
from config import YFINANCE_INDICATORS
from utils.db import upsert
from utils.validator import filter_valid, describe_drops
from utils.notifier import send_error


def collect(lookback_days: int = 365):
    start = (datetime.today() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    # 실패한 티커도 0으로 남긴다 — 호출자가 '전멸'을 판정할 수 있어야 한다
    results = {ticker: 0 for ticker in YFINANCE_INDICATORS}

    for ticker, meta in YFINANCE_INDICATORS.items():
        try:
            df = yf.download(ticker, start=start, auto_adjust=True, progress=False)
            if df.empty:
                send_error(f"yfinance 0건 응답: {ticker}", f"{start} 이후 데이터 없음")
                print(f"  [MARKET] {ticker}: 데이터 없음")
                continue
            close = df["Close"]
            if hasattr(close, "squeeze"):
                close = close.squeeze()
            close = close.dropna()
            records = [(d.strftime("%Y-%m-%d"), round(float(v), 4)) for d, v in close.items()]

            records, dropped = filter_valid(ticker, records)
            if dropped:
                detail = describe_drops(ticker, dropped)
                send_error(f"yfinance 범위 초과: {ticker}", detail)
                print(f"  [MARKET] {ticker} 경고: {detail}")

            saved = upsert(ticker, meta["name"], meta["category"], meta["unit"], records)
            results[ticker] = saved
            print(f"  [MARKET] {ticker}: {saved}건 저장")
            time.sleep(1)
        except Exception as e:
            send_error(f"yfinance 수집 실패: {ticker}", str(e))
            print(f"  [MARKET] {ticker} 오류: {e}")

    return results


if __name__ == "__main__":
    from utils.db import init_db
    init_db()
    collect()
