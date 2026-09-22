"""Generate synthetic accounts + transactions via Faker, inject labeled
anomalies, and write output shaped to match the eventual Snowflake
RAW.FACT_TRANSACTIONS / RAW.DIM_ACCOUNTS tables plus a ground-truth label file.

Usage:
    python -m data_generation.generate_transactions
    python -m data_generation.generate_transactions --n-accounts 200 --n-transactions 5000 --seed 7
"""

import argparse
from datetime import date, datetime, timedelta, timezone

import numpy as np
import pandas as pd
from faker import Faker

from data_generation.anomalies import LOCATION_COORDS, MERCHANT_CATEGORIES, AnomalyConfig, inject_all_anomalies
from data_generation.io_utils import resolve_out_dir, write_df, write_manifest

SCRIPT_VERSION = "1.0.0"

SEGMENTS = ["retail", "small_business", "premium"]
SEGMENT_BASELINE_PARAMS = {
    # (lognormal mean, lognormal sigma) for avg_transaction_amount
    "retail": (3.8, 0.5),  # ~ $45 median
    "small_business": (5.5, 0.6),  # ~ $245 median
    "premium": (5.0, 0.7),  # ~ $150 median, higher variance
}


def build_accounts(n_accounts: int, rng: np.random.Generator, fake: Faker) -> pd.DataFrame:
    locations = list(LOCATION_COORDS.keys())
    segments = rng.choice(SEGMENTS, size=n_accounts, p=[0.6, 0.15, 0.25])

    rows = []
    for i in range(n_accounts):
        segment = segments[i]
        mu, sigma = SEGMENT_BASELINE_PARAMS[segment]
        avg_amount = round(float(rng.lognormal(mu, sigma) / 10), 2)  # scale down from raw lognormal draw
        rows.append(
            {
                "account_id": f"ACC{i + 1:06d}",
                "customer_segment": segment,
                "home_location": locations[int(rng.integers(0, len(locations)))],
                "avg_transaction_amount": max(avg_amount, 5.0),
            }
        )
    return pd.DataFrame(rows)


def build_transactions(
    accounts: pd.DataFrame,
    n_transactions: int,
    start: date,
    end: date,
    rng: np.random.Generator,
) -> pd.DataFrame:
    account_ids = accounts["account_id"].to_numpy()
    baselines = accounts.set_index("account_id")["avg_transaction_amount"]
    locations = accounts.set_index("account_id")["home_location"]

    span_seconds = int((datetime.combine(end, datetime.min.time()) - datetime.combine(start, datetime.min.time())).total_seconds())

    chosen_accounts = rng.choice(account_ids, size=n_transactions, replace=True)
    offsets = rng.integers(0, max(span_seconds, 1), size=n_transactions)
    categories = rng.choice(MERCHANT_CATEGORIES, size=n_transactions)

    rows = []
    start_dt = datetime.combine(start, datetime.min.time())
    for i in range(n_transactions):
        account_id = chosen_accounts[i]
        baseline = baselines.loc[account_id]
        amount = round(float(rng.lognormal(np.log(max(baseline, 1.0)), 0.4)), 2)
        ts = start_dt + timedelta(seconds=int(offsets[i]))
        rows.append(
            {
                "transaction_id": f"TXN{i + 1:08d}",
                "account_id": account_id,
                "amount": amount,
                "timestamp": ts,
                "merchant_category": categories[i],
                "location": locations.loc[account_id],
                "is_flagged": False,
            }
        )

    return pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Generate synthetic accounts/transactions with injected anomalies")
    parser.add_argument("--n-accounts", type=int, default=500)
    parser.add_argument("--n-transactions", type=int, default=20000)
    default_end = date.today()
    default_start = default_end - timedelta(days=365)
    parser.add_argument("--start", type=str, default=default_start.isoformat())
    parser.add_argument("--end", type=str, default=default_end.isoformat())
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-velocity-bursts", type=int, default=15)
    parser.add_argument("--n-amount-outliers", type=int, default=25)
    parser.add_argument("--n-impossible-travel", type=int, default=15)
    parser.add_argument("--out-dir", type=str, default="data/transactions")
    parser.add_argument("--format", type=str, default="csv", choices=["csv", "parquet"])
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    rng = np.random.default_rng(args.seed)
    fake = Faker()
    Faker.seed(args.seed)

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)

    accounts = build_accounts(args.n_accounts, rng, fake)
    transactions = build_transactions(accounts, args.n_transactions, start, end, rng)

    config = AnomalyConfig(
        n_velocity_bursts=args.n_velocity_bursts,
        n_amount_outliers=args.n_amount_outliers,
        n_impossible_travel=args.n_impossible_travel,
    )
    transactions, labels = inject_all_anomalies(transactions, accounts, rng, config)

    # Invariant: every labeled anomaly must be flagged in the transactions output.
    flagged_ids = set(transactions.loc[transactions["is_flagged"], "transaction_id"])
    label_ids = set(labels["transaction_id"])
    missing = label_ids - flagged_ids
    if missing:
        raise AssertionError(f"Ground truth labels exist for un-flagged transactions: {missing}")

    out_dir = resolve_out_dir(args.out_dir)
    write_df(transactions, out_dir / "fact_transactions", args.format)
    write_df(accounts, out_dir / "dim_accounts", args.format)
    write_df(labels, out_dir / "ground_truth_labels", args.format)

    anomalies_by_type = labels["anomaly_type"].value_counts().to_dict() if len(labels) else {}
    manifest = {
        "seed": args.seed,
        "n_accounts": args.n_accounts,
        "n_transactions_requested": args.n_transactions,
        "n_transactions_final": len(transactions),
        "n_anomalies_injected_by_type": anomalies_by_type,
        "date_range": {"start": args.start, "end": args.end},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "script_version": SCRIPT_VERSION,
    }
    write_manifest(manifest, out_dir / "_run_manifest.json")

    print(f"Wrote {len(transactions)} transactions, {len(accounts)} accounts, {len(labels)} labeled anomalies to {out_dir}")


if __name__ == "__main__":
    main()
