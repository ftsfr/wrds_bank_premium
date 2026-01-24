# WRDS Bank Regulatory Premium

WRDS Bank Regulatory Premium database tables including call reports, CRSP linkage, and LEI data.

## Overview

This pipeline pulls key tables from the WRDS Bank Regulatory Premium database, which provides comprehensive bank regulatory data.

## Tables Pulled

| Table | Description |
|-------|-------------|
| wrds_struct_rel_ultimate | Ultimate parent structure relationships |
| wrds_call_research | Call report research data (quarterly) |
| wrds_bank_crsp_link | Bank to CRSP stock linkage |
| idrssd_to_lei | RSSD ID to LEI mapping |
| lei_main | Legal Entity Identifier main data |
| lei_legalevents | LEI legal events |
| lei_otherentnames | LEI other entity names |
| lei_successorentity | LEI successor entities |

## Data Sources

- **WRDS Bank Regulatory Premium**: Requires WRDS subscription with Bank Regulatory access

## Outputs

- Individual parquet files for each table
- `ftsfr_bank_total_assets.parquet`: FTSFR format with bank total assets time series

## Requirements

- WRDS account with Bank Regulatory Premium access
- Python 3.10+

## Setup

1. Configure WRDS credentials in `~/.pgpass`
2. Install dependencies: `pip install -r requirements.txt`
3. Run pipeline: `doit`

## Academic References

### Primary Paper

- **Drechsler, Savov, and Schnabl (2017)** - "The Deposits Channel of Monetary Policy"
  - Quarterly Journal of Economics
  - Uses bank regulatory data to study monetary policy transmission

### Key Applications

- Bank balance sheet analysis
- Regulatory capital studies
- LEI data for entity resolution across datasets
