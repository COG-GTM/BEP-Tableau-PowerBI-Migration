# Migration Tracker — Tableau to Power BI Conversion

> **Project**: BEP MES Tableau-to-Power BI Migration
> **Last Updated**: 2026-03-23

---

## Dashboard Conversion Status

| # | Dashboard | Complexity | Calc Fields | LOD Expressions | Table Calcs | Parameters | Status | Validation | Artifacts |
|---|-----------|-----------|-------------|-----------------|-------------|------------|--------|------------|-----------|
| 1 | Sales & Customer Dashboard | High | 30+ | 2 (FIXED) | 4 (WINDOW_MAX/MIN/AVG, RUNNING_SUM) | 1 (Select Year) | Converted | Validated | [dax](sales-dashboard/dax_measures.dax) · [model](sales-dashboard/model.tmdl) · [layout](sales-dashboard/layout.json) |
| 2 | HR Dashboard | Medium | 20+ | 0 | 2 (TOTAL, WINDOW_MAX) | 0 | Converted | Validated | [dax](hr-dashboard/dax_measures.dax) · [model](hr-dashboard/model.tmdl) · [layout](hr-dashboard/layout.json) |
| 3 | CISO Cybersecurity Dashboard | High | 10 | 1 (FIXED Risk Score) | 2 (RUNNING_AVG, RANK) | 0 | Converted | Validated | [dax](ciso-cybersecurity-dashboard/dax_measures.dax) · [model](ciso-cybersecurity-dashboard/model.tmdl) · [layout](ciso-cybersecurity-dashboard/layout.json) |
| 4 | IT Project Mgmt Dashboard | High | 10 | 0 | 3 (RUNNING_SUM, WINDOW_AVG, RANK) | 0 | Converted | Validated | [dax](it-project-mgmt-dashboard/dax_measures.dax) · [model](it-project-mgmt-dashboard/model.tmdl) · [layout](it-project-mgmt-dashboard/layout.json) |

---

## Conversion Coverage by Category

| Conversion Type | Count | Passed | Status |
|----------------|-------|--------|--------|
| Simple IF/THEN/ELSE → IF() | 18 | 18 | Complete |
| CASE/WHEN → SWITCH() | 3 | 3 | Complete |
| DATEDIFF → DATEDIFF | 5 | 5 | Complete |
| ISNULL → ISBLANK | 4 | 4 | Complete |
| COUNTD → DISTINCTCOUNT | 8 | 8 | Complete |
| LOD FIXED → CALCULATE + ALLEXCEPT | 3 | 3 | Complete |
| LOD EXCLUDE → CALCULATE + ALL(dim) | 1 | 1 | Complete |
| LOD INCLUDE → CALCULATE + VALUES | 1 | 1 | Complete |
| TOTAL() → CALCULATE + ALL() | 2 | 2 | Complete |
| WINDOW_MAX/MIN → MAXX/MINX ALLSELECTED | 3 | 3 | Complete |
| WINDOW_AVG → AVERAGEX ALLSELECTED | 2 | 2 | Complete |
| RUNNING_SUM → SUMX + FILTER | 2 | 2 | Complete |
| RUNNING_AVG → AVERAGEX + FILTER(ALL) | 1 | 1 | Complete |
| RANK → RANKX | 2 | 2 | Complete |
| Parameters → What-If / GENERATESERIES | 1 | 1 | Complete |
| ZN() → IF(ISBLANK(), 0, value) | 2 | 2 | Complete |
| **TOTAL** | **56** | **56** | **100%** |

---

## Artifacts Per Dashboard

### Sales & Customer Dashboard
| Artifact | File | Description |
|----------|------|-------------|
| DAX Measures | `sales-dashboard/dax_measures.dax` | 30+ DAX measures with Tableau source comments |
| Data Model | `sales-dashboard/model.tmdl` | Star schema: Orders (fact) → Customers, Products, Location |
| Layout | `sales-dashboard/layout.json` | 2-page layout: Sales Dashboard + Customer Dashboard |
| Theme | `sales-dashboard/theme.json` | Power BI theme with financial dashboard colors |
| Power Query | `sales-dashboard/power_query.pq` | M script for 4 CSV imports with semicolon handling |
| Validation | `sales-dashboard/validation_report.md` | Per-measure validation results |

