# Usage Guide — Tableau to Power BI Migration Framework

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the full pipeline
bash scripts/run_full_pipeline.sh

# 3. (Optional) Parse a specific .docx file listing dashboards
bash scripts/run_full_pipeline.sh path/to/dashboards.docx
```

## Repository Structure

```
BEP-Tableau-PowerBI-Migration/
├── scripts/                          # Automation scripts
│   ├── parse_dashboard_docx.py       # Parse .docx → manifest + inventory
│   ├── generate_powerbi_datasets.py  # Clean source CSVs for Power BI import
│   └── run_full_pipeline.sh          # End-to-end pipeline runner
│
├── conversion-output/                # All conversion artifacts
│   ├── dashboard_manifest.json       # Structured metadata for all dashboards
│   ├── dashboard_inventory.md        # Human-readable dashboard list
│   ├── migration_tracker.md          # Per-dashboard conversion status
│   ├── conversion_summary.md         # Executive summary with metrics
│   │
│   ├── sales-dashboard/             # Sales & Customer Dashboard
│   │   ├── dax_measures.dax          # DAX measures (with Tableau source comments)
│   │   ├── model.tmdl                # Star schema definition (TMDL)
│   │   ├── layout.json               # Power BI page layout specification
│   │   ├── theme.json                # Power BI theme (colors, fonts)
│   │   ├── power_query.pq            # Power Query M import script
│   │   └── validation_report.md      # Per-measure validation results
│   │
│   ├── hr-dashboard/                # HR Dashboard (same structure)
│   ├── ciso-cybersecurity-dashboard/ # CISO Dashboard (same structure)
│   ├── it-project-mgmt-dashboard/   # IT PM Dashboard (same structure)
│   │
│   └── powerbi-ready/               # Cleaned CSVs for Power BI import
│       ├── Orders_clean.csv
│       ├── Customers_clean.csv
│       ├── Products_clean.csv
│       ├── Location_clean.csv
│       ├── HR_clean.csv
│       ├── Vulnerabilities_clean.csv
│       └── JIRA_Issues_clean.csv
│
├── validation/                       # Automated validation framework
│   ├── conftest.py                   # Shared pytest fixtures (dataset loading)
│   ├── validate_conversion.py        # Standalone validation engine
│   ├── run_validation.py             # CLI runner with report generation
│   ├── test_sales_dashboard.py       # Sales dashboard measure tests
│   ├── test_hr_dashboard.py          # HR dashboard measure tests
│   ├── test_ciso_dashboard.py        # CISO dashboard measure tests
│   ├── test_it_project_mgmt.py       # IT PM dashboard measure tests
│   ├── requirements.txt              # Validation dependencies
│   └── reports/                      # Generated validation reports
│       ├── conversion_validation_report.md
│       └── validation_summary.json
│
├── projects/                         # Source Tableau data (existing)
│   ├── sales-dashboard-project/
│   ├── hr-dashboard-project/
│   ├── ciso-cybersecurity-project/
│   └── it-project-mgmt-project/
│
├── windsurf-conversion-guide/        # Conversion reference documentation
│   ├── CONVERSION_OUTLINE.md
│   ├── CISO_CYBERSECURITY_CONVERSION.md
│   └── IT_PROJECT_MGMT_CONVERSION.md
│
├── requirements.txt                  # Python dependencies
└── USAGE.md                          # This file
```

## Individual Scripts

### 1. Parse Dashboard .docx

Extracts dashboard definitions from a Word document:

```bash
python scripts/parse_dashboard_docx.py path/to/dashboards.docx --output-dir conversion-output
```

**Outputs**:
- `conversion-output/dashboard_manifest.json` — structured metadata
- `conversion-output/dashboard_inventory.md` — human-readable summary

If no .docx is provided, uses the 4 built-in dashboard definitions.

### 2. Generate Cleaned Datasets

Converts source CSVs to Power BI-ready format:

```bash
python scripts/generate_powerbi_datasets.py --output-dir conversion-output/powerbi-ready
```

**Handles**:
- Semicolon delimiters → comma-delimited
- DD/MM/YYYY dates → YYYY-MM-DD
- Encoding issues (UTF-8 with Latin-1 fallback)
- Column name standardization and whitespace trimming

### 3. Run Validation

```bash
# Run all tests
pytest validation/ -v

# Generate detailed report
python validation/run_validation.py

# Run specific dashboard tests
pytest validation/test_sales_dashboard.py -v
pytest validation/test_hr_dashboard.py -v
pytest validation/test_ciso_dashboard.py -v
pytest validation/test_it_project_mgmt.py -v
```

## How to Use the Power BI Artifacts

### DAX Measures (`.dax` files)

1. Open Power BI Desktop
2. Go to **Modeling** → **New Measure**
3. Copy each measure from the `.dax` file into the formula bar
4. Each measure includes the original Tableau formula as a comment for reference

### Data Models (`.tmdl` files)

Option A — **Manual setup**:
1. Import the cleaned CSVs from `conversion-output/powerbi-ready/`
2. Create relationships as defined in the `.tmdl` file
3. Add the DAX measures

Option B — **TMDL import** (Power BI Developer Mode):
1. Enable Developer Mode in Power BI Desktop (Preview features)
2. Use Tabular Editor to import the `.tmdl` definition
3. Deploy to Power BI Service

### Power Query M Scripts (`.pq` files)

1. In Power BI Desktop, go to **Home** → **Transform Data**
2. Click **Advanced Editor**
3. Paste the M script from the `.pq` file
4. Update file paths or API credentials as needed

### Themes (`.json` files)

1. In Power BI Desktop, go to **View** → **Themes** → **Browse for themes**
2. Select the `.json` theme file
3. The theme applies colors, fonts, and formatting to all visuals

### Layouts (`.json` files)

Use as a reference specification when building dashboard pages. Each layout defines:
- Page dimensions and names
- Visual positions (x, y, width, height)
- Visual types and data bindings
- Cross-filter settings

## Data Format Notes

| Dataset | Delimiter | Date Format | Encoding | Special Notes |
|---------|-----------|-------------|----------|---------------|
| Sales CSVs | Semicolon (;) | MM/DD/YYYY | Latin-1 | Some customer names contain special characters |
| HR CSV | Semicolon (;) | DD/MM/YYYY | UTF-8 | Termdate may be empty for active employees |
| Vulnerabilities CSV | Comma (,) | YYYY-MM-DD | UTF-8 | Remediated_Date may be empty for open vulns |
| JIRA Issues CSV | Comma (,) | YYYY-MM-DD | UTF-8 | Story_Points may be empty for Epics |

## Validation Report Interpretation

The validation framework generates a report with three result levels:

| Level | Meaning | Tolerance |
|-------|---------|-----------|
| **PASS** | Results match exactly or within tight tolerance | Integers: exact; Floats: ±0.001 |
| **WARN** | Results match within relaxed tolerance | Floats: ±0.01 |
| **FAIL** | Results differ — conversion error detected | Beyond tolerance |

A **PASS** rate of 100% indicates all Tableau formulas have been faithfully converted to DAX.
