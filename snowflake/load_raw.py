"""Loads the local CSVs from data_generation/ into FIN_COPILOT.RAW via PUT + COPY INTO.

Usage:
    python -m snowflake.load_raw
"""

from pathlib import Path

from snowflake.conn import get_connection

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# (local file, target table)
FILES_TO_LOAD = [
    (PROJECT_ROOT / "data/market/fact_market_prices.csv", "FACT_MARKET_PRICES"),
    (PROJECT_ROOT / "data/market/dim_tickers.csv", "DIM_TICKERS"),
    (PROJECT_ROOT / "data/transactions/fact_transactions.csv", "FACT_TRANSACTIONS"),
    (PROJECT_ROOT / "data/transactions/dim_accounts.csv", "DIM_ACCOUNTS"),
    (PROJECT_ROOT / "data/transactions/ground_truth_labels.csv", "GROUND_TRUTH_LABELS"),
]


def main():
    conn = get_connection(warehouse="FIN_COPILOT_WH", database="FIN_COPILOT", schema="RAW")
    cur = conn.cursor()
    try:
        for local_path, table in FILES_TO_LOAD:
            if not local_path.exists():
                print(f"SKIP {table}: {local_path} not found (run data_generation scripts first)")
                continue

            print(f"\n--- {table} ---")
            cur.execute(f"TRUNCATE TABLE IF EXISTS {table}")

            put_sql = f"PUT file://{local_path} @LOAD_STAGE AUTO_COMPRESS=TRUE OVERWRITE=TRUE"
            cur.execute(put_sql)
            put_result = cur.fetchall()
            print(f"PUT: {put_result[0][0]} -> {put_result[0][6]}")

            copy_sql = f"""
                COPY INTO {table}
                FROM @LOAD_STAGE/{local_path.name}.gz
                FILE_FORMAT = (TYPE = CSV FIELD_OPTIONALLY_ENCLOSED_BY = '"' SKIP_HEADER = 1)
                ON_ERROR = 'ABORT_STATEMENT'
            """
            cur.execute(copy_sql)
            copy_result = cur.fetchall()
            rows_loaded = sum(r[3] for r in copy_result) if copy_result else 0
            print(f"COPY INTO: {rows_loaded} rows loaded across {len(copy_result)} file(s)")

        print("\n--- Row counts after load ---")
        for _, table in FILES_TO_LOAD:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"{table}: {count}")
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
