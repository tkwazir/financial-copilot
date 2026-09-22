"""Deliberate, labeled anomaly injection for the synthetic transaction set.

Each injector is a pure function: (transactions, accounts, rng, ...params) ->
(mutated_transactions, labels). Labels record exactly which transaction_ids
were injected and why, which is the ground truth later phases (spec section
8) use to compute real precision/recall against a detection model.
"""

from dataclasses import dataclass
from datetime import timedelta
from math import asin, cos, radians, sin, sqrt

import numpy as np
import pandas as pd

# Fixed city -> (lat, lon) lookup. Kept small and static so impossible-travel
# distances are deterministic and numerically checkable, not just asserted.
LOCATION_COORDS: dict[str, tuple[float, float]] = {
    "Chicago, IL": (41.8781, -87.6298),
    "New York, NY": (40.7128, -74.0060),
    "Los Angeles, CA": (34.0522, -118.2437),
    "Houston, TX": (29.7604, -95.3698),
    "Phoenix, AZ": (33.4484, -112.0740),
    "Philadelphia, PA": (39.9526, -75.1652),
    "San Antonio, TX": (29.4241, -98.4936),
    "San Diego, CA": (32.7157, -117.1611),
    "Dallas, TX": (32.7767, -96.7970),
    "Miami, FL": (25.7617, -80.1918),
    "Seattle, WA": (47.6062, -122.3321),
    "Denver, CO": (39.7392, -104.9903),
    "Boston, MA": (42.3601, -71.0589),
    "Atlanta, GA": (33.7490, -84.3880),
    "Portland, OR": (45.5152, -122.6784),
}

MERCHANT_CATEGORIES = [
    "groceries",
    "dining",
    "travel",
    "electronics",
    "utilities",
    "entertainment",
    "healthcare",
    "retail",
]


