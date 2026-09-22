"""Read-only Snowflake query execution for the NL-to-SQL backend.

Always connects under COPILOT_APP_ROLE — a role with SELECT-only grants on
ANALYTICS (see snowflake/setup.sql) — never a role that can write or drop
anything, per the spec's own security guidance (section 4).
"""

from snowflake.conn import get_connection

QUERY_TIMEOUT_SECONDS = 30


def run_query(sql: str) -> tuple[list[str], list[tuple]]:
    conn = get_connection(
        role="COPILOT_APP_ROLE",
        warehouse="FIN_COPILOT_WH",
        database="FIN_COPILOT",
        schema="ANALYTICS",
    )
    cur = conn.cursor()
    try:
        cur.execute(f"ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = {QUERY_TIMEOUT_SECONDS}")
        cur.execute(sql)
        columns = [d[0] for d in cur.description]
        rows = cur.fetchall()
        return columns, rows
    finally:
        cur.close()
        conn.close()
