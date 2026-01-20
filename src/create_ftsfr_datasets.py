"""
Create FTSFR-standardized datasets from WRDS Bank Premium data.

Note: This module primarily provides reference/linking tables rather than
time series data, so the FTSFR format (unique_id, ds, y) is applied to
the wrds_call_research table which has a date column.
"""

import sys
from pathlib import Path

sys.path.insert(1, "./src/")

import pandas as pd
import chartbook

BASE_DIR = chartbook.env.get_project_root()
DATA_DIR = BASE_DIR / "_data"


def main():
    """Create FTSFR dataset from wrds_call_research table."""
    print("Loading wrds_call_research...")
    df = pd.read_parquet(DATA_DIR / "wrds_call_research.parquet")

    print(f"Total rows: {len(df)}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"Unique banks (rssd9001): {df['rssd9001'].nunique()}")

    # Select key financial metrics for FTSFR format
    # Using total assets as the primary metric
    key_cols = ["rssd9001", "date", "assets"]

    df_subset = df[key_cols].dropna()
    df_subset = df_subset.rename(columns={
        "rssd9001": "unique_id",
        "date": "ds",
        "assets": "y"
    })

    # Ensure unique_id is string
    df_subset["unique_id"] = df_subset["unique_id"].astype(str)

    # Sort and reset index
    df_subset = df_subset.sort_values(["unique_id", "ds"]).reset_index(drop=True)

    print(f"\nFTSFR dataset: {len(df_subset)} rows, {df_subset['unique_id'].nunique()} unique banks")

    df_subset.to_parquet(DATA_DIR / "ftsfr_bank_total_assets.parquet")
    print("Saved ftsfr_bank_total_assets.parquet")

    print("\nDone!")


if __name__ == "__main__":
    main()
