"""FastAPI NL-to-SQL backend for the Financial Copilot.

Flow (spec section 6): question -> schema-aware Claude call -> SQL ->
validation/guardrail layer -> execute read-only against Snowflake -> second
Claude call turning rows into a plain-English answer. Every generated query
is logged with its accept/reject outcome regardless of what happens next.
"""

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


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


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
