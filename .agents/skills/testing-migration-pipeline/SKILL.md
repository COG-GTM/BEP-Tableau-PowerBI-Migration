# Testing the BEP Tableau-to-Power BI Migration Pipeline

## Overview
This skill covers end-to-end testing of the migration pipeline that converts Tableau dashboards to Power BI artifacts (DAX, TMDL, Power Query M, layouts, themes) and validates conversion accuracy.

## Prerequisites
- Python 3.12+ with packages: pandas, numpy, pytest, python-docx, tabulate, jinja2
- Install via: `pip install -r requirements.txt && pip install -r validation/requirements.txt`

## Running the Full Pipeline
```bash
# With docx file (parses dashboard definitions from document)
bash scripts/run_full_pipeline.sh "/path/to/dashboards.docx"

# Without docx (uses 4 default dashboards)
bash scripts/run_full_pipeline.sh
```

The pipeline runs 6 steps:
1. Install dependencies
2. Parse docx (or use defaults)
3. Generate cleaned datasets to `conversion-output/powerbi-ready/`
4. Verify all 24 conversion artifacts exist (4 dashboards × 6 files)
5. Run pytest validation suite (36 tests)
6. Generate validation reports and print summary

## Key Verification Points

### Dataset Row Counts (expected values)
| Dataset | Expected Rows |
|---------|---------------|
| Orders_clean.csv | 9,994 |
| Customers_clean.csv | 793 |
| Products_clean.csv | 1,894 |
| Location_clean.csv | 632 |
| HR_clean.csv | 8,950 |
| Vulnerabilities_clean.csv | 200 |
| JIRA_Issues_clean.csv | 300 |

### Validation Tests (36 total)
- Sales Dashboard: 8 tests (CY/PY sales, YoY %, LOD orders per customer, min/max, KPIs)
- HR Dashboard: 10 tests (hired/terminated/active counts, status, location, age, groups)
- CISO Dashboard: 9 tests (critical/high counts, MTTR, risk scores, remediation rate)
- IT PM Dashboard: 9 tests (velocity, burndown, cycle time, bug escape rate, scope creep)

### Running Tests Independently
```bash
# All tests
pytest validation/ -v

# Single dashboard
pytest validation/test_sales_dashboard.py -v

# Generate validation reports (markdown + JSON)
python3 validation/run_validation.py
```

## Common Issues & Workarounds

### Double Date-Parsing Bug in Power Query M
A common bug pattern in `.tmdl` and `.pq` files: the `ChangedTypes` step converts date columns to `type date`, then a subsequent step tries to use `Text.Middle`/`Text.Start`/`Text.Split` on those values. Since they're already date objects, text functions fail.

**Detection**: Look for `type date` in `ChangedTypes` followed by text manipulation of the same column.
**Fix**: Change `type date` to `type text` in `ChangedTypes` so the text parsing step receives string values.

This pattern might appear in any dashboard's `.tmdl` or `.pq` files — always spot-check after generation.

### EU Dataset Formatting
The HR dataset (`projects/hr-dashboard-project/dataset.csv`) uses:
- Semicolon delimiters (not commas)
- DD/MM/YYYY date format
- The dataset cleaner handles this automatically, but validation fixtures in `conftest.py` must also use `sep=';'` and `dayfirst=True`

### Encoding Issues
Some CSVs may not be valid UTF-8. The dataset cleaner falls back to Latin-1 encoding automatically. If you see `UnicodeDecodeError`, check the encoding fallback logic in `scripts/generate_powerbi_datasets.py`.

### DeprecationWarnings
`datetime.utcnow()` warnings appear in `parse_dashboard_docx.py` and `run_validation.py`. These are cosmetic and don't affect functionality. Future fix: replace with `datetime.now(datetime.UTC)`.

## Devin Secrets Needed
No secrets are required for testing this pipeline. All data is local CSV files included in the repository.
