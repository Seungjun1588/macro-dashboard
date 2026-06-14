import sqlite3
from datetime import datetime
from config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    import os
    schema_path = os.path.join(os.path.dirname(DB_PATH), "schema.sql")
    with get_conn() as conn:
        with open(schema_path, "r") as f:
            conn.executescript(f.read())


def upsert(ticker: str, name: str, category: str, unit: str, records: list[tuple]):
    """records: list of (date_str, value)"""
    now = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = [
        (ticker, name, category, unit, date, value, now)
        for date, value in records
        if value is not None
    ]
    if not rows:
        return 0
    with get_conn() as conn:
        conn.executemany(
            """INSERT INTO indicators (ticker, name, category, unit, date, value, collected_at)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(ticker, date) DO UPDATE SET value=excluded.value, collected_at=excluded.collected_at""",
            rows,
        )
    return len(rows)


def latest(ticker: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM indicators WHERE ticker=? ORDER BY date DESC LIMIT 1", (ticker,)
        ).fetchone()
    return dict(row) if row else None


def history(ticker: str, limit: int = 365) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT date, value FROM indicators WHERE ticker=? ORDER BY date DESC LIMIT ?",
            (ticker, limit),
        ).fetchall()
    return [dict(r) for r in rows]
