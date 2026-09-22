"""Shared helper: parse and execute a .sql file's statements against Snowflake."""

from pathlib import Path

from snowflake.conn import get_connection


def parse_statements(sql_text: str) -> list[str]:
    """Strip full-line comments from each ';'-delimited chunk *before*
    deciding whether the chunk is empty — otherwise a statement preceded by
    a comment line gets mistaken for an all-comment chunk and dropped."""
    statements = []
    for chunk in sql_text.split(";"):
        lines = [line for line in chunk.splitlines() if not line.strip().startswith("--")]
        clean_stmt = "\n".join(lines).strip()
        if clean_stmt:
            statements.append(clean_stmt)
    return statements


def run_sql_file(sql_path: Path, conn=None) -> None:
    statements = parse_statements(sql_path.read_text())
    owns_conn = conn is None
    if owns_conn:
        conn = get_connection()
    cur = conn.cursor()
    try:
        for stmt in statements:
            print(f"Executing: {stmt.splitlines()[0][:80]}...")
            cur.execute(stmt)
    finally:
        cur.close()
        if owns_conn:
            conn.close()
