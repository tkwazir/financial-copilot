# Snowflake

Phases 3 (setup) and 5 (anomaly detection) are done. Contents:

- `conn.py` — shared connection helper. Uses **RSA key-pair auth**, not password — this account enforces MFA on password-based connector logins (`Multi-factor authentication is required for this account`), which key-pair auth bypasses. This is Snowflake's own recommended approach for service/script access regardless, so the MFA block just forced the right choice earlier than planned. Private key lives in `.secrets/` (gitignored, local-only).
- `setup.sql` — idempotent DDL: `FIN_COPILOT_WH` warehouse (`X-SMALL`, `AUTO_SUSPEND=60`), `FIN_COPILOT` database, `RAW`/`STAGING`/`ANALYTICS` schemas, `RAW` tables (shaped to match `data_generation/` output — see `docs/data_model.md`), an internal `LOAD_STAGE`, and the read-only `COPILOT_APP_ROLE`.
- `run_setup.py` — executes `setup.sql`, then grants `COPILOT_APP_ROLE` to the connecting user (fetched via `CURRENT_USER()` at runtime rather than hardcoded, since this repo is public).
- `load_raw.py` — `PUT` + `COPY INTO` for the 5 CSVs in `data/` into their matching `RAW` tables. Truncates before each load (idempotent reruns). Prints row counts after loading.
- `anomaly_detection.py` — registers `detect_anomalies_proc` as a **Snowpark Python stored procedure** and calls it via `CALL` — feature engineering (amount ratio, trailing-10-minute velocity, distance-from-home via haversine) and the Isolation Forest fit/predict all execute inside Snowflake's own compute (the warehouse's sandboxed Python runtime), not on the local machine. Writes `ANALYTICS.FLAGGED_TXNS`. Uses a *temporary* stored procedure (registered fresh each run, not persisted as a named SQL object) since it only needs to exist for the duration of one run.
- `evaluate_anomaly_detection.py` — joins `FLAGGED_TXNS` against `RAW.GROUND_TRUTH_LABELS`, computes precision/recall/F1/PR-AUC overall and broken down by anomaly type, writes `docs/anomaly_detection_results.md`.
- `sql_runner.py` — shared helper (`parse_statements`, `run_sql_file`) used by `run_setup.py` and `setup_resource_monitor.py` to execute a `.sql` file's statements one at a time.
- `resource_monitor.sql` / `setup_resource_monitor.py` — account-wide resource monitor capping spend at 350 credits (notify 75%/90%, suspend 100%, suspend-immediate 110%) — see root README's "Budget / Cost Constraints".

Run order: `python -m snowflake.run_setup` → `python -m snowflake.load_raw` → (`dbt/run_dbt.sh run` — see `dbt/`) → `python -m snowflake.anomaly_detection` → `python -m snowflake.evaluate_anomaly_detection` (from the repo root, `financial-copilot` conda env active). Requires `.env` filled in (see `.env.example`) and a registered RSA public key on your Snowflake user — see the root README's "Snowflake Auth Setup" section.

**Real results** (see `docs/anomaly_detection_results.md` for full breakdown + methodology notes): 38.9% precision, 37.7% recall overall against 162 ground-truth anomalies in 20,137 transactions — 100% recall on amount outliers, 0% on impossible travel (a genuine, diagnosed limitation of joint-feature Isolation Forest scoring at this contamination level with only 15 examples of that category, not a bug — the distance feature is correctly computed).

**Still to build** (future sessions):
- FastAPI + Claude API NL-to-SQL backend (Phase 6)
- (Optional) Cortex Analyst semantic model YAML, Cortex `ANOMALY_DETECTION` comparison (Phase 7)
