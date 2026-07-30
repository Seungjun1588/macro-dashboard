import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from utils.db import init_db
from collectors import fred, market, ecos
from utils.notifier import send_error
from datetime import datetime


SOURCES = [("FRED", fred), ("Market", market), ("ECOS", ecos)]


def run() -> int:
    """수집을 실행하고 실패한 소스 수를 돌려준다.

    소스 하나가 티커를 하나도 저장하지 못하면 '전멸'로 본다. 티커별
    예외는 각 수집기가 잡아 넘기므로, 그것만으로는 전체가 실패해도
    프로세스가 성공으로 끝난다 — 실제로 yfinance가 3주간 그렇게
    조용히 죽어 있었다.
    """
    print(f"\n=== 수집 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
    init_db()

    total = 0
    failed = []

    for label, collector in SOURCES:
        try:
            r = collector.collect()
        except Exception as e:
            send_error(f"{label} 수집 전체 실패", str(e))
            print(f"  [{label}] 전체 실패: {e}")
            failed.append(label)
            continue

        saved = sum(r.values())
        total += saved
        dead = [ticker for ticker, n in r.items() if n == 0]

        if saved == 0:
            send_error(f"{label} 전멸", f"{len(r)}개 티커 전부 0건 저장")
            print(f"  [{label}] 전멸: {len(r)}개 티커 전부 0건")
            failed.append(label)
        elif dead:
            send_error(f"{label} 일부 실패", f"0건 티커: {', '.join(dead)}")
            print(f"  [{label}] 경고: 0건 티커 {len(dead)}개 — {', '.join(dead)}")

    print(f"=== 수집 완료: 총 {total}건 저장 ===")
    if failed:
        print(f"=== 실패한 소스: {', '.join(failed)} ===\n")
    else:
        print()
    return len(failed)


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
