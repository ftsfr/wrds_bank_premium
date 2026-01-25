"""Generate interactive HTML charts for WRDS Bank Premium aggregated total assets data."""

import pandas as pd
import plotly.express as px
from pathlib import Path

# Get the project root (one level up from src/)
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "_data"
OUTPUT_DIR = PROJECT_ROOT / "_output"

# Define quartile order and labels
QUARTILE_ORDER_EW = ["Q1_small_ew", "Q2_ew", "Q3_ew", "Q4_large_ew"]
QUARTILE_ORDER_VW = ["Q1_small_vw", "Q2_vw", "Q3_vw", "Q4_large_vw"]

QUARTILE_LABELS = {
    "Q1_small_ew": "Q1 (Smallest Banks)",
    "Q2_ew": "Q2",
    "Q3_ew": "Q3",
    "Q4_large_ew": "Q4 (Largest Banks)",
    "Q1_small_vw": "Q1 (Smallest Banks)",
    "Q2_vw": "Q2",
    "Q3_vw": "Q3",
    "Q4_large_vw": "Q4 (Largest Banks)",
}


def generate_ew_quartile_chart():
    """Generate equal-weight quartile total assets chart."""
    df = pd.read_parquet(DATA_DIR / "ftsfr_bank_total_assets_ew_quartile.parquet")

    # Map unique_id to readable labels
    df["Quartile"] = df["unique_id"].map(QUARTILE_LABELS)

    # Sort by quartile order
    df["sort_order"] = df["unique_id"].apply(lambda x: QUARTILE_ORDER_EW.index(x))
    df = df.sort_values(["sort_order", "ds"])

    fig = px.line(
        df,
        x="ds",
        y="y",
        color="Quartile",
        title="Bank Total Assets by Size Quartile (Equal-Weight)",
        labels={
            "ds": "Date",
            "y": "Total Assets (thousands)",
            "Quartile": "Size Quartile"
        },
        category_orders={"Quartile": [QUARTILE_LABELS[q] for q in QUARTILE_ORDER_EW]}
    )

    fig.update_layout(
        template="plotly_white",
        hovermode="x unified"
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "bank_total_assets_ew_quartile.html"
    fig.write_html(str(output_path))
    print(f"Chart saved to {output_path}")

    return fig


def generate_vw_quartile_chart():
    """Generate value-weight quartile total assets chart."""
    df = pd.read_parquet(DATA_DIR / "ftsfr_bank_total_assets_vw_quartile.parquet")

    # Map unique_id to readable labels
    df["Quartile"] = df["unique_id"].map(QUARTILE_LABELS)

    # Sort by quartile order
    df["sort_order"] = df["unique_id"].apply(lambda x: QUARTILE_ORDER_VW.index(x))
    df = df.sort_values(["sort_order", "ds"])

    fig = px.line(
        df,
        x="ds",
        y="y",
        color="Quartile",
        title="Bank Total Assets by Size Quartile (Value-Weight)",
        labels={
            "ds": "Date",
            "y": "Total Assets (thousands)",
            "Quartile": "Size Quartile"
        },
        category_orders={"Quartile": [QUARTILE_LABELS[q] for q in QUARTILE_ORDER_VW]}
    )

    fig.update_layout(
        template="plotly_white",
        hovermode="x unified"
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "bank_total_assets_vw_quartile.html"
    fig.write_html(str(output_path))
    print(f"Chart saved to {output_path}")

    return fig


if __name__ == "__main__":
    generate_ew_quartile_chart()
    generate_vw_quartile_chart()
