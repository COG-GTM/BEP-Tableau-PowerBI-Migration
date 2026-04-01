# Testing the BEP Tableau-to-Power BI Migration Pipeline

## Overview
This skill covers end-to-end testing of the migration pipeline that converts Tableau dashboards to Power BI artifacts (DAX, TMDL, Power Query M, layouts, themes) and validates conversion accuracy.

## Prerequisites
- Python 3.12+ with packages: pandas, numpy, pytest, python-docx, tabulate, jinja2, streamlit, plotly
- Install via: `pip install -r requirements.txt && pip install -r validation/requirements.txt`
- For Streamlit dashboard: `pip install streamlit plotly`

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
4. Verify all 24 conversion artifacts exist (4 dashboards x 6 files)
5. Run pytest validation suite (255 tests)
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

### Validation Tests (255 total)
- Sales Dashboard: 8 tests (CY/PY sales, YoY %, LOD orders per customer, min/max, KPIs)
- HR Dashboard: 10 tests (hired/terminated/active counts, status, location, age, groups)
- CISO Dashboard: 9 tests (critical/high counts, MTTR, risk scores, remediation rate)
- IT PM Dashboard: 9 tests (velocity, burndown, cycle time, bug escape rate, scope creep)
- Cross-Dashboard Shared Patterns: 5 tests (STATUS_COUNT, DIVIDE rate, AVERAGEX+DATEDIFF, RANKX, WINDOW_MAX)
- Additional parametrized tests bring the total to 255

### Running Tests Independently
```bash
# All tests
pytest validation/ -v

# Single dashboard
pytest validation/test_sales_dashboard.py -v

# Cross-dashboard pattern tests only
pytest validation/test_shared_patterns.py -v

# Generate validation reports (markdown + JSON)
python3 validation/run_validation.py
```

## Testing the Streamlit Validation Dashboard

The Streamlit app (`streamlit_app.py`) provides an interactive UI to verify all conversion logic.

### Starting the App
```bash
streamlit run streamlit_app.py --server.headless true --server.port 8501
```
Then open `http://localhost:8501` in Chrome.

### Pages to Test (sidebar navigation)
1. **Overview**: Shows KPI cards (Total Measures, Passed, Dashboards, Datasets), a pass rate gauge, and per-dashboard breakdown chart. Expected: 36/36 measures at 100%.
2. **Sales & Customer**: KPI cards ($733K sales, etc.), charts (by sub-category, segment, monthly trend), and 8 validation results — all should show PASS.
3. **HR Dashboard**: Department/age group charts, hiring trend, and 10 validation results — all PASS.
4. **CISO Cybersecurity**: Severity chart, risk by BU, CVSS running avg, top 10 assets table, and 9 validation results — all PASS.
5. **IT Project Mgmt**: Sprint velocity with moving avg, issues by status/type, and 9 validation results — all PASS.
6. **DAX Code Viewer**: Dropdown to select dashboard, tabs for DAX Measures/Model/Power Query/Layout/Theme. Verify pattern annotations (`// Shared Pattern: X`) are visible in DAX Measures tab.

### Verifying Pattern Annotations in DAX Code Viewer
After the redundancy consolidation, each dashboard's DAX file has `// Shared Pattern: PATTERN_NAME` comments. To verify:
- Select each dashboard from the dropdown
- Check the DAX Measures tab for annotation comments
- Key patterns to look for: STATUS_COUNT_PATTERN, YOY_PCT_DIFF_PATTERN, LOD_FIXED_PATTERN, FILTERED_RATIO_PATTERN, WINDOW_FLAG_PATTERN, AVG_TIME_BETWEEN_DATES_PATTERN, RUNNING_AGGREGATE_PATTERN, RANK_PATTERN

### Shared Test Helpers
The `validation/conftest.py` file contains:
- `_float_close(a, b, tol=0.001)` — float comparison helper used by all test files
- `TODAY = pd.Timestamp.now().normalize()` — shared date constant
- Dataset fixtures: `sales_orders_df`, `hr_df`, `vuln_df`, `jira_df`

All 4 test files import `_float_close` and `TODAY` from conftest via `from conftest import _float_close, TODAY`.

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

### Streamlit App Tips
- The app might take a few seconds to load initially as it reads all CSV datasets
- If the app shows errors on load, verify that `pip install streamlit plotly` was run
- The DAX Code Viewer uses `st.code()` with `language="sql"` for syntax highlighting of DAX files
- Navigation is via sidebar radio buttons — click the page name to switch

## Devin Secrets Needed
No secrets are required for testing this pipeline. All data is local CSV files included in the repository.
