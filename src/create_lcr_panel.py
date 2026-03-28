"""
Create GSIB Liquidity Coverage Ratio (LCR) proxy panel.

Reads call report data from wrds_call_research.parquet, filters to GSIB subsidiary
banks, computes proxy HQLA and cash outflows using Basel III standard runoff rates,
and produces both bank-level and BHC-level panels.

LCR = Total HQLA / Total Net Cash Outflows (30-day), expressed as %
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(1, "./src/")
import chartbook

BASE_DIR = chartbook.env.get_project_root()
DATA_DIR = BASE_DIR / "_data"
DATA_MANUAL_DIR = BASE_DIR / "data_manual"

# BHC name -> list of subsidiary bank RSSD IDs found in call report data.
# Derived from wrds_struct_rel_ultimate (2024) with manual corrections for
# Morgan Stanley (ultimate parent is MUFG in the structure table due to
# ownership structure, but MS is the relevant BHC for LCR reporting).
BHC_TO_BANKS = {
    "JPMorgan Chase": [852218, 651448, 906915],
    "Bank of America": [480228, 783871, 1443266, 2138626],
    "Citigroup": [476810, 449038, 750864, 938019],
    "Wells Fargo": [451965, 24837, 688079, 1225761, 2362458, 2531991, 3385968],
    "Goldman Sachs": [2182786, 3066025],
    "Morgan Stanley": [1456501, 2489805],
    "BNY Mellon": [541101, 398668, 488318, 720317, 934329, 978819],
    "State Street": [35301, 93619, 348104, 812164, 1865091],
}

# Reverse mapping: bank RSSD -> BHC name
BANK_TO_BHC = {}
for bhc_name, bank_rssds in BHC_TO_BANKS.items():
    for rssd in bank_rssds:
        BANK_TO_BHC[rssd] = bhc_name

ALL_BANK_RSSDIDS = set(BANK_TO_BHC.keys())

# Columns needed from wrds_call_research for LCR computation
HQLA_COLS = ["cash", "treasurysec", "usgovobligations", "mbsassets"]
OUTFLOW_COLS = [
    "deposits",
    "domdepuninsured",
    "brokereddep",
    "foreigndep",
    "fedfundsrepoliab",
    "otherborrowedmoney",
]
KEEP_COLS = ["rssd9001", "date"] + HQLA_COLS + OUTFLOW_COLS

# HQLA and outflow component columns created during computation
HQLA_COMPONENT_COLS = [
    "level1_hqla",
    "level2a_gross",
    "level2a_haircut",
    "level2a_capped",
    "total_hqla",
]
OUTFLOW_COMPONENT_COLS = [
    "insured_deposits",
    "uninsured_non_brokered",
    "outflow_insured",
    "outflow_uninsured",
    "outflow_brokered",
    "outflow_foreign",
    "outflow_repo",
    "outflow_other_borrowed",
    "total_net_outflows",
]
ALL_COMPONENT_COLS = HQLA_COMPONENT_COLS + OUTFLOW_COMPONENT_COLS
SUMMABLE_COLS = ALL_COMPONENT_COLS  # All component columns can be summed for BHC aggregation


def compute_proxy_hqla(df):
    """Add HQLA component columns to the dataframe."""
    df["level1_hqla"] = df["cash"] + df["treasurysec"] + df["usgovobligations"]
    df["level2a_gross"] = df["mbsassets"]
    df["level2a_haircut"] = df["level2a_gross"] * 0.85  # 15% haircut
    # Basel III: Level 2 cannot exceed 40% of total HQLA.
    # If L2 = 40% of total, then L1 = 60%, so L2/L1 = 2/3.
    df["level2a_capped"] = np.minimum(df["level2a_haircut"], df["level1_hqla"] * (2 / 3))
    df["total_hqla"] = df["level1_hqla"] + df["level2a_capped"]
    return df


def compute_proxy_outflows(df):
    """Add outflow component columns to the dataframe."""
    # Use domestic deposits for insured/uninsured split to avoid
    # double-counting foreign deposits (which get their own runoff rate).
    df["insured_deposits"] = (df["deposits"] - df["domdepuninsured"]).clip(lower=0)
    df["uninsured_non_brokered"] = (df["domdepuninsured"] - df["brokereddep"]).clip(lower=0)

    # Apply Basel III standard runoff rates
    df["outflow_insured"] = df["insured_deposits"] * 0.05
    df["outflow_uninsured"] = df["uninsured_non_brokered"] * 0.25
    df["outflow_brokered"] = df["brokereddep"] * 0.25
    df["outflow_foreign"] = df["foreigndep"] * 0.40
    df["outflow_repo"] = df["fedfundsrepoliab"] * 0.25
    df["outflow_other_borrowed"] = df["otherborrowedmoney"] * 0.25

    df["total_net_outflows"] = (
        df["outflow_insured"]
        + df["outflow_uninsured"]
        + df["outflow_brokered"]
        + df["outflow_foreign"]
        + df["outflow_repo"]
        + df["outflow_other_borrowed"]
    )
    # Floor to avoid division by zero
    df["total_net_outflows"] = df["total_net_outflows"].clip(lower=1.0)
    return df


def compute_proxy_lcr(df):
    """Add proxy LCR column (expressed as percentage)."""
    df["proxy_lcr"] = (df["total_hqla"] / df["total_net_outflows"]) * 100
    return df


def aggregate_to_bhc(df):
    """Aggregate bank-level components to BHC level and recompute LCR.

    For each BHC and quarter, sums HQLA and outflow component columns across
    all subsidiary banks, then recomputes proxy_lcr from the summed components.
    """
    df["bhc_name"] = df["rssd9001"].map(BANK_TO_BHC)

    bhc_df = (
        df.groupby(["bhc_name", "date"])[SUMMABLE_COLS]
        .sum()
        .reset_index()
    )
    # Recompute LCR from aggregated components
    bhc_df["total_net_outflows"] = bhc_df["total_net_outflows"].clip(lower=1.0)
    bhc_df["proxy_lcr"] = (bhc_df["total_hqla"] / bhc_df["total_net_outflows"]) * 100
    return bhc_df


def main():
    print("Loading wrds_call_research.parquet...")
    df = pd.read_parquet(DATA_DIR / "wrds_call_research.parquet", columns=KEEP_COLS)

    # Filter to GSIB subsidiary banks
    df = df[df["rssd9001"].isin(ALL_BANK_RSSDIDS)].copy()
    df = df.dropna(subset=["date"])
    print(f"GSIB subsidiary banks: {df['rssd9001'].nunique()}")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"Total bank-quarters: {len(df)}")

    # Fill NaN values in numeric columns with 0 for computation
    for col in HQLA_COLS + OUTFLOW_COLS:
        df[col] = df[col].fillna(0)

    # Compute bank-level LCR components
    print("\nComputing bank-level proxy HQLA...")
    df = compute_proxy_hqla(df)
    print("Computing bank-level proxy outflows...")
    df = compute_proxy_outflows(df)
    print("Computing bank-level proxy LCR...")
    df = compute_proxy_lcr(df)

    # Map bank RSSD to bank name for display
    bank_names = {
        852218: "JPMorgan Chase Bank, N.A.",
        651448: "JPMorgan Chase Bank, Dearborn",
        906915: "J.P. Morgan International Finance",
        480228: "Bank of America, N.A.",
        783871: "Bank of America Oregon",
        1443266: "Bank of America California",
        2138626: "Bank of America (misc.)",
        476810: "Citibank, N.A.",
        449038: "Citibank (South Dakota)",
        750864: "Citibank (misc. 1)",
        938019: "Citibank (misc. 2)",
        451965: "Wells Fargo Bank, N.A.",
        24837: "Wells Fargo (misc. 1)",
        688079: "Wells Fargo (misc. 2)",
        1225761: "Wells Fargo (misc. 3)",
        2362458: "Wells Fargo (misc. 4)",
        2531991: "Wells Fargo (misc. 5)",
        3385968: "Wells Fargo (misc. 6)",
        2182786: "Goldman Sachs Bank USA",
        3066025: "Goldman Sachs (misc.)",
        1456501: "Morgan Stanley Bank, N.A.",
        2489805: "Morgan Stanley Private Bank",
        541101: "The Bank of New York Mellon",
        398668: "BNY Mellon (misc. 1)",
        488318: "BNY Mellon (misc. 2)",
        720317: "BNY Mellon (misc. 3)",
        934329: "BNY Mellon (misc. 4)",
        978819: "BNY Mellon (misc. 5)",
        35301: "State Street Bank and Trust",
        93619: "State Street (misc. 1)",
        348104: "State Street (misc. 2)",
        812164: "State Street (misc. 3)",
        1865091: "State Street (misc. 4)",
    }
    df["bank_name"] = df["rssd9001"].map(bank_names)

    # Print bank-level summary
    print("\nBank-level proxy LCR summary:")
    bank_summary = df.groupby("bank_name")["proxy_lcr"].agg(["mean", "min", "max", "count"])
    print(bank_summary.to_string())

    # --- Bank-level outputs ---

    # FTSFR format: unique_id, ds, y
    bank_panel = df[["bank_name", "date", "proxy_lcr"]].rename(
        columns={"bank_name": "unique_id", "date": "ds", "proxy_lcr": "y"}
    )
    bank_panel["unique_id"] = bank_panel["unique_id"].astype(str)
    bank_panel = bank_panel.sort_values(["unique_id", "ds"]).reset_index(drop=True)
    bank_panel.to_parquet(DATA_DIR / "ftsfr_gsib_lcr_bank_panel.parquet")
    print(f"\nSaved bank-level FTSFR panel: {len(bank_panel)} rows")

    # Wide components
    bank_component_cols = ["rssd9001", "bank_name", "date"] + ALL_COMPONENT_COLS + ["proxy_lcr"]
    bank_components = df[bank_component_cols].sort_values(["bank_name", "date"]).reset_index(drop=True)
    bank_components.to_parquet(DATA_DIR / "ftsfr_gsib_lcr_bank_components.parquet")
    print(f"Saved bank-level components: {len(bank_components)} rows")

    # --- BHC-level outputs ---

    print("\nAggregating to BHC level...")
    bhc_df = aggregate_to_bhc(df)

    # Print BHC-level summary
    print("\nBHC-level proxy LCR summary:")
    bhc_summary = bhc_df.groupby("bhc_name")["proxy_lcr"].agg(["mean", "min", "max", "count"])
    print(bhc_summary.to_string())

    # FTSFR format
    bhc_panel = bhc_df[["bhc_name", "date", "proxy_lcr"]].rename(
        columns={"bhc_name": "unique_id", "date": "ds", "proxy_lcr": "y"}
    )
    bhc_panel["unique_id"] = bhc_panel["unique_id"].astype(str)
    bhc_panel = bhc_panel.sort_values(["unique_id", "ds"]).reset_index(drop=True)
    bhc_panel.to_parquet(DATA_DIR / "ftsfr_gsib_lcr_bhc_panel.parquet")
    print(f"\nSaved BHC-level FTSFR panel: {len(bhc_panel)} rows")

    # Wide components
    bhc_component_cols = ["bhc_name", "date"] + ALL_COMPONENT_COLS + ["proxy_lcr"]
    bhc_components = bhc_df[bhc_component_cols].sort_values(["bhc_name", "date"]).reset_index(drop=True)
    bhc_components.to_parquet(DATA_DIR / "ftsfr_gsib_lcr_bhc_components.parquet")
    print(f"Saved BHC-level components: {len(bhc_components)} rows")

    # --- Optional: compare with reported LCR ---
    reported_path = DATA_MANUAL_DIR / "gsib_reported_lcr.csv"
    if reported_path.exists():
        print("\nLoading reported LCR data for comparison...")
        reported = pd.read_csv(reported_path, parse_dates=["date"])
        merged = bhc_panel.merge(
            reported.rename(columns={"bhc_name": "unique_id", "date": "ds"}),
            on=["unique_id", "ds"],
            how="inner",
        )
        if len(merged) > 0:
            print(f"Matched {len(merged)} BHC-quarters with reported LCR")
            merged["diff"] = merged["y"] - merged["reported_lcr_pct"]
            print(f"Mean proxy - reported: {merged['diff'].mean():.1f} pp")
            print(f"Median proxy - reported: {merged['diff'].median():.1f} pp")
        else:
            print("No matching quarters found between proxy and reported LCR")
    else:
        print(f"\nNo reported LCR file found at {reported_path}. Skipping comparison.")

    print("\nDone!")


if __name__ == "__main__":
    main()
