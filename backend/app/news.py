"""Fetches real, attributed news headlines via yfinance's `.news` property —
no new API key, no new signup, the same free library already used for price
data. Returns real publisher names, timestamps, and clickable source URLs so
the LLM answer built on top of this can cite verifiable sources instead of
answering from unsourced model knowledge.
"""

import yfinance as yf


def fetch_news(ticker: str, limit: int = 8) -> list[dict]:
    try:
        raw = yf.Ticker(ticker).news or []
    except Exception:  # noqa: BLE001 - a flaky/missing news response shouldn't crash the request
        raw = []

    articles = []
    for item in raw[:limit]:
        content = item.get("content", {})
        provider = content.get("provider") or {}
        canonical = content.get("canonicalUrl") or {}
        click = content.get("clickThroughUrl") or {}
        url = canonical.get("url") or click.get("url") or ""
        title = content.get("title", "")
        if not title or not url:
            continue
        articles.append(
            {
                "title": title,
                "publisher": provider.get("displayName", "Unknown"),
                "url": url,
                "pub_date": content.get("pubDate", ""),
                "summary": content.get("summary", ""),
            }
        )
    return articles
