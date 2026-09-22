-- Phase 3 setup: warehouse, database, medallion schemas, RAW tables, stage, RBAC.
-- Run once via snowflake/run_setup.py (idempotent — every object uses IF NOT EXISTS).

USE ROLE ACCOUNTADMIN;

-- Compute: smallest size, auto-suspend after 60s idle. This is the single
-- most important cost control on a free trial (spec section 1a / 4).
CREATE WAREHOUSE IF NOT EXISTS FIN_COPILOT_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE;

-- Storage: one database, medallion schemas.
CREATE DATABASE IF NOT EXISTS FIN_COPILOT;
CREATE SCHEMA IF NOT EXISTS FIN_COPILOT.RAW;
CREATE SCHEMA IF NOT EXISTS FIN_COPILOT.STAGING;
CREATE SCHEMA IF NOT EXISTS FIN_COPILOT.ANALYTICS;

-- Internal stage for loading the local CSVs produced by data_generation/.
CREATE STAGE IF NOT EXISTS FIN_COPILOT.RAW.LOAD_STAGE
  FILE_FORMAT = (
    TYPE = CSV
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    SKIP_HEADER = 1
    NULL_IF = ('')
    EMPTY_FIELD_AS_NULL = TRUE
  );

-- RAW tables, shaped to match data_generation/ output 1:1 (see docs/data_model.md).
CREATE TABLE IF NOT EXISTS FIN_COPILOT.RAW.FACT_MARKET_PRICES (
  ticker STRING,
  price_date DATE,
  open NUMBER(10, 4),
  high NUMBER(10, 4),
  low NUMBER(10, 4),
  close NUMBER(10, 4),
  volume NUMBER,
  _loaded_at TIMESTAMP_TZ,
  _source_file STRING
);

CREATE TABLE IF NOT EXISTS FIN_COPILOT.RAW.DIM_TICKERS (
  ticker STRING,
  company_name STRING,
  sector STRING
);

CREATE TABLE IF NOT EXISTS FIN_COPILOT.RAW.FACT_TRANSACTIONS (
  transaction_id STRING,
  account_id STRING,
  amount NUMBER(10, 2),
  timestamp TIMESTAMP_NTZ,
  merchant_category STRING,
  location STRING,
  is_flagged BOOLEAN
);

CREATE TABLE IF NOT EXISTS FIN_COPILOT.RAW.DIM_ACCOUNTS (
  account_id STRING,
  customer_segment STRING,
  home_location STRING,
  avg_transaction_amount NUMBER(10, 2)
);

CREATE TABLE IF NOT EXISTS FIN_COPILOT.RAW.GROUND_TRUTH_LABELS (
  transaction_id STRING,
  anomaly_type STRING,
  injected_at TIMESTAMP_TZ,
  detail STRING
);

-- Read-only application role. The NL-to-SQL backend (Phase 6) must run under
-- this role only — never a role that can write or drop anything (spec section 4).
CREATE ROLE IF NOT EXISTS COPILOT_APP_ROLE;
GRANT USAGE ON WAREHOUSE FIN_COPILOT_WH TO ROLE COPILOT_APP_ROLE;
GRANT USAGE ON DATABASE FIN_COPILOT TO ROLE COPILOT_APP_ROLE;
GRANT USAGE ON SCHEMA FIN_COPILOT.ANALYTICS TO ROLE COPILOT_APP_ROLE;
GRANT SELECT ON ALL TABLES IN SCHEMA FIN_COPILOT.ANALYTICS TO ROLE COPILOT_APP_ROLE;
GRANT SELECT ON FUTURE TABLES IN SCHEMA FIN_COPILOT.ANALYTICS TO ROLE COPILOT_APP_ROLE;
-- Note: `GRANT ROLE COPILOT_APP_ROLE TO USER <current_user>` is issued
-- separately by run_setup.py (fetches CURRENT_USER() at runtime) rather than
-- hardcoded here, since this file is committed to a public repo.
