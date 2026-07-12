import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import sqlite3

from macro_health_check import _expected_tickers
from config import DB_PATH

DAILY_NOTABLE_PCT = 3.0
MONTHLY_NOTABLE_PCT = 2.0


def snapshot():
    tickers = _expected_tickers()
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

    by_category = {}
    for ticker, meta in tickers.items():
        rows = conn.execute(
            "SELECT date, value FROM indicators WHERE ticker = ? ORDER BY date DESC LIMIT 2",
            (ticker,),
        ).fetchall()
        if not rows:
            continue

        latest_date, latest_value = rows[0]
        prev_value = rows[1][1] if len(rows) > 1 else None

        change_pct = None
        if prev_value not in (None, 0):
            change_pct = (latest_value - prev_value) / abs(prev_value) * 100

        notable = False
        if ticker == "10Y2Y_SPREAD" and latest_value < 0:
            notable = True
        elif change_pct is not None:
            threshold = DAILY_NOTABLE_PCT if meta["freq"] == "D" else MONTHLY_NOTABLE_PCT
            if abs(change_pct) > threshold:
                notable = True

        by_category.setdefault(meta["category"], []).append({
            "ticker": ticker,
            "name": meta["name"],
            "date": latest_date,
            "value": latest_value,
            "change_pct": change_pct,
            "notable": notable,
        })

    conn.close()
    return by_category


def render(by_category):
    lines = ["## 최신 지표 스냅샷", ""]
    for category, items in by_category.items():
        lines.append(f"### {category}")
        for item in items:
            tag = " [NOTABLE]" if item["notable"] else ""
            change = f", 변화 {item['change_pct']:+.2f}%" if item["change_pct"] is not None else ""
            lines.append(
                f"- `{item['ticker']}` ({item['name']}): {item['value']} ({item['date']}){change}{tag}"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    print(render(snapshot()))
