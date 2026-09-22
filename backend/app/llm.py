"""Claude API calls: NL question -> SQL, and SQL result rows -> NL answer.

Uses Haiku (cheapest current Claude model) for both calls — the project
spec's $0 budget constraint explicitly asks for "smaller/cheaper models and
short prompts where possible" (section 1a) to keep LLM spend near-zero.
"""

import os

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
