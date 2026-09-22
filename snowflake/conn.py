"""Shared Snowflake connection helper.

Uses RSA key-pair auth (not password) — this account enforces MFA for
password-based connector logins, which key-pair auth bypasses. Private key
lives in .secrets/ (gitignored, local-only, never committed).
"""

import os
from pathlib import Path

import snowflake.connector
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

PRIVATE_KEY_PATH = PROJECT_ROOT / ".secrets" / "snowflake_rsa_key.p8"


def _load_private_key_der() -> bytes:
    with open(PRIVATE_KEY_PATH, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)
    return private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )


def get_connection(
    role: str = "ACCOUNTADMIN",
    warehouse: str | None = None,
    database: str | None = None,
    schema: str | None = None,
):
    """Connect to Snowflake. Only pass warehouse/database/schema once they
    exist — Snowflake errors on connect if asked to USE an object that isn't
    there yet, which is the case for the very first setup connection."""
    kwargs = {
        "account": os.environ["SNOWFLAKE_ACCOUNT"],
        "user": os.environ["SNOWFLAKE_USER"],
        "private_key": _load_private_key_der(),
        "role": role,
    }
    if warehouse:
        kwargs["warehouse"] = warehouse
    if database:
        kwargs["database"] = database
    if schema:
        kwargs["schema"] = schema
    return snowflake.connector.connect(**kwargs)
