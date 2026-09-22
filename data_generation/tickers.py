"""Static ticker universe seeding DIM_TICKERS.

Kept static (not pulled from yfinance's `.info`) because that endpoint is
flaky/rate-limited; `.history()` (used for OHLCV) is the reliable one.
"""

DEFAULT_TICKERS: list[dict] = [
    # Technology
    {"ticker": "AAPL", "company_name": "Apple Inc.", "sector": "Technology"},
    {"ticker": "MSFT", "company_name": "Microsoft Corp.", "sector": "Technology"},
    {"ticker": "GOOGL", "company_name": "Alphabet Inc.", "sector": "Technology"},
    {"ticker": "NVDA", "company_name": "NVIDIA Corp.", "sector": "Technology"},
    {"ticker": "META", "company_name": "Meta Platforms Inc.", "sector": "Technology"},
    {"ticker": "CRM", "company_name": "Salesforce Inc.", "sector": "Technology"},
    {"ticker": "ORCL", "company_name": "Oracle Corp.", "sector": "Technology"},
    {"ticker": "ADBE", "company_name": "Adobe Inc.", "sector": "Technology"},
    # Financials
    {"ticker": "JPM", "company_name": "JPMorgan Chase & Co.", "sector": "Financials"},
    {"ticker": "BAC", "company_name": "Bank of America Corp.", "sector": "Financials"},
    {"ticker": "GS", "company_name": "Goldman Sachs Group Inc.", "sector": "Financials"},
    {"ticker": "V", "company_name": "Visa Inc.", "sector": "Financials"},
    {"ticker": "MA", "company_name": "Mastercard Inc.", "sector": "Financials"},
    # Healthcare
    {"ticker": "JNJ", "company_name": "Johnson & Johnson", "sector": "Healthcare"},
    {"ticker": "UNH", "company_name": "UnitedHealth Group Inc.", "sector": "Healthcare"},
    {"ticker": "PFE", "company_name": "Pfizer Inc.", "sector": "Healthcare"},
    {"ticker": "ABBV", "company_name": "AbbVie Inc.", "sector": "Healthcare"},
    # Energy
    {"ticker": "XOM", "company_name": "Exxon Mobil Corp.", "sector": "Energy"},
    {"ticker": "CVX", "company_name": "Chevron Corp.", "sector": "Energy"},
    {"ticker": "COP", "company_name": "ConocoPhillips", "sector": "Energy"},
    # Consumer
    {"ticker": "AMZN", "company_name": "Amazon.com Inc.", "sector": "Consumer"},
    {"ticker": "WMT", "company_name": "Walmart Inc.", "sector": "Consumer"},
    {"ticker": "COST", "company_name": "Costco Wholesale Corp.", "sector": "Consumer"},
    {"ticker": "MCD", "company_name": "McDonald's Corp.", "sector": "Consumer"},
    {"ticker": "NKE", "company_name": "Nike Inc.", "sector": "Consumer"},
    {"ticker": "SBUX", "company_name": "Starbucks Corp.", "sector": "Consumer"},
    # Industrials
    {"ticker": "BA", "company_name": "Boeing Co.", "sector": "Industrials"},
    {"ticker": "CAT", "company_name": "Caterpillar Inc.", "sector": "Industrials"},
    {"ticker": "UPS", "company_name": "United Parcel Service Inc.", "sector": "Industrials"},
    # Communication
    {"ticker": "DIS", "company_name": "Walt Disney Co.", "sector": "Communication Services"},
]


def get_ticker_universe() -> list[dict]:
    return DEFAULT_TICKERS
