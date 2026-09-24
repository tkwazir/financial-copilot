"""FastAPI NL-to-SQL backend for the Financial Copilot.

Flow (spec section 6): question -> schema-aware Claude call -> SQL ->
validation/guardrail layer -> execute read-only against Snowflake -> second
Claude call turning rows into a plain-English answer. Every generated query
is logged with its accept/reject outcome regardless of what happens next.
"""

import re
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from backend.app import db, llm, query_log, validate  # noqa: E402
from backend.app.schema_context import fetch_schema_description  # noqa: E402

_schema_description_cache: str | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _schema_description_cache
    _schema_description_cache = fetch_schema_description()
    yield


app = FastAPI(title="Financial Copilot NL-to-SQL API", lifespan=lifespan)


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    question: str
    sql: str
    accepted: bool
    rejection_reason: str | None = None
    answer: str | None = None
    row_count: int | None = None
    elapsed_ms: int


TICKER_PATTERN = re.compile(r"^[A-Z.]{1,10}$")


class PricePoint(BaseModel):
    date: str
    close: float


class ChartResponse(BaseModel):
    ticker: str
    prices: list[PricePoint]


class TickerQuote(BaseModel):
    ticker: str
    close: float
    change: float
    change_pct: float
    sparkline: list[float]


class TickersResponse(BaseModel):
    quotes: list[TickerQuote]


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/chart/{ticker}", response_model=ChartResponse)
def chart(ticker: str) -> ChartResponse:
    """Full daily-close price history for one ticker — a fixed, parameterized,
    non-LLM-generated query (no guardrail layer needed), used by the frontend
    to render an interactive price chart alongside the NL answer."""
    ticker_clean = ticker.strip().upper()
    if not TICKER_PATTERN.match(ticker_clean):
        return ChartResponse(ticker=ticker_clean, prices=[])

    _, rows = db.run_query(
        "SELECT PRICE_DATE, CLOSE FROM FACT_MARKET_PRICES WHERE TICKER = %s ORDER BY PRICE_DATE",
        (ticker_clean,),
    )
    prices = [PricePoint(date=str(r[0]), close=float(r[1])) for r in rows]
    return ChartResponse(ticker=ticker_clean, prices=prices)


@app.get("/tickers", response_model=TickersResponse)
def tickers() -> TickersResponse:
    """Latest close + day change + a short recent-close sparkline for every
    ticker — powers the scrolling ticker tape. Fixed query, no LLM involved."""
    _, rows = db.run_query("""
        WITH ranked AS (
            SELECT TICKER, PRICE_DATE, CLOSE,
                   ROW_NUMBER() OVER (PARTITION BY TICKER ORDER BY PRICE_DATE DESC) AS rn
            FROM FACT_MARKET_PRICES
            WHERE CLOSE IS NOT NULL
        )
        SELECT TICKER, PRICE_DATE, CLOSE
        FROM ranked
        WHERE rn <= 20
        ORDER BY TICKER, PRICE_DATE
    """)

    by_ticker: dict[str, list[float]] = {}
    for ticker, _price_date, close in rows:
        by_ticker.setdefault(ticker, []).append(float(close))

    quotes = []
    for ticker in sorted(by_ticker):
        closes = by_ticker[ticker]
        if len(closes) < 2:
            continue
        latest, prev = closes[-1], closes[-2]
        change = latest - prev
        change_pct = (change / prev * 100) if prev else 0.0
        quotes.append(
            TickerQuote(ticker=ticker, close=latest, change=change, change_pct=change_pct, sparkline=closes)
        )
    return TickersResponse(quotes=quotes)


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    start = time.monotonic()
    schema_description = _schema_description_cache or fetch_schema_description()

    generated_sql = llm.generate_sql(req.question, schema_description)
    result = validate.validate_sql(generated_sql)

    query_log.log_query(req.question, generated_sql, result.accepted, result.reason, result.safe_sql)

    if not result.accepted:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return QueryResponse(
            question=req.question,
            sql=generated_sql,
            accepted=False,
            rejection_reason=result.reason,
            elapsed_ms=elapsed_ms,
        )

    columns, rows = db.run_query(result.safe_sql)
    answer = llm.generate_answer(req.question, result.safe_sql, columns, rows)

    elapsed_ms = int((time.monotonic() - start) * 1000)
    return QueryResponse(
        question=req.question,
        sql=result.safe_sql,
        accepted=True,
        answer=answer,
        row_count=len(rows),
        elapsed_ms=elapsed_ms,
    )
