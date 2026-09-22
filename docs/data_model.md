# Data Model Mapping

Maps the columns produced by `data_generation/` to the Snowflake RAW/ANALYTICS tables (project spec section 5). The full pipeline is live: `RAW` (via `snowflake/setup.sql` + `snowflake/load_raw.py`) -> `STAGING` -> `ANALYTICS` (both via `dbt/`, see `dbt/models/`). Column names match 1:1 end-to-end — STAGING only dedupes/trims/rounds, ANALYTICS is a direct pass-through into the star schema.

## Market data (`data/market/`)

### `fact_market_prices.csv` -> `RAW.FACT_MARKET_PRICES` -> `ANALYTICS.FACT_MARKET_PRICES`

| Column | Type (target) | Notes |
|---|---|---|
| `ticker` | VARCHAR | FK to `DIM_TICKERS.ticker` |
| `price_date` | DATE | |
| `open` | NUMBER(10,4) | |
| `high` | NUMBER(10,4) | |
| `low` | NUMBER(10,4) | |
| `close` | NUMBER(10,4) | |
| `volume` | NUMBER | |
| `_loaded_at` | TIMESTAMP_TZ | ingestion metadata, anticipates `COPY INTO` load tracking; drop or keep in RAW only |
| `_source_file` | VARCHAR | ingestion metadata; drop or keep in RAW only |

### `dim_tickers.csv` -> `RAW.DIM_TICKERS` -> `ANALYTICS.DIM_TICKERS`

| Column | Type (target) | Notes |
|---|---|---|
| `ticker` | VARCHAR | PK |
| `company_name` | VARCHAR | |
| `sector` | VARCHAR | |

## Transaction data (`data/transactions/`)

### `fact_transactions.csv` -> `RAW.FACT_TRANSACTIONS` -> `ANALYTICS.FACT_TRANSACTIONS`

| Column | Type (target) | Notes |
|---|---|---|
| `transaction_id` | VARCHAR | PK |
| `account_id` | VARCHAR | FK to `DIM_ACCOUNTS.account_id` |
| `amount` | NUMBER(10,2) | |
| `timestamp` | TIMESTAMP_NTZ | |
| `merchant_category` | VARCHAR | |
| `location` | VARCHAR | city-level, from a fixed lookup (see `data_generation/anomalies.py::LOCATION_COORDS`) |
| `is_flagged` | BOOLEAN | set by anomaly injection (ground truth) — the model's own predictions live separately in `ANALYTICS.FLAGGED_TXNS`, not written back here |

### `dim_accounts.csv` -> `RAW.DIM_ACCOUNTS` -> `ANALYTICS.DIM_ACCOUNTS`

| Column | Type (target) | Notes |
|---|---|---|
| `account_id` | VARCHAR | PK |
| `customer_segment` | VARCHAR | `retail` \| `small_business` \| `premium` |
| `home_location` | VARCHAR | city-level |
| `avg_transaction_amount` | NUMBER(10,2) | baseline used by amount-outlier detection, both synthetic injection and future model |

### `ground_truth_labels.csv` — not part of the medallion model; evaluation artifact only

| Column | Notes |
|---|---|
| `transaction_id` | FK to `fact_transactions.transaction_id` |
| `anomaly_type` | `VELOCITY_BURST` \| `AMOUNT_OUTLIER` \| `IMPOSSIBLE_TRAVEL` |
| `injected_at` | generation-time timestamp, not a transaction attribute |
| `detail` | free-text explanation (burst position, multiplier, distance/time for impossible travel) |

Used to compute precision/recall for the Snowpark anomaly detection model (`snowflake/evaluate_anomaly_detection.py`), and optionally against Snowflake's native `ANOMALY_DETECTION` function in a future phase — the labels are ground truth because the anomalies were injected on purpose, not estimated.

## Model output — `ANALYTICS.FLAGGED_TXNS` (produced by `snowflake/anomaly_detection.py`, not part of the medallion load)

| Column | Notes |
|---|---|
| `TRANSACTION_ID` | FK to `FACT_TRANSACTIONS.transaction_id` |
| `ANOMALY_SCORE` | Isolation Forest score, higher = more anomalous |
| `MODEL_FLAGGED` | binary decision at `contamination=0.008` |
| `AMOUNT_RATIO`, `VELOCITY_COUNT_10MIN`, `DISTANCE_FROM_HOME_KM` | the 3 model features, kept for debugging/threshold analysis |
| `MODEL_VERSION`, `SCORED_AT` | run metadata |

See [`anomaly_detection_results.md`](anomaly_detection_results.md) for precision/recall against `RAW.GROUND_TRUTH_LABELS`.
