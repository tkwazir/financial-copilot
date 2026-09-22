#!/usr/bin/env bash
# Loads .env (for SNOWFLAKE_* vars, which dbt's profiles.yml reads via env_var())
# then runs dbt against this project. Usage: ./dbt/run_dbt.sh run
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

set -a
source "$PROJECT_ROOT/.env"
set +a

dbt "$@" --project-dir "$SCRIPT_DIR" --profiles-dir "$SCRIPT_DIR"
