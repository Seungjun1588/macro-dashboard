import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime
import sqlite3

from config import (
    DB_PATH,
    FRED_INDICATORS,
    YFINANCE_INDICATORS,
    ECOS_INDICATORS,
    SPREAD_INDICATOR,
)

# 월간 시계열은 관측치가 그 달 1일자로 찍히고 다음 달 초에 발표된다.
# 즉 정상 상태에서도 월말이면 60일 가까이 벌어진다 — 45일은 상시 오탐이었다.
# 70일이면 발표 지연은 통과시키고 한 달을 통째로 놓친 경우(~90일)는 잡는다.
MONTHLY_STALE_DAYS = 70
DAILY_STALE_DAYS = 7

# 같은 날 FRED에 함께 요청해도 CPI·실업률은 6월치가 오는데 이 둘은 5월치가
# 최신이다 — 누락이 아니라 발표가 한 달 더 느린 계열이라 따로 잡아준다.
SLOW_MONTHLY_STALE_DAYS = {
    "PCEPI": 100,
    "UMCSENT": 100,
}


def _expected_tickers():
    tickers = {}
    for source, freq in (
        (FRED_INDICATORS, "M"),
        (ECOS_INDICATORS, "M"),
        (SPREAD_INDICATOR, "M"),
        (YFINANCE_INDICATORS, "D"),
    ):
        for ticker, meta in source.items():
            tickers[ticker] = {"name": meta["name"], "category": meta["category"], "freq": freq}
    return tickers


def check():
    today = datetime.utcnow().date()
    tickers = _expected_tickers()
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

    never_collected = []
    stale = []
    ok_count = 0

    for ticker, meta in tickers.items():
        last_date, total_rows = conn.execute(
            "SELECT MAX(date), COUNT(*) FROM indicators WHERE ticker = ?", (ticker,)
        ).fetchone()
        total_rows = total_rows or 0

        if total_rows == 0:
            never_collected.append((ticker, meta))
            continue

        last = datetime.strptime(last_date[:10], "%Y-%m-%d").date()
        days_since = (today - last).days
        default = MONTHLY_STALE_DAYS if meta["freq"] == "M" else DAILY_STALE_DAYS
        threshold = SLOW_MONTHLY_STALE_DAYS.get(ticker, default)

        if days_since > threshold:
            stale.append((ticker, meta, last, days_since))
        else:
            ok_count += 1

    conn.close()
    return today, never_collected, stale, ok_count, len(tickers)


def render(today, never_collected, stale, ok_count, total):
    lines = [f"## 데이터 수집 헬스체크 ({today.isoformat()})", ""]

    if not never_collected and not stale:
        lines.append(f"이상 없음, 총 {total}개 티커 정상")
        return "\n".join(lines) + "\n"

    if never_collected:
        lines.append(f"### [NEVER_COLLECTED] 한 번도 수집되지 않음 ({len(never_collected)})")
        for ticker, meta in never_collected:
            lines.append(f"- `{ticker}` ({meta['name']}, {meta['category']})")
        lines.append("")

    if stale:
        lines.append(f"### [STALE] 최신 데이터 지연 ({len(stale)})")
        for ticker, meta, last, days_since in stale:
            lines.append(
                f"- `{ticker}` ({meta['name']}): 마지막 {last.isoformat()}, 기준 대비 {days_since}일 지연"
            )
        lines.append("")

    lines.append(f"### [OK] 정상: {ok_count}개 티커")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    # 기본은 항상 0으로 끝난다 — 스킬·에이전트가 리포트를 읽으려고 호출하는데
    # 종료 코드로 실패를 알리면 그쪽이 깨진다. CI만 --strict로 게이트를 건다.
    today, never_collected, stale, ok_count, total = check()
    print(render(today, never_collected, stale, ok_count, total))

    if "--strict" in sys.argv and (never_collected or stale):
        print(
            f"[STRICT] 문제 {len(never_collected) + len(stale)}건 — "
            f"NEVER_COLLECTED {len(never_collected)}, STALE {len(stale)}",
            file=sys.stderr,
        )
        sys.exit(1)
