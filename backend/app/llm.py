"""Claude API calls: NL question -> SQL, and SQL result rows -> NL answer.

Uses Haiku (cheapest current Claude model) for both calls — the project
spec's $0 budget constraint explicitly asks for "smaller/cheaper models and
short prompts where possible" (section 1a) to keep LLM spend near-zero.
"""

import os
import re
from typing import NamedTuple

import anthropic

MODEL = "claude-haiku-4-5"

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


SQL_SYSTEM_PROMPT = """You are a SQL generator for a Snowflake financial data warehouse.

Given a user's question and the schema below, output ONLY a single valid
Snowflake SQL SELECT statement (optionally starting with WITH) that answers
the question. No explanation, no markdown code fences, no semicolon, no
prose before or after the SQL.

When comparing multiple tickers ("compare X and Y", "X vs Y vs Z"), prefer
one aggregated row per ticker (e.g. average/min/max close, latest close,
volatility) over raw per-day rows — a flat LIMIT can otherwise return rows
for only the alphabetically-first ticker and starve the others out of the
result entirely. Only return per-day rows if the user explicitly asks for
daily detail or a date range.

To get the "latest" or "first" value of a column alongside GROUP BY
aggregates, use MAX_BY(column, order_column) / MIN_BY(column,
order_column) — never a window function (anything with OVER (...)) mixed
into a query that also has GROUP BY; Snowflake frequently rejects that
combination as an invalid group by expression. Example of the correct
pattern:
SELECT TICKER, AVG(CLOSE) AS avg_close, MAX_BY(CLOSE, PRICE_DATE) AS latest_close
FROM FACT_MARKET_PRICES WHERE TICKER IN (...) GROUP BY TICKER

If the question cannot be answered with the given schema, output exactly:
SELECT 'UNANSWERABLE: <brief reason>' AS error"""


def generate_sql(question: str, schema_description: str) -> str:
    client = _get_client()
    # No `temperature` param — the installed anthropic SDK (1.x) removed
    # top-level sampling params entirely, not just for thinking-enabled models.
    message = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=f"{SQL_SYSTEM_PROMPT}\n\n{schema_description}",
        messages=[{"role": "user", "content": question}],
    )
    sql = next((b.text for b in message.content if b.type == "text"), "").strip()
    return _strip_code_fences(sql)


def _strip_code_fences(sql: str) -> str:
    sql = sql.strip()
    if sql.startswith("```"):
        lines = sql.splitlines()
        lines = lines[1:] if lines else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        sql = "\n".join(lines).strip()
    return sql


ANSWER_SYSTEM_PROMPT = """You answer questions about financial data in plain
English, given the user's original question, the SQL query that was run,
and the resulting rows. Be concise (1-3 sentences). Use the actual numbers
from the rows — don't round unnecessarily. If the rows are empty, say so
plainly rather than guessing."""


def generate_answer(question: str, sql: str, columns: list[str], rows: list[tuple]) -> str:
    client = _get_client()
    rows_preview = rows[:20]  # cap prompt size regardless of how many rows matched
    rows_text = "\n".join(str(dict(zip(columns, r, strict=False))) for r in rows_preview)
    user_content = (
        f"Question: {question}\n\nSQL: {sql}\n\n"
        f"Results ({len(rows)} rows total, showing up to 20):\n{rows_text}"
    )
    message = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=ANSWER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    return next((b.text for b in message.content if b.type == "text"), "").strip()


INTENT_SYSTEM_PROMPT = """Given a user's question about financial markets, decide:

1. Does answering it well require recent NEWS or an explanation of *why*
something happened — not just historical price/volume/transaction data
that a SQL query over a price warehouse could compute directly?

Data questions (NEEDS_NEWS: NO) include: price lookups, comparisons
between two or more tickers ("compare AAPL and MSFT", "which is doing
better, X or Y"), aggregates, rankings, trends over a date range — even
when phrased casually. These stay NO even when multiple companies are
named, as long as the question is about their price/volume data, not an
explanation of events.

News questions (NEEDS_NEWS: YES) include: "why is X moving/up/down",
"what's the latest news on X", "what happened to X today", "why is the
market up/down".

2. If NEEDS_NEWS is YES, what single stock ticker (standard symbol, e.g.
AAPL) is the question about? If it's a market-wide question naming no
specific company, use SPY. If NEEDS_NEWS is NO, leave this blank.

Respond in exactly this format, nothing else:
NEEDS_NEWS: YES or NO
TICKER: <TICKER or NONE>"""


class Intent(NamedTuple):
    needs_news: bool
    ticker: str | None


def classify_intent(question: str) -> Intent:
    client = _get_client()
    message = client.messages.create(
        model=MODEL,
        max_tokens=20,
        system=INTENT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": question}],
    )
    text = next((b.text for b in message.content if b.type == "text"), "").upper()
    needs_news = "NEEDS_NEWS: YES" in text
    match = re.search(r"TICKER:\s*([A-Z.\-]+)", text)
    ticker = match.group(1) if match else None
    if ticker == "NONE":
        ticker = None
    return Intent(needs_news=needs_news, ticker=ticker)


NEWS_ANSWER_SYSTEM_PROMPT = """You answer questions about why a stock or the
market is moving, using ONLY the real news headlines provided below — never
your own general knowledge or training data about this company or event.
Be concise (2-4 sentences). Cite which headline(s) support your answer by
naming the publisher. If none of the provided headlines are relevant to the
question, say plainly that no relevant recent news was found — do not guess
or fabricate a reason."""


def generate_news_answer(question: str, ticker: str, articles: list[dict]) -> str:
    client = _get_client()
    if not articles:
        articles_text = "(no recent articles available)"
    else:
        articles_text = "\n".join(f'- "{a["title"]}" ({a["publisher"]}, {a["pub_date"]})' for a in articles)
    user_content = f"Question: {question}\n\nTicker: {ticker}\n\nRecent headlines:\n{articles_text}"
    message = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=NEWS_ANSWER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )
    return next((b.text for b in message.content if b.type == "text"), "").strip()
