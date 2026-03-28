# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.18.1
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# %% [markdown]
# # GSIB Liquidity Coverage Ratio (LCR) Proxy Panel
#
# This notebook analyzes proxy LCR calculations for the 8 US GSIB holding companies
# using call report data from the WRDS Bank Regulatory Premium database.
#
# ## Methodology
#
# - **HQLA**: Level 1 (cash + Treasuries + US gov) + Level 2A (agency MBS, 15% haircut, 40% cap)
# - **Outflows**: Basel III standard runoff rates applied to deposit and liability categories
# - **LCR**: Total HQLA / Total Net Cash Outflows (30-day), expressed as percentage

# %%
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import chartbook

BASE_DIR = chartbook.env.get_project_root()
DATA_DIR = BASE_DIR / "_data"
DATA_MANUAL_DIR = BASE_DIR / "data_manual"

# %% [markdown]
# ## Load Data

# %%
bhc_panel = pd.read_parquet(DATA_DIR / "ftsfr_gsib_lcr_bhc_panel.parquet")
bhc_components = pd.read_parquet(DATA_DIR / "ftsfr_gsib_lcr_bhc_components.parquet")
bank_panel = pd.read_parquet(DATA_DIR / "ftsfr_gsib_lcr_bank_panel.parquet")
bank_components = pd.read_parquet(DATA_DIR / "ftsfr_gsib_lcr_bank_components.parquet")

# Focus on LCR era (2017+)
bhc_panel = bhc_panel[bhc_panel["ds"] >= "2017-01-01"].copy()
bhc_components = bhc_components[bhc_components["date"] >= "2017-01-01"].copy()
bank_panel = bank_panel[bank_panel["ds"] >= "2017-01-01"].copy()

print(f"BHC panel: {bhc_panel.shape}, {bhc_panel['unique_id'].nunique()} BHCs")
print(f"Bank panel: {bank_panel.shape}, {bank_panel['unique_id'].nunique()} banks")
print(f"Date range: {bhc_panel['ds'].min()} to {bhc_panel['ds'].max()}")

# %% [markdown]
# ## BHC-Level Proxy LCR Time Series

# %%
fig, ax = plt.subplots(figsize=(14, 7))
for bhc in sorted(bhc_panel["unique_id"].unique()):
    data = bhc_panel[bhc_panel["unique_id"] == bhc]
    ax.plot(data["ds"], data["y"], label=bhc, marker="o", markersize=3)

ax.axhline(y=100, color="red", linestyle="--", alpha=0.7, label="100% Minimum")
ax.set_xlabel("Date")
ax.set_ylabel("Proxy LCR (%)")
ax.set_title("GSIB Proxy Liquidity Coverage Ratio (BHC Level)")
ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=9)
plt.tight_layout()
plt.show()

# %% [markdown]
# ## Bank-Level Proxy LCR Time Series
#
# Individual subsidiary bank LCR proxies. Only showing primary bank subsidiaries
# (those with consistent data over the period).

# %%
# Filter to primary bank subsidiaries (those with >= 25 quarters of data in 2017+)
bank_counts = bank_panel.groupby("unique_id").size()
primary_banks = bank_counts[bank_counts >= 25].index.tolist()
bank_primary = bank_panel[bank_panel["unique_id"].isin(primary_banks)]

fig, ax = plt.subplots(figsize=(14, 7))
for bank in sorted(bank_primary["unique_id"].unique()):
    data = bank_primary[bank_primary["unique_id"] == bank]
    ax.plot(data["ds"], data["y"], label=bank, marker="o", markersize=2)

ax.axhline(y=100, color="red", linestyle="--", alpha=0.7, label="100% Minimum")
ax.set_xlabel("Date")
ax.set_ylabel("Proxy LCR (%)")
ax.set_title("GSIB Proxy LCR (Primary Subsidiary Banks)")
ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=8)
plt.tight_layout()
plt.show()

# %% [markdown]
# ## HQLA Composition (BHC Level)
#
# Breakdown of Level 1 and Level 2A HQLA for each GSIB over time.

# %%
fig, axes = plt.subplots(2, 4, figsize=(18, 8), sharex=True)
axes = axes.flatten()

for i, bhc in enumerate(sorted(bhc_components["bhc_name"].unique())):
    data = bhc_components[bhc_components["bhc_name"] == bhc].sort_values("date")
    ax = axes[i]
    ax.fill_between(data["date"], 0, data["level1_hqla"] / 1e6, alpha=0.7, label="Level 1")
    ax.fill_between(
        data["date"],
        data["level1_hqla"] / 1e6,
        (data["level1_hqla"] + data["level2a_capped"]) / 1e6,
        alpha=0.7,
        label="Level 2A",
    )
    ax.set_title(bhc, fontsize=10)
    ax.set_ylabel("HQLA ($B)" if i % 4 == 0 else "")
    ax.tick_params(axis="x", rotation=45)

