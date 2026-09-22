from unittest.mock import MagicMock, patch

import pandas as pd

from data_generation.generate_market_data import build_dim_tickers, fetch_ohlcv, to_raw_market_prices


def _mock_history_df():
    return pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-02", "2024-01-03"]),
            "Open": [100.0, 101.0],
            "High": [102.0, 103.0],
            "Low": [99.0, 100.0],
            "Close": [101.5, 102.5],
            "Volume": [1000000, 1100000],
        }
    )


def test_fetch_ohlcv_tolerates_individual_failures():
    good_ticker = MagicMock()
    good_ticker.history.return_value = _mock_history_df()

    bad_ticker = MagicMock()
    bad_ticker.history.side_effect = RuntimeError("network error")

    def fake_ticker(symbol):
        return good_ticker if symbol == "AAPL" else bad_ticker

    with patch("data_generation.generate_market_data.yf.Ticker", side_effect=fake_ticker):
        df, failed = fetch_ohlcv(["AAPL", "BADTICKER"], "2024-01-01", "2024-01-05")

    assert failed == ["BADTICKER"]
    assert set(df["ticker"]) == {"AAPL"}
    assert len(df) == 2


def test_to_raw_market_prices_shapes_columns():
    raw = _mock_history_df()
    raw["ticker"] = "AAPL"

    out = to_raw_market_prices(raw, source_file="fact_market_prices.csv")

    assert list(out.columns) == [
        "ticker",
        "price_date",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "_loaded_at",
        "_source_file",
    ]
    assert len(out) == 2
    assert out["ticker"].unique().tolist() == ["AAPL"]
    assert out["_source_file"].unique().tolist() == ["fact_market_prices.csv"]


def test_build_dim_tickers_falls_back_for_unknown_ticker():
    out = build_dim_tickers(["AAPL", "ZZZZ_UNKNOWN"])
    assert set(out["ticker"]) == {"AAPL", "ZZZZ_UNKNOWN"}
    unknown_row = out.loc[out["ticker"] == "ZZZZ_UNKNOWN"].iloc[0]
    assert unknown_row["sector"] == "Unknown"
