"""Creates and attaches an account-wide Snowflake resource monitor to cap
credit spend, per snowflake/resource_monitor.sql — the real mechanism for
avoiding trial overcharges (notifies at 75%/90%, suspends compute at 100%).

Usage:
    python -m snowflake.setup_resource_monitor
"""

from pathlib import Path

from snowflake.conn import get_connection
from snowflake.sql_runner import run_sql_file


def main():
    conn = get_connection()
    try:
        run_sql_file(Path(__file__).resolve().parent / "resource_monitor.sql", conn=conn)
        print("\nResource monitor configured.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
