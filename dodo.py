"""
Doit build file for WRDS Bank Regulatory Premium pipeline.

Run with: doit
"""

import platform
import sys
from pathlib import Path

import chartbook

sys.path.insert(1, "./src/")

BASE_DIR = chartbook.env.get_project_root()
DATA_DIR = BASE_DIR / "_data"
OUTPUT_DIR = BASE_DIR / "_output"
OS_TYPE = "nix" if platform.system() != "Windows" else "windows"


def jupyter_execute_notebook(notebook):
    """Execute a Jupyter notebook and save output."""
    return (
        f"jupyter nbconvert --execute --to notebook "
        f'--ClearMetadataPreprocessor.enabled=True --inplace "{notebook}"'
    )


def jupyter_to_html(notebook, output_dir):
    """Convert notebook to HTML."""
    return (
        f'jupyter nbconvert --to html --output-dir="{output_dir}" "{notebook}"'
    )


def task_config():
    """Create necessary directories."""
    return {
        "actions": [
            f'mkdir -p "{DATA_DIR}"' if OS_TYPE == "nix" else f'if not exist "{DATA_DIR}" mkdir "{DATA_DIR}"',
            f'mkdir -p "{OUTPUT_DIR}"' if OS_TYPE == "nix" else f'if not exist "{OUTPUT_DIR}" mkdir "{OUTPUT_DIR}"',
            f'mkdir -p "{OUTPUT_DIR}/_notebook_build"' if OS_TYPE == "nix" else f'if not exist "{OUTPUT_DIR}/_notebook_build" mkdir "{OUTPUT_DIR}/_notebook_build"',
        ],
        "verbosity": 2,
    }


def task_pull():
    """Pull WRDS Bank Premium tables."""
    return {
        "actions": ["python src/pull_wrds_bank_premium.py"],
        "file_dep": ["src/pull_wrds_bank_premium.py"],
        "targets": [
            DATA_DIR / "wrds_struct_rel_ultimate.parquet",
            DATA_DIR / "wrds_call_research.parquet",
            DATA_DIR / "wrds_bank_crsp_link.parquet",
            DATA_DIR / "idrssd_to_lei.parquet",
            DATA_DIR / "lei_main.parquet",
            DATA_DIR / "lei_legalevents.parquet",
            DATA_DIR / "lei_otherentnames.parquet",
            DATA_DIR / "lei_successorentity.parquet",
        ],
        "verbosity": 2,
        "task_dep": ["config"],
    }


def task_format():
    """Create FTSFR datasets."""
    return {
        "actions": ["python src/create_ftsfr_datasets.py"],
        "file_dep": [
            "src/create_ftsfr_datasets.py",
            DATA_DIR / "wrds_call_research.parquet",
        ],
        "targets": [DATA_DIR / "ftsfr_bank_total_assets.parquet"],
        "verbosity": 2,
        "task_dep": ["pull"],
    }


def task_aggregate():
    """Create aggregated total assets datasets by size quartiles."""
    return {
        "actions": ["python src/create_aggregated_assets.py"],
        "file_dep": [
            "src/create_aggregated_assets.py",
            DATA_DIR / "ftsfr_bank_total_assets.parquet",
        ],
        "targets": [
            DATA_DIR / "ftsfr_bank_total_assets_ew_quartile.parquet",
            DATA_DIR / "ftsfr_bank_total_assets_vw_quartile.parquet",
        ],
        "verbosity": 2,
        "task_dep": ["format"],
    }


def task_generate_charts():
    """Generate aggregated total assets charts."""
    return {
        "actions": ["python src/generate_chart.py"],
        "file_dep": [
            "src/generate_chart.py",
            DATA_DIR / "ftsfr_bank_total_assets_ew_quartile.parquet",
            DATA_DIR / "ftsfr_bank_total_assets_vw_quartile.parquet",
        ],
        "targets": [
            OUTPUT_DIR / "bank_total_assets_ew_quartile.html",
            OUTPUT_DIR / "bank_total_assets_vw_quartile.html",
        ],
        "verbosity": 2,
        "task_dep": ["aggregate"],
    }


def task_run_notebooks():
    """Execute summary notebooks."""
    notebook_py = BASE_DIR / "src" / "summary_wrds_bank_premium_ipynb.py"
    notebook_ipynb = OUTPUT_DIR / "summary_wrds_bank_premium_ipynb.ipynb"

    actions = [
        f'ipynb-py-convert "{notebook_py}" "{notebook_ipynb}"',
        jupyter_execute_notebook(notebook_ipynb),
        jupyter_to_html(notebook_ipynb, OUTPUT_DIR),
    ]

    return {
        "actions": actions,
        "file_dep": [
            notebook_py,
            DATA_DIR / "ftsfr_bank_total_assets.parquet",
        ],
        "targets": [
            notebook_ipynb,
            OUTPUT_DIR / "summary_wrds_bank_premium_ipynb.html",
        ],
        "verbosity": 2,
        "task_dep": ["format"],
    }


def task_generate_pipeline_site():
    """Generate pipeline documentation site."""
    return {
        "actions": ["chartbook build -f"],
        "file_dep": [
            "chartbook.toml",
            OUTPUT_DIR / "summary_wrds_bank_premium_ipynb.ipynb",
            OUTPUT_DIR / "bank_total_assets_ew_quartile.html",
            OUTPUT_DIR / "bank_total_assets_vw_quartile.html",
        ],
        "targets": [BASE_DIR / "docs" / "index.html"],
        "verbosity": 2,
        "task_dep": ["run_notebooks", "generate_charts"],
    }
