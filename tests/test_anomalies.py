from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from data_generation.anomalies import (
    AnomalyConfig,
    haversine_km,
    inject_all_anomalies,
    inject_amount_outlier,
    inject_impossible_travel,
    inject_velocity_burst,
)


@pytest.fixture
def accounts():
    return pd.DataFrame(
        [
            {"account_id": "ACC000001", "customer_segment": "retail", "home_location": "Chicago, IL", "avg_transaction_amount": 50.0},
            {"account_id": "ACC000002", "customer_segment": "retail", "home_location": "New York, NY", "avg_transaction_amount": 80.0},
            {"account_id": "ACC000003", "customer_segment": "premium", "home_location": "Seattle, WA", "avg_transaction_amount": 200.0},
        ]
    )


@pytest.fixture
def transactions(accounts):
    base_time = datetime(2025, 1, 1)
    rows = []
    for i in range(30):
        account = accounts.iloc[i % len(accounts)]
        rows.append(
            {
                "transaction_id": f"TXN{i + 1:08d}",
                "account_id": account["account_id"],
                "amount": round(account["avg_transaction_amount"] * 1.0, 2),
                "timestamp": base_time + timedelta(hours=i),
                "merchant_category": "groceries",
                "location": account["home_location"],
                "is_flagged": False,
            }
        )
    return pd.DataFrame(rows)


def test_velocity_burst_injects_expected_rows_and_labels(transactions, accounts):
    rng = np.random.default_rng(1)
    mutated, labels = inject_velocity_burst(transactions, accounts, rng, n_bursts=2, burst_size=(5, 5), burst_window_minutes=10)

    assert len(labels) == 10  # 2 bursts * 5 transactions
    assert len(mutated) == len(transactions) + 10
    assert set(labels["anomaly_type"]) == {"VELOCITY_BURST"}
    flagged = mutated.loc[mutated["transaction_id"].isin(labels["transaction_id"]), "is_flagged"]
    assert flagged.all()


def test_amount_outlier_overwrites_existing_rows_not_add(transactions, accounts):
    rng = np.random.default_rng(2)
    original_len = len(transactions)
    mutated, labels = inject_amount_outlier(transactions, accounts, rng, n_outliers=5, multiplier_range=(5.0, 5.0))

    assert len(mutated) == original_len  # in-place overwrite, no new rows
    assert len(labels) == 5
    for _, label in labels.iterrows():
        row = mutated.loc[mutated["transaction_id"] == label["transaction_id"]].iloc[0]
        account_baseline = accounts.set_index("account_id").loc[row["account_id"], "avg_transaction_amount"]
        assert row["amount"] == pytest.approx(account_baseline * 5.0, rel=0.01)
        assert row["is_flagged"]


def test_impossible_travel_respects_min_distance(transactions, accounts):
    rng = np.random.default_rng(3)
    mutated, labels = inject_impossible_travel(transactions, accounts, rng, n_events=2, min_distance_km=500, max_minutes_apart=30)

    assert len(labels) == 2
    for _, label in labels.iterrows():
        row = mutated.loc[mutated["transaction_id"] == label["transaction_id"]].iloc[0]
        home = accounts.set_index("account_id").loc[row["account_id"], "home_location"]
        from data_generation.anomalies import LOCATION_COORDS

        distance = haversine_km(LOCATION_COORDS[home], LOCATION_COORDS[row["location"]])
        assert distance >= 500


def test_inject_all_anomalies_ground_truth_invariant(transactions, accounts):
    rng = np.random.default_rng(42)
    config = AnomalyConfig(n_velocity_bursts=2, burst_size_min=3, burst_size_max=3, n_amount_outliers=3, n_impossible_travel=2)
    mutated, labels = inject_all_anomalies(transactions, accounts, rng, config)

    flagged_ids = set(mutated.loc[mutated["is_flagged"], "transaction_id"])
    label_ids = set(labels["transaction_id"])
    assert label_ids.issubset(flagged_ids)
    assert set(labels.columns) == {"transaction_id", "anomaly_type", "injected_at", "detail"}


def test_reproducible_with_same_seed(transactions, accounts):
    config = AnomalyConfig(n_velocity_bursts=2, burst_size_min=3, burst_size_max=3, n_amount_outliers=3, n_impossible_travel=2)

    rng1 = np.random.default_rng(99)
    mutated1, labels1 = inject_all_anomalies(transactions, accounts, rng1, config)

    rng2 = np.random.default_rng(99)
    mutated2, labels2 = inject_all_anomalies(transactions, accounts, rng2, config)

    pd.testing.assert_frame_equal(
        mutated1.drop(columns=[]).reset_index(drop=True),
        mutated2.reset_index(drop=True),
    )
    assert list(labels1["transaction_id"]) == list(labels2["transaction_id"])
