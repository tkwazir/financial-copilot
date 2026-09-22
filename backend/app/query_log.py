"""Local JSONL log of every generated query + validation outcome — the
spec's own requirement (section 6): "Log every generated query and whether
it was accepted or rejected, for your own evaluation later." Feeds the
Phase 9 SQL-accuracy evaluation.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parent.parent / "query_log.jsonl"


def log_query(
    question: str,
    generated_sql: str,
    accepted: bool,
    reason: str | None,
    executed_sql: str | None,
) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "generated_sql": generated_sql,
        "accepted": accepted,
        "reason": reason,
        "executed_sql": executed_sql,
    }
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
