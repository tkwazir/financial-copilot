"""SQL validation/guardrail layer for LLM-generated queries.

Pure, dependency-light (only sqlparse), and independently unit-testable
without live Snowflake/Claude credentials — this is the "genuinely testable
code" the spec calls out (section 6, section 9) as distinct from the rest of
an LLM-adjacent pipeline.
"""

import re
from typing import NamedTuple

import sqlparse

DEFAULT_ROW_LIMIT = 200

FORBIDDEN_KEYWORDS = {
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "MERGE",
    "GRANT",
    "REVOKE",
    "COPY",
    "CALL",
    "EXECUTE",
    "PUT",
    "GET",
    "UNLOAD",
    "REPLACE",
}


class ValidationResult(NamedTuple):
    accepted: bool
    safe_sql: str | None
    reason: str | None


def validate_sql(sql: str, default_limit: int = DEFAULT_ROW_LIMIT) -> ValidationResult:
    """Accepts only a single read-only SELECT (optionally WITH ... SELECT)
    statement, rejects anything containing a write/DDL keyword, and appends
    a LIMIT if the query doesn't already have one."""
    cleaned = (sql or "").strip()
    if not cleaned:
        return ValidationResult(False, None, "empty query")

    statements = [s for s in sqlparse.parse(cleaned) if s.token_first(skip_cm=True) is not None]
    if len(statements) != 1:
        return ValidationResult(False, None, f"exactly one SQL statement required, got {len(statements)}")

    stmt = statements[0]
    first_token = stmt.token_first(skip_cm=True)
    first_keyword = (first_token.value if first_token else "").upper()
    if first_keyword not in {"SELECT", "WITH"}:
        return ValidationResult(
            False, None, f"only SELECT (or WITH ... SELECT) statements allowed, got '{first_keyword}'"
        )

    upper = cleaned.upper()
    for kw in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{kw}\b", upper):
            return ValidationResult(False, None, f"forbidden keyword: {kw}")

    safe_sql = _ensure_limit(cleaned.rstrip(";").rstrip(), default_limit)
    return ValidationResult(True, safe_sql, None)


def _ensure_limit(sql: str, default_limit: int) -> str:
    if re.search(r"\bLIMIT\s+\d+\b", sql, re.IGNORECASE):
        return sql
    return f"{sql}\nLIMIT {default_limit}"
