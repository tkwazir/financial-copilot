"""Runs snowflake/setup.sql against the account, then grants the
COPILOT_APP_ROLE role to the connecting (current) user.

Usage:
    python -m snowflake.run_setup
"""

from pathlib import Path

from snowflake.conn import get_connection
from snowflake.sql_runner import run_sql_file


def main():
    conn = get_connection()
    try:
        run_sql_file(Path(__file__).resolve().parent / "setup.sql", conn=conn)

        cur = conn.cursor()
        cur.execute("SELECT CURRENT_USER()")
        current_user = cur.fetchone()[0]
        grant_stmt = f'GRANT ROLE COPILOT_APP_ROLE TO USER "{current_user}"'
        print(f"Executing: {grant_stmt}")
        cur.execute(grant_stmt)
        cur.close()

        print("\nSetup complete.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
