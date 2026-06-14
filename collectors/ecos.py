import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests
from datetime import datetime, timedelta
from config import ECOS_API_KEY, ECOS_INDICATORS
from utils.db import upsert
from utils.notifier import send_error

ECOS_BASE = "https://ecos.bok.or.kr/api/StatisticSearch"


def _fetch(stat_code: str, item_code: str, freq: str, start: str, end: str) -> list[tuple]:
    url = (
        f"{ECOS_BASE}/{ECOS_API_KEY}/json/kr/1/1000"
        f"/{stat_code}/{freq}/{start}/{end}/{item_code}"
    )
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        rows = data.get("StatisticSearch", {}).get("row", [])
        records = []
        for row in rows:
            raw_date = row.get("TIME", "")
            val_str = row.get("DATA_VALUE", "")
            if not raw_date or not val_str:
                continue
            try:
                value = float(val_str.replace(",", ""))
            except ValueError:
                continue
            # 월별(YYYYMM) → YYYY-MM-01
            if len(raw_date) == 6:
                date = f"{raw_date[:4]}-{raw_date[4:6]}-01"
            else:
                date = raw_date
            records.append((date, value))
        return records
    except Exception as e:
        raise RuntimeError(f"ECOS API 오류: {e}")


def collect(lookback_months: int = 36):
    end_dt = datetime.today()
    start_dt = end_dt - timedelta(days=lookback_months * 30)
    start = start_dt.strftime("%Y%m")
    end = end_dt.strftime("%Y%m")
    results = {}

    for stat_code, meta in ECOS_INDICATORS.items():
        try:
            records = _fetch(stat_code, meta["item_code"], meta["freq"], start, end)
            if not records:
                print(f"  [ECOS] {stat_code}: 데이터 없음 (item_code 확인 필요)")
                results[stat_code] = 0
                continue
            saved = upsert(stat_code, meta["name"], meta["category"], meta["unit"], records)
            results[stat_code] = saved
            print(f"  [ECOS] {stat_code} ({meta['name']}): {saved}건 저장")
        except Exception as e:
            send_error(f"ECOS 수집 실패: {stat_code}", str(e))
            print(f"  [ECOS] {stat_code} 오류: {e}")

    return results


if __name__ == "__main__":
    from utils.db import init_db
    init_db()
    collect()
