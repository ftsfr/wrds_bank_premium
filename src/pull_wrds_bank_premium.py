"""
Pull selected premium tables from WRDS Bank Regulatory database.
"""

import sys
from pathlib import Path

sys.path.insert(1, "./src/")

import pandas as pd
import wrds
import chartbook

BASE_DIR = chartbook.env.get_project_root()
DATA_DIR = BASE_DIR / "_data"
WRDS_USERNAME = chartbook.env.get("WRDS_USERNAME")


def pull_selected_premium_tables(wrds_username=WRDS_USERNAME):
    """Pull selected tables from WRDS Bank Regulatory Premium database."""
    db = wrds.Connection(wrds_username=wrds_username)

    print("Pulling wrds_struct_rel_ultimate...")
    wrds_struct_rel_ultimate = db.get_table(
        library="bank", table="wrds_struct_rel_ultimate"
    )

    print("Pulling wrds_call_research...")
    wrds_call_research = db.get_table(library="bank", table="wrds_call_research")
    wrds_call_research["date"] = pd.to_datetime(wrds_call_research["date"])

    print("Pulling wrds_bank_crsp_link...")
    wrds_bank_crsp_link = db.get_table(library="bank", table="wrds_bank_crsp_link")

    print("Pulling idrssd_to_lei...")
    idrssd_to_lei = db.get_table(library="bank", table="idrssd_to_lei")

    print("Pulling lei_main...")
    lei_main = db.get_table(
        library="bank",
        table="lei_main",
        columns=[
            "lei_record_id",
            "most_recent",
            "lei",
            "legalname",
            "entitycategory",
            "entitystatus",
            "rec_bdate",
            "rec_edate",
        ],
    )

    print("Pulling lei_legalevents...")
    lei_legalevents = db.get_table(library="bank", table="lei_legalevents")

    print("Pulling lei_otherentnames...")
    lei_otherentnames = db.get_table(library="bank", table="lei_otherentnames")

    print("Pulling lei_successorentity...")
    lei_successorentity = db.get_table(library="bank", table="lei_successorentity")

    db.close()

    selected_tables = {
        "wrds_struct_rel_ultimate": wrds_struct_rel_ultimate,
        "wrds_call_research": wrds_call_research,
        "wrds_bank_crsp_link": wrds_bank_crsp_link,
        "idrssd_to_lei": idrssd_to_lei,
        "lei_main": lei_main,
        "lei_legalevents": lei_legalevents,
        "lei_otherentnames": lei_otherentnames,
        "lei_successorentity": lei_successorentity,
    }
    return selected_tables


AVAILABLE_TABLES = [
    "wrds_struct_rel_ultimate",
    "wrds_call_research",
    "wrds_bank_crsp_link",
    "idrssd_to_lei",
    "lei_main",
    "lei_legalevents",
    "lei_otherentnames",
    "lei_successorentity",
]


def load_table(table_name, data_dir=DATA_DIR):
    """Load a specific table from parquet file."""
    if table_name not in AVAILABLE_TABLES:
        raise ValueError(f"Table {table_name} not available. Choose from: {AVAILABLE_TABLES}")
    return pd.read_parquet(data_dir / f"{table_name}.parquet")


if __name__ == "__main__":
    # Create data directory
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Pull data
    print("Pulling WRDS Bank Premium tables...")
    selected_tables = pull_selected_premium_tables(wrds_username=WRDS_USERNAME)

    for table_name, df in selected_tables.items():
        output_path = DATA_DIR / f"{table_name}.parquet"
        df.to_parquet(output_path)
        print(f"Saved {table_name}: {len(df)} rows")

    print("\nDone!")
