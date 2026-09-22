"""Builds the schema-aware prompt context by introspecting ANALYTICS at
startup, via COPILOT_APP_ROLE (the same read-only role queries run under).

Given the schema is small (4 tables), the whole schema is included in every
prompt rather than doing RAG-style retrieval over per-table descriptions —
a deliberate design decision (spec section 6), not a limitation. RAG starts
to matter once this scales to dozens of tables; it doesn't here.
"""

from snowflake.conn import get_connection


def fetch_schema_description() -> str:
    conn = get_connection(
        role="COPILOT_APP_ROLE",
        warehouse="FIN_COPILOT_WH",
        database="FIN_COPILOT",
        schema="ANALYTICS",
    )
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'ANALYTICS'
            ORDER BY TABLE_NAME, ORDINAL_POSITION
        """)
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    tables: dict[str, list[tuple[str, str]]] = {}
    for table_name, column_name, data_type in rows:
        tables.setdefault(table_name, []).append((column_name, data_type))

    lines = ["Available tables in FIN_COPILOT.ANALYTICS (read-only, fully-qualified names not needed):", ""]
    for table_name, columns in tables.items():
        column_list = ", ".join(f"{c} {t}" for c, t in columns)
        lines.append(f"- {table_name}({column_list})")

    lines.append("")
    lines.append(
        "Notes: FACT_TRANSACTIONS.is_flagged reflects known synthetic ground-truth "
        "anomalies, not a live model's predictions. Amounts are in USD."
    )
    return "\n".join(lines)
