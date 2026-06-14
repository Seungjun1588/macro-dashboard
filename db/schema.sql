CREATE TABLE IF NOT EXISTS indicators (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker      TEXT NOT NULL,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL,
    unit        TEXT NOT NULL,
    date        TEXT NOT NULL,
    value       REAL NOT NULL,
    collected_at TEXT NOT NULL,
    UNIQUE(ticker, date)
);

CREATE INDEX IF NOT EXISTS idx_ticker_date ON indicators(ticker, date);
CREATE INDEX IF NOT EXISTS idx_category ON indicators(category);
