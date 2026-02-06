"""
Doit build file for WRDS Bank Regulatory Premium pipeline.

Run with: doit
"""

import os
import platform
import sys
from pathlib import Path

import chartbook

sys.path.insert(1, "./src/")

BASE_DIR = chartbook.env.get_project_root()
DATA_DIR = BASE_DIR / "_data"
OUTPUT_DIR = BASE_DIR / "_output"
OS_TYPE = "nix" if platform.system() != "Windows" else "windows"



## Helpers for handling Jupyter Notebook tasks
os.environ["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"


# fmt: off
def jupyter_execute_notebook(notebook_path):
    return f"jupyter nbconvert --execute --to notebook --ClearMetadataPreprocessor.enabled=True --inplace {notebook_path}"
def jupyter_to_html(notebook_path, output_dir=OUTPUT_DIR):
    return f"jupyter nbconvert --to html --output-dir={output_dir} {notebook_path}"
# fmt: on


def mv(from_path, to_path):
    from_path = Path(from_path)
    to_path = Path(to_path)
    to_path.mkdir(parents=True, exist_ok=True)
    if OS_TYPE == "nix":
        command = f"mv {from_path} {to_path}"
    else:
        command = f"move {from_path} {to_path}"
    return command


def task_config():
    """Create necessary directories."""
    def create_dirs():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return {
        "actions": [create_dirs],
        "targets": [DATA_DIR, OUTPUT_DIR],
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


notebook_tasks = {
    "summary_wrds_bank_premium_ipynb": {
        "path": "./src/summary_wrds_bank_premium_ipynb.py",
        "file_dep": [
            DATA_DIR / "ftsfr_bank_total_assets.parquet",
        ],
        "targets": [],
    },
}
notebook_files = []
for notebook in notebook_tasks.keys():
    pyfile_path = Path(notebook_tasks[notebook]["path"])
    notebook_files.append(pyfile_path)


def task_run_notebooks():
    """Execute summary notebooks."""
    for notebook in notebook_tasks.keys():
        pyfile_path = Path(notebook_tasks[notebook]["path"])
        notebook_path = pyfile_path.with_suffix(".ipynb")
        yield {
            "name": notebook,
            "actions": [
                f"jupytext --to notebook --output {notebook_path} {pyfile_path}",
                jupyter_execute_notebook(notebook_path),
                jupyter_to_html(notebook_path),
                mv(notebook_path, OUTPUT_DIR),
            ],
            "file_dep": [
                pyfile_path,
                *notebook_tasks[notebook]["file_dep"],
            ],
            "targets": [
                OUTPUT_DIR / f"{notebook}.html",
                *notebook_tasks[notebook]["targets"],
            ],
            "clean": True,
        }


def task_generate_pipeline_site():
    """Generate pipeline documentation site."""
    return {
        "actions": ["chartbook build -f"],
        "file_dep": [
            "chartbook.toml",
            *notebook_files,
            OUTPUT_DIR / "bank_total_assets_ew_quartile.html",
            OUTPUT_DIR / "bank_total_assets_vw_quartile.html",
        ],
        "targets": [BASE_DIR / "docs" / "index.html"],
        "verbosity": 2,
        "task_dep": ["run_notebooks", "generate_charts"],
    }