axes[0].legend(fontsize=8)
fig.suptitle("HQLA Composition by BHC (Billions)", fontsize=13)
plt.tight_layout()
plt.show()

# %% [markdown]
# ## Cash Outflow Components (BHC Level)
#
# Breakdown of outflow categories for each GSIB at the latest available quarter.

# %%
latest_date = bhc_components["date"].max()
latest = bhc_components[bhc_components["date"] == latest_date].set_index("bhc_name")

outflow_cats = [
    "outflow_insured",
    "outflow_uninsured",
    "outflow_brokered",
    "outflow_foreign",
    "outflow_repo",
    "outflow_other_borrowed",
]
outflow_labels = [
    "Insured (5%)",
    "Uninsured (25%)",
    "Brokered (25%)",
    "Foreign (40%)",
    "Repo (25%)",
    "Other Borrowed (25%)",
]

fig, ax = plt.subplots(figsize=(14, 6))
latest_outflows = latest[outflow_cats].div(1e6)  # Convert to billions
latest_outflows.columns = outflow_labels
latest_outflows.plot(kind="barh", stacked=True, ax=ax)
ax.set_xlabel(f"Outflow Amount ($B) as of {latest_date.strftime('%Y-%m-%d')}")
ax.set_title("Cash Outflow Components by BHC")
ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=9)
plt.tight_layout()
plt.show()

# %% [markdown]
# ## Summary Statistics

# %%
summary = bhc_components.groupby("bhc_name").agg(
    mean_lcr=("proxy_lcr", "mean"),
    min_lcr=("proxy_lcr", "min"),
    max_lcr=("proxy_lcr", "max"),
    mean_hqla_B=("total_hqla", lambda x: x.mean() / 1e6),
    mean_outflows_B=("total_net_outflows", lambda x: x.mean() / 1e6),
    quarters=("proxy_lcr", "count"),
)
summary = summary.round(1)
summary

# %% [markdown]
# ## Comparison with Reported LCR
#
# Comparing the BHC-level proxy LCR with publicly reported BHC-level LCR values.
#
# Note: reported values are from BHC Pillar 3 disclosures (consolidated BHC level).
# The proxy is constructed from call report data aggregated across subsidiary banks.
# Differences are expected due to methodology (standard vs actual runoff rates,
# missing off-balance-sheet outflows, etc.).

# %%
reported = pd.read_csv(DATA_MANUAL_DIR / "gsib_reported_lcr.csv", parse_dates=["date"])
reported = reported.rename(columns={"bhc_name": "unique_id", "date": "ds"})

merged = bhc_panel.merge(reported, on=["unique_id", "ds"], how="inner")

print(f"Matched {len(merged)} BHC-quarters with reported LCR")
print(f"Mean proxy LCR: {merged['y'].mean():.1f}%")
print(f"Mean reported LCR: {merged['reported_lcr_pct'].mean():.1f}%")
print(f"Mean difference (proxy - reported): {(merged['y'] - merged['reported_lcr_pct']).mean():.1f} pp")

# Scatter: proxy vs reported
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

ax = axes[0]
for bhc in sorted(merged["unique_id"].unique()):
    d = merged[merged["unique_id"] == bhc]
    ax.scatter(d["reported_lcr_pct"], d["y"], label=bhc, s=40, alpha=0.8)
lims = [80, max(merged["y"].max(), merged["reported_lcr_pct"].max()) + 20]
ax.plot(lims, lims, "k--", alpha=0.5, label="45-degree line")
ax.set_xlabel("Reported LCR (%)")
ax.set_ylabel("Proxy LCR (%)")
ax.set_title("Proxy vs Reported LCR")
ax.legend(fontsize=8)

# Time series overlay for selected banks
ax = axes[1]
for bhc in sorted(merged["unique_id"].unique()):
    d = merged[merged["unique_id"] == bhc].sort_values("ds")
    ax.plot(d["ds"], d["y"], marker="o", markersize=4, label=f"{bhc} (proxy)")
    ax.plot(
        d["ds"],
        d["reported_lcr_pct"],
        marker="x",
        markersize=6,
        linestyle="--",
        alpha=0.6,
    )
ax.axhline(y=100, color="red", linestyle="--", alpha=0.5)
ax.set_xlabel("Date")
ax.set_ylabel("LCR (%)")
ax.set_title("Proxy (solid) vs Reported (dashed) LCR")
ax.legend(fontsize=7, bbox_to_anchor=(1.05, 1), loc="upper left")

plt.tight_layout()
plt.show()
