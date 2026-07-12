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

MONTHLY_STALE_DAYS = 45
DAILY_STALE_DAYS = 7


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
        threshold = MONTHLY_STALE_DAYS if meta["freq"] == "M" else DAILY_STALE_DAYS

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
    print(render(*check()))
