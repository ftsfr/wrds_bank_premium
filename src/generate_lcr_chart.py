"""Generate interactive HTML chart for GSIB proxy LCR panel."""

import pandas as pd
import plotly.express as px
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "_data"
OUTPUT_DIR = PROJECT_ROOT / "_output"


def generate_lcr_chart():
    """Generate BHC-level proxy LCR time series chart."""
    df = pd.read_parquet(DATA_DIR / "ftsfr_gsib_lcr_bhc_panel.parquet")

    # Filter to LCR era (2017+) for a cleaner chart
    df = df[df["ds"] >= "2017-01-01"].copy()
    df = df.sort_values(["unique_id", "ds"])

    fig = px.line(
        df,
        x="ds",
        y="y",
        color="unique_id",
        title="GSIB Proxy Liquidity Coverage Ratio (BHC Level)",
        labels={
            "ds": "Date",
            "y": "Proxy LCR (%)",
            "unique_id": "Bank Holding Company",
        },
    )

    # Add 100% minimum threshold line
    fig.add_hline(
        y=100,
        line_dash="dash",
        line_color="red",
        annotation_text="100% Minimum",
        annotation_position="bottom right",
    )

    fig.update_layout(
        template="plotly_white",
        hovermode="x unified",
        legend=dict(title="Bank Holding Company"),
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "gsib_lcr_proxy.html"
    fig.write_html(str(output_path))
    print(f"Chart saved to {output_path}")

    return fig


if __name__ == "__main__":
    generate_lcr_chart()