def haversine_km(coord_a: tuple[float, float], coord_b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(radians, [*coord_a, *coord_b])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * 6371 * asin(sqrt(a))


@dataclass
class AnomalyConfig:
    n_velocity_bursts: int = 15
    burst_size_min: int = 5
    burst_size_max: int = 12
    burst_window_minutes: int = 10

    n_amount_outliers: int = 25
    amount_multiplier_min: float = 5.0
    amount_multiplier_max: float = 15.0

    n_impossible_travel: int = 15
    min_distance_km: float = 500.0
    max_minutes_apart: int = 30


def inject_velocity_burst(
    txns: pd.DataFrame,
    accounts: pd.DataFrame,
    rng: np.random.Generator,
    n_bursts: int,
    burst_size: tuple[int, int] = (5, 12),
    burst_window_minutes: int = 10,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Insert bursts of rapid, tightly-clustered transactions per account."""
    txns = txns.copy()
    new_rows = []
    labels = []

    account_ids = accounts["account_id"].to_numpy()
    if len(account_ids) == 0 or n_bursts == 0:
        return txns, pd.DataFrame(columns=["transaction_id", "anomaly_type", "detail"])

    chosen_accounts = rng.choice(account_ids, size=min(n_bursts, len(account_ids)), replace=False)
    next_id = _next_transaction_id(txns)

    for burst_idx, account_id in enumerate(chosen_accounts):
        size = int(rng.integers(burst_size[0], burst_size[1] + 1))
        acct_row = accounts.loc[accounts["account_id"] == account_id].iloc[0]
        base_amount = acct_row["avg_transaction_amount"]
        location = acct_row["home_location"]

        anchor_time = pd.Timestamp(rng.choice(txns["timestamp"].to_numpy()))
        for position in range(size):
            offset_minutes = rng.uniform(0, burst_window_minutes)
            ts = anchor_time + timedelta(minutes=float(offset_minutes))
            amount = round(float(base_amount * rng.uniform(0.8, 1.2)), 2)
            txn_id = f"TXN{next_id:08d}"
            next_id += 1
            new_rows.append(
                {
                    "transaction_id": txn_id,
                    "account_id": account_id,
                    "amount": amount,
                    "timestamp": ts,
                    "merchant_category": rng.choice(MERCHANT_CATEGORIES),
                    "location": location,
                    "is_flagged": True,
                }
            )
            labels.append(
                {
                    "transaction_id": txn_id,
                    "anomaly_type": "VELOCITY_BURST",
                    "detail": f"burst_id={burst_idx}, position {position + 1} of {size}",
                }
            )

    txns = pd.concat([txns, pd.DataFrame(new_rows)], ignore_index=True)
    return txns, pd.DataFrame(labels)


def inject_amount_outlier(
    txns: pd.DataFrame,
    accounts: pd.DataFrame,
    rng: np.random.Generator,
    n_outliers: int,
    multiplier_range: tuple[float, float] = (5.0, 15.0),
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Overwrite existing transactions' amounts to a large multiple of the account baseline."""
    txns = txns.copy()
    labels = []

    if len(txns) == 0 or n_outliers == 0:
        return txns, pd.DataFrame(columns=["transaction_id", "anomaly_type", "detail"])

    accounts_by_id = accounts.set_index("account_id")["avg_transaction_amount"]
    chosen_idx = rng.choice(txns.index.to_numpy(), size=min(n_outliers, len(txns)), replace=False)

    for idx in chosen_idx:
        account_id = txns.at[idx, "account_id"]
        baseline = float(accounts_by_id.loc[account_id])
        multiplier = rng.uniform(*multiplier_range)
        new_amount = round(baseline * multiplier, 2)
        txns.at[idx, "amount"] = new_amount
        txns.at[idx, "is_flagged"] = True
        labels.append(
            {
                "transaction_id": txns.at[idx, "transaction_id"],
                "anomaly_type": "AMOUNT_OUTLIER",
                "detail": f"multiplier={multiplier:.2f}x avg (avg={baseline:.2f})",
            }
        )

    return txns, pd.DataFrame(labels)


def inject_impossible_travel(
    txns: pd.DataFrame,
    accounts: pd.DataFrame,
    rng: np.random.Generator,
    n_events: int,
    min_distance_km: float = 500.0,
    max_minutes_apart: int = 30,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Insert a paired transaction far from an account's home location, minutes after a normal one."""
    txns = txns.copy()
    new_rows = []
    labels = []

    if len(txns) == 0 or n_events == 0:
        return txns, pd.DataFrame(columns=["transaction_id", "anomaly_type", "detail"])

    account_ids = accounts["account_id"].to_numpy()
    chosen_accounts = rng.choice(account_ids, size=min(n_events, len(account_ids)), replace=False)
    next_id = _next_transaction_id(txns)

    far_locations = {
        city: coord
        for city, coord in LOCATION_COORDS.items()
    }

    for event_idx, account_id in enumerate(chosen_accounts):
        acct_row = accounts.loc[accounts["account_id"] == account_id].iloc[0]
        home_location = acct_row["home_location"]
        home_coord = LOCATION_COORDS[home_location]

        candidates = [
            city for city, coord in far_locations.items() if haversine_km(home_coord, coord) >= min_distance_km
        ]
        if not candidates:
            continue
        far_location = candidates[rng.integers(0, len(candidates))]

        acct_txns = txns.loc[txns["account_id"] == account_id]
        if acct_txns.empty:
            continue
        anchor_row = acct_txns.sample(n=1, random_state=int(rng.integers(0, 2**31))).iloc[0]
        anchor_time = pd.Timestamp(anchor_row["timestamp"])
        offset_minutes = rng.uniform(1, max_minutes_apart)
        ts = anchor_time + timedelta(minutes=float(offset_minutes))

        txn_id = f"TXN{next_id:08d}"
        next_id += 1
        amount = round(float(acct_row["avg_transaction_amount"] * rng.uniform(0.5, 1.5)), 2)
        new_rows.append(
            {
                "transaction_id": txn_id,
                "account_id": account_id,
                "amount": amount,
                "timestamp": ts,
                "merchant_category": rng.choice(MERCHANT_CATEGORIES),
                "location": far_location,
                "is_flagged": True,
            }
        )
        distance = haversine_km(home_coord, LOCATION_COORDS[far_location])
        labels.append(
            {
                "transaction_id": txn_id,
                "anomaly_type": "IMPOSSIBLE_TRAVEL",
                "detail": (
                    f"event_id={event_idx}, anchor_txn={anchor_row['transaction_id']}, "
                    f"distance_km={distance:.0f}, minutes_apart={offset_minutes:.1f}"
                ),
            }
        )

    txns = pd.concat([txns, pd.DataFrame(new_rows)], ignore_index=True)
    return txns, pd.DataFrame(labels)


def inject_all_anomalies(
    txns: pd.DataFrame,
    accounts: pd.DataFrame,
    rng: np.random.Generator,
    config: AnomalyConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    txns, velocity_labels = inject_velocity_burst(
        txns,
        accounts,
        rng,
        n_bursts=config.n_velocity_bursts,
        burst_size=(config.burst_size_min, config.burst_size_max),
        burst_window_minutes=config.burst_window_minutes,
    )
    txns, amount_labels = inject_amount_outlier(
        txns,
        accounts,
        rng,
        n_outliers=config.n_amount_outliers,
        multiplier_range=(config.amount_multiplier_min, config.amount_multiplier_max),
    )
    txns, travel_labels = inject_impossible_travel(
        txns,
        accounts,
        rng,
        n_events=config.n_impossible_travel,
        min_distance_km=config.min_distance_km,
        max_minutes_apart=config.max_minutes_apart,
    )

    labels = pd.concat([velocity_labels, amount_labels, travel_labels], ignore_index=True)
    labels["injected_at"] = pd.Timestamp.now(tz="UTC").isoformat()
    labels = labels[["transaction_id", "anomaly_type", "injected_at", "detail"]]

    return txns.reset_index(drop=True), labels


def _next_transaction_id(txns: pd.DataFrame) -> int:
    if len(txns) == 0:
        return 1
    existing = txns["transaction_id"].str.replace("TXN", "", regex=False).astype(int)
    return int(existing.max()) + 1
