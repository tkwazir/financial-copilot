"""Pull daily OHLCV market data via yfinance and shape it to match the
eventual Snowflake RAW.FACT_MARKET_PRICES / RAW.DIM_TICKERS tables.

Usage:
    python -m data_generation.generate_market_data
    python -m data_generation.generate_market_data --tickers AAPL,MSFT --start 2024-01-01 --end 2024-12-31
"""

import argparse
from datetime import date, datetime, timedelta, timezone

import pandas as pd
import yfinance as yf

from data_generation.io_utils import resolve_out_dir, write_df, write_manifest
from data_generation.tickers import get_ticker_universe

SCRIPT_VERSION = "1.0.0"


def fetch_ohlcv(tickers: list[str], start: str, end: str) -> tuple[pd.DataFrame, list[str]]:
    """Fetch OHLCV per ticker, tolerating individual failures.

    Returns (long_format_df, failed_tickers).
    """
    frames = []
    failed = []
    for ticker in tickers:
        try:
            hist = yf.Ticker(ticker).history(start=start, end=end, interval="1d")
            if hist.empty:
                failed.append(ticker)
                continue
            hist = hist.reset_index()
            hist["ticker"] = ticker
            frames.append(hist)
        except Exception:
            failed.append(ticker)

    if not frames:
        return pd.DataFrame(), failed

    return pd.concat(frames, ignore_index=True), failed


def to_raw_market_prices(df: pd.DataFrame, source_file: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=["ticker", "price_date", "open", "high", "low", "close", "volume", "_loaded_at", "_source_file"]
        )

    out = pd.DataFrame(
        {
            "ticker": df["ticker"],
            "price_date": pd.to_datetime(df["Date"]).dt.date,
            "open": df["Open"].round(4),
            "high": df["High"].round(4),
            "low": df["Low"].round(4),
            "close": df["Close"].round(4),
            "volume": df["Volume"].astype("int64"),
        }
    )
    out["_loaded_at"] = datetime.now(timezone.utc).isoformat()
    out["_source_file"] = source_file
    return out.sort_values(["ticker", "price_date"]).reset_index(drop=True)


def build_dim_tickers(tickers: list[str]) -> pd.DataFrame:
    universe = {t["ticker"]: t for t in get_ticker_universe()}
    rows = [universe.get(t, {"ticker": t, "company_name": t, "sector": "Unknown"}) for t in tickers]
    return pd.DataFrame(rows, columns=["ticker", "company_name", "sector"])


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Generate synthetic-free market data via yfinance")
    parser.add_argument("--tickers", type=str, default=None, help="Comma-separated ticker list")
    default_end = date.today()
    default_start = default_end - timedelta(days=365 * 2)
    parser.add_argument("--start", type=str, default=default_start.isoformat())
    parser.add_argument("--end", type=str, default=default_end.isoformat())
    parser.add_argument("--out-dir", type=str, default="data/market")
    parser.add_argument("--format", type=str, default="csv", choices=["csv", "parquet"])
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    tickers = args.tickers.split(",") if args.tickers else [t["ticker"] for t in get_ticker_universe()]

    out_dir = resolve_out_dir(args.out_dir)
    source_file = f"fact_market_prices.{args.format}"

    raw, failed = fetch_ohlcv(tickers, args.start, args.end)
    prices_df = to_raw_market_prices(raw, source_file)
    tickers_df = build_dim_tickers(tickers)

    write_df(prices_df, out_dir / "fact_market_prices", args.format)
    write_df(tickers_df, out_dir / "dim_tickers", args.format)

    manifest = {
        "tickers_requested": tickers,
        "tickers_fetched": sorted(set(tickers) - set(failed)),
        "tickers_failed": failed,
        "date_range": {"start": args.start, "end": args.end},
        "row_count": len(prices_df),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "script_version": SCRIPT_VERSION,
    }
    write_manifest(manifest, out_dir / "_run_manifest.json")

    print(f"Wrote {len(prices_df)} price rows for {len(tickers) - len(failed)}/{len(tickers)} tickers to {out_dir}")
    if failed:
        print(f"Failed tickers: {failed}")


if __name__ == "__main__":
    main()
