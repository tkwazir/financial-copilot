"""Trains + scores an Isolation Forest anomaly detection model.

Registers detect_anomalies_proc as a Snowpark Python stored procedure and
invokes it via CALL — the feature engineering and sklearn fit/predict run
inside Snowflake's own compute (the warehouse's sandboxed Python runtime),
not on this laptop. Results land in ANALYTICS.FLAGGED_TXNS.

Usage:
    python -m snowflake.anomaly_detection
"""

import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv
from snowflake.snowpark import Session

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def get_snowpark_session() -> Session:
    key_path = PROJECT_ROOT / ".secrets" / "snowflake_rsa_key.p8"
    with open(key_path, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)
    private_key_der = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return Session.builder.configs(
        {
            "account": os.environ["SNOWFLAKE_ACCOUNT"],
            "user": os.environ["SNOWFLAKE_USER"],
            "private_key": private_key_der,
            "role": os.environ.get("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
            "warehouse": os.environ["SNOWFLAKE_WAREHOUSE"],
            "database": os.environ["SNOWFLAKE_DATABASE"],
            "schema": "ANALYTICS",
        }
    ).create()


def detect_anomalies_proc(session: Session) -> str:
    """Self-contained on purpose: this becomes a Snowpark stored procedure,
    shipped to and executed by Snowflake's runtime, so all imports and the
    city coordinate lookup are inlined rather than referencing local modules."""
    from math import asin, cos, radians, sin, sqrt

    import numpy as np
    import pandas as pd
    from sklearn.ensemble import IsolationForest

    # Mirrors data_generation/anomalies.py::LOCATION_COORDS — duplicated
    # intentionally since a stored procedure body must be self-contained.
    location_coords = {
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

    def haversine_km(coord_a, coord_b):
        lat1, lon1, lat2, lon2 = map(radians, [*coord_a, *coord_b])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        return 2 * 6371 * asin(sqrt(a))

    txns = session.table("FIN_COPILOT.ANALYTICS.FACT_TRANSACTIONS").to_pandas()
    accounts = session.table("FIN_COPILOT.ANALYTICS.DIM_ACCOUNTS").to_pandas()
    txns.columns = txns.columns.str.lower()
    accounts.columns = accounts.columns.str.lower()

    df = txns.merge(accounts, on="account_id", how="left")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(["account_id", "timestamp"]).reset_index(drop=True)

    # Feature 1: amount relative to the account's historical average (catches AMOUNT_OUTLIER)
    df["amount_ratio"] = (df["amount"] / df["avg_transaction_amount"].replace(0, np.nan)).fillna(1.0)

    # Feature 2: trailing-10-minute transaction count per account (catches VELOCITY_BURST)
    indexed = df.set_index("timestamp")
    velocity = indexed.groupby("account_id")["transaction_id"].rolling("10min").count()
    df["velocity_count_10min"] = velocity.reset_index(level=0, drop=True).to_numpy()

    # Feature 3: distance from the account's home location (catches IMPOSSIBLE_TRAVEL)
    def distance_row(row):
        home = location_coords.get(row["home_location"])
        loc = location_coords.get(row["location"])
        if not home or not loc:
            return 0.0
        return haversine_km(home, loc)

    df["distance_from_home_km"] = df.apply(distance_row, axis=1)

    feature_cols = ["amount_ratio", "velocity_count_10min", "distance_from_home_km"]
    features = df[feature_cols].fillna(0.0)

    # contamination set to the known synthetic injection rate (~0.8%) — a
    # real deployment without ground truth would tune this via a validation
    # set or cost-based thresholding instead.
    model = IsolationForest(n_estimators=200, contamination=0.008, random_state=42)
    model.fit(features)
    df["anomaly_score"] = -model.score_samples(features)  # higher = more anomalous
    df["model_flagged"] = model.predict(features) == -1

    result = df[["transaction_id", "anomaly_score", "model_flagged", *feature_cols]].copy()
    result["model_version"] = "isolation_forest_v1"
    result["scored_at"] = pd.Timestamp.now(tz="UTC")
    # Uppercase so the table's columns are standard unquoted identifiers,
    # consistent with every other table in this project (RAW/STAGING/ANALYTICS).
    result.columns = result.columns.str.upper()

    session.write_pandas(
        result,
        table_name="FLAGGED_TXNS",
        schema="ANALYTICS",
        auto_create_table=True,
        overwrite=True,
    )

    flagged_count = int(result["MODEL_FLAGGED"].sum())
    return f"Scored {len(result)} transactions, flagged {flagged_count} as anomalous."


def main():
    session = get_snowpark_session()
    try:
        detect_anomalies_sproc = session.sproc.register(
            func=detect_anomalies_proc,
            name="DETECT_ANOMALIES",
            packages=["snowflake-snowpark-python", "pandas", "numpy", "scikit-learn", "pyarrow"],
            replace=True,
        )
        result = detect_anomalies_sproc()
        print(result)
    finally:
        session.close()


if __name__ == "__main__":
    main()
