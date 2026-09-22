"""Shared output helpers used by both generation scripts."""

import json
from pathlib import Path

import pandas as pd


def resolve_out_dir(cli_arg: str) -> Path:
    out_dir = Path(cli_arg)
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def write_df(df: pd.DataFrame, path: Path, fmt: str) -> None:
    if fmt == "csv":
        df.to_csv(path.with_suffix(".csv"), index=False)
    elif fmt == "parquet":
        df.to_parquet(path.with_suffix(".parquet"), index=False)
    else:
        raise ValueError(f"Unsupported format: {fmt}")


def write_manifest(manifest: dict, path: Path) -> None:
    path.write_text(json.dumps(manifest, indent=2, default=str))
