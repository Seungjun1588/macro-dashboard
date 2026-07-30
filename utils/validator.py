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
    "^SOX":       (100, 50000),
    "005930.KS":  (1000, 1000000),
    "000660.KS":  (10000, 5000000),
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


def filter_valid(ticker: str, records: list[tuple]) -> tuple[list, list]:
    """records를 (통과, 탈락)으로 나눈다.

    탈락분을 호출자에게 돌려주는 게 요점이다. 걸러낸 값을 조용히 버리면
    범위 상한을 넘어선 정상 데이터(예: 주가 급등)와 진짜 이상치를
    구분할 수 없고, 수집은 계속 '성공'으로 보고된다.
    """
    kept, dropped = [], []
    for date, value in records:
        (kept if validate(ticker, value) else dropped).append((date, value))
    return kept, dropped


def describe_drops(ticker: str, dropped: list[tuple]) -> str:
    values = [v for _, v in dropped]
    lo, hi = BOUNDS.get(ticker, (None, None))
    return (
        f"{len(dropped)}건이 허용 범위({lo:,} ~ {hi:,})를 벗어나 제외됨: "
        f"{min(values):,.2f} ~ {max(values):,.2f} "
        f"(최근 {max(d for d, _ in dropped)})"
    )
