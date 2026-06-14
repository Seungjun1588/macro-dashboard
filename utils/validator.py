BOUNDS = {
    "FEDFUNDS":   (0, 30),
    "GS10":       (0, 25),
    "GS2":        (0, 25),
    "10Y2Y_SPREAD": (-5, 10),
    "CPIAUCSL":   (0, 500),
    "PCEPI":      (0, 500),
    "UNRATE":     (0, 30),
    "UMCSENT":    (0, 150),
    "DX-Y.NYB":   (50, 200),
    "KRW=X":      (500, 3000),
    "CL=F":       (0, 300),
    "GC=F":       (100, 10000),
    "^KS11":      (100, 10000),
    "^KQ11":      (100, 5000),
    "^GSPC":      (100, 20000),
    "^IXIC":      (100, 50000),
    "^SOX":       (100, 15000),
    "005930.KS":  (1000, 200000),
    "000660.KS":  (10000, 1000000),
    "NVDA":       (1, 5000),
}


def validate(ticker: str, value: float) -> bool:
    if value is None:
        return False
    bounds = BOUNDS.get(ticker)
    if bounds is None:
        return True
    lo, hi = bounds
    return lo <= value <= hi
