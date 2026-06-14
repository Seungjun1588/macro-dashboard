import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from utils.db import init_db
from collectors import fred, market, ecos
from utils.notifier import send_error
from datetime import datetime


def run():
    print(f"\n=== 수집 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    init_db()

    total = 0
    try:
        r = fred.collect()
        total += sum(r.values())
    except Exception as e:
        send_error("FRED 수집 전체 실패", str(e))

    try:
        r = market.collect()
        total += sum(r.values())
    except Exception as e:
        send_error("Market 수집 전체 실패", str(e))

    try:
        r = ecos.collect()
        total += sum(r.values())
    except Exception as e:
        send_error("ECOS 수집 전체 실패", str(e))

    print(f"=== 수집 완료: 총 {total}건 저장 ===\n")


if __name__ == "__main__":
    run()
