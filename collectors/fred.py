import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from fredapi import Fred
from datetime import datetime, timedelta
from config import FRED_API_KEY, FRED_INDICATORS, SPREAD_INDICATOR
from utils.db import upsert
from utils.validator import validate
from utils.notifier import send_error


def collect(lookback_days: int = 365):
    fred = Fred(api_key=FRED_API_KEY)
    start = (datetime.today() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
    results = {}

    for ticker, meta in FRED_INDICATORS.items():
        try:
            series = fred.get_series(ticker, observation_start=start)
            records = [
                (d.strftime("%Y-%m-%d"), float(v))
                for d, v in series.dropna().items()
                if validate(ticker, float(v))
            ]
            saved = upsert(ticker, meta["name"], meta["category"], meta["unit"], records)
            results[ticker] = saved
            print(f"  [FRED] {ticker}: {saved}건 저장")
        except Exception as e:
            send_error(f"FRED 수집 실패: {ticker}", str(e))
            print(f"  [FRED] {ticker} 오류: {e}")

    _collect_spread(fred, start, results)
    return results


def _collect_spread(fred, start: str, results: dict):
    try:
        gs10 = fred.get_series("GS10", observation_start=start).dropna()
        gs2 = fred.get_series("GS2", observation_start=start).dropna()
        spread = (gs10 - gs2).dropna()
        meta = SPREAD_INDICATOR["10Y2Y_SPREAD"]
        records = [
            (d.strftime("%Y-%m-%d"), round(float(v), 4))
            for d, v in spread.items()
            if validate("10Y2Y_SPREAD", float(v))
        ]
        saved = upsert("10Y2Y_SPREAD", meta["name"], meta["category"], meta["unit"], records)
        results["10Y2Y_SPREAD"] = saved
        print(f"  [FRED] 10Y2Y_SPREAD: {saved}건 저장")
    except Exception as e:
        send_error("FRED 수집 실패: 장단기 금리차", str(e))
        print(f"  [FRED] 10Y2Y_SPREAD 오류: {e}")


if __name__ == "__main__":
    from utils.db import init_db
    init_db()
    collect()
