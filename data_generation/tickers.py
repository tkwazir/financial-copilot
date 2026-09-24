"""Ticker universe seeding DIM_TICKERS: the full S&P 500.

Loaded from a committed CSV snapshot (`sp500_constituents.csv`), not fetched
live at run time — keeps the generation script network-independent and
reproducible, and avoids re-hitting Wikipedia on every run. The snapshot was
built once from the live "List of S&P 500 companies" Wikipedia table via
`refresh_sp500_constituents()` below; re-run that function to update it.

Dotted symbols (e.g. `BRK.B`) are rewritten to yfinance's dash convention
(`BRK-B`) in the CSV already.
"""

import csv
from pathlib import Path

CONSTITUENTS_CSV = Path(__file__).resolve().parent / "sp500_constituents.csv"


def get_ticker_universe() -> list[dict]:
    with open(CONSTITUENTS_CSV, newline="") as f:
        return list(csv.DictReader(f))


def refresh_sp500_constituents(out_path: Path = CONSTITUENTS_CSV) -> int:
    """Re-fetches the live S&P 500 constituent list from Wikipedia and
    overwrites the CSV snapshot. Not called automatically — run manually
    (`python -c "from data_generation.tickers import refresh_sp500_constituents as r; r()"`)
    when the index membership needs updating. Returns the row count."""
    from io import StringIO

    import pandas as pd
    import requests

    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    headers = {"User-Agent": "Mozilla/5.0 (financial-copilot-portfolio-project; research use)"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()

    df = pd.read_html(StringIO(resp.text))[0][["Symbol", "Security", "GICS Sector"]].copy()
    df.columns = ["ticker", "company_name", "sector"]
    df["ticker"] = df["ticker"].str.replace(".", "-", regex=False)
    df = df.sort_values("ticker").reset_index(drop=True)
    df.to_csv(out_path, index=False)
    return len(df)