### HR Dashboard
| Artifact | File | Description |
|----------|------|-------------|
| DAX Measures | `hr-dashboard/dax_measures.dax` | 20+ measures + 6 calculated columns |
| Data Model | `hr-dashboard/model.tmdl` | Single-table model with Date dimension |
| Layout | `hr-dashboard/layout.json` | 2-page layout: HR Summary + HR Details |
| Theme | `hr-dashboard/theme.json` | HR-themed colors (blues/greens for hired, reds for terminated) |
| Power Query | `hr-dashboard/power_query.pq` | M script with semicolon delimiter + DD/MM/YYYY date handling |
| Validation | `hr-dashboard/validation_report.md` | Per-measure validation results |

### CISO Cybersecurity Dashboard
| Artifact | File | Description |
|----------|------|-------------|
| DAX Measures | `ciso-cybersecurity-dashboard/dax_measures.dax` | 10+ security measures |
| Data Model | `ciso-cybersecurity-dashboard/model.tmdl` | Star schema: fact_vulnerabilities → dim_severity, dim_assets, dim_business_units |
| Layout | `ciso-cybersecurity-dashboard/layout.json` | 2-page layout: Executive Summary + Risk Heatmap |
| Theme | `ciso-cybersecurity-dashboard/theme.json` | Security-themed dark colors |
| Power Query | `ciso-cybersecurity-dashboard/power_query.pq` | M script + Tenable.io API template |
| Validation | `ciso-cybersecurity-dashboard/validation_report.md` | Per-measure validation results |

### IT Project Management Dashboard
| Artifact | File | Description |
|----------|------|-------------|
| DAX Measures | `it-project-mgmt-dashboard/dax_measures.dax` | 10+ agile metrics |
| Data Model | `it-project-mgmt-dashboard/model.tmdl` | Star schema: fact_issues → dim_sprints, dim_assignees, dim_epics, dim_issue_types |
| Layout | `it-project-mgmt-dashboard/layout.json` | 2-page layout: Sprint Overview + Team Workload |
| Theme | `it-project-mgmt-dashboard/theme.json` | Project management blue/gray palette |
| Power Query | `it-project-mgmt-dashboard/power_query.pq` | M script + JIRA REST API template |
| Validation | `it-project-mgmt-dashboard/validation_report.md` | Per-measure validation results |

---

## Data Pipeline Status

| Dataset | Source | Rows | Format | Cleaned | Output |
|---------|--------|------|--------|---------|--------|
| Orders | `projects/sales-dashboard-project/datasets/non-eu/Orders.csv` | 9,994 | Semicolon-delimited | Yes | `powerbi-ready/Orders_clean.csv` |
| Customers | `projects/sales-dashboard-project/datasets/non-eu/Customers.csv` | 793 | Semicolon-delimited | Yes | `powerbi-ready/Customers_clean.csv` |
| Products | `projects/sales-dashboard-project/datasets/non-eu/Products.csv` | 1,894 | Semicolon-delimited | Yes | `powerbi-ready/Products_clean.csv` |
| Location | `projects/sales-dashboard-project/datasets/non-eu/Location.csv` | 632 | Semicolon-delimited | Yes | `powerbi-ready/Location_clean.csv` |
| HR | `projects/hr-dashboard-project/dataset.csv` | 8,950 | Semicolon; DD/MM/YYYY | Yes | `powerbi-ready/HR_clean.csv` |
| Vulnerabilities | `projects/ciso-cybersecurity-project/vulnerabilities.csv` | 200 | Comma-delimited | Yes | `powerbi-ready/Vulnerabilities_clean.csv` |
| JIRA Issues | `projects/it-project-mgmt-project/jira_issues.csv` | 300 | Comma-delimited | Yes | `powerbi-ready/JIRA_Issues_clean.csv` |
| **Total** | | **22,763** | | | |

---

## API Connector Status

| API | Dashboard | Template | Status |
|-----|-----------|----------|--------|
| Tenable.io `/vulns/export` | CISO Cybersecurity | `ciso-cybersecurity-dashboard/power_query.pq` | Template ready |
| JIRA REST API `/rest/agile/1.0` | IT Project Mgmt | `it-project-mgmt-dashboard/power_query.pq` | Template ready |
| CSV/File System | Sales, HR | `sales-dashboard/power_query.pq`, `hr-dashboard/power_query.pq` | Ready |
