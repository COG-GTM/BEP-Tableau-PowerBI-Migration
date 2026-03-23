# CISO Cybersecurity Dashboard — Conversion Validation Report

> **Source**: Tableau CISO Cybersecurity Vulnerability Dashboard
> **Target**: Power BI Desktop / Power BI Service (GCC High)
> **Conversion Guide**: `windsurf-conversion-guide/CISO_CYBERSECURITY_CONVERSION.md`
> **Dataset**: `projects/ciso-cybersecurity-project/vulnerabilities.csv` (~200 rows)
> **Report Date**: 2026-03-23

---

## Executive Summary

All 10 core Tableau calculated fields have been converted to DAX measures, plus 10 additional utility measures (20 total). The star schema data model has been implemented with 1 fact table and 3 dimension tables. Two dashboard pages (Executive Summary + Risk Heatmap) have been specified in the layout.

---

## 1. Measure Conversion Matrix

| # | Measure Name | Tableau Pattern | DAX Pattern | Status |
|---|-------------|----------------|-------------|--------|
| 1 | Critical Open Count | `IF [Severity]='Critical' AND [Status]='Open' THEN 1 ELSE 0 END` | `CALCULATE + COUNTROWS` with two filter predicates | Converted |
| 2 | High Open Count | `IF [Severity]='High' AND [Status]='Open' THEN 1 ELSE 0 END` | `CALCULATE + COUNTROWS` with two filter predicates | Converted |
| 3 | Total Vulnerabilities | `COUNTD([CVE_ID])` | `DISTINCTCOUNT(fact_vulnerabilities[CVE_ID])` | Converted |
| 4 | MTTR (Days) | `AVG(IF [Status]='Remediated' THEN DATEDIFF(...) END)` | `AVERAGEX + FILTER + DATEDIFF` | Converted |
| 5 | Risk Score by Business Unit | `{FIXED [Business_Unit]: SUM(IF...)}` (LOD) | `CALCULATE + SUMX + SWITCH + ALLEXCEPT` | Converted |
| 6 | Vuln Count by Severity | `COUNTD([CVE_ID])` on Severity dimension | `DISTINCTCOUNT` (filter context via visual) | Converted |
| 7 | Remediation Rate | `COUNTD(IF [Status]='Remediated'...)/COUNTD([CVE_ID])` | `DIVIDE + CALCULATE + DISTINCTCOUNT` | Converted |
| 8 | Aging Vulnerabilities (>30d) | `IF [Status]='Open' AND DATEDIFF(...)>30 THEN 1 ELSE 0 END` | `CALCULATE + COUNTROWS + FILTER + DATEDIFF + TODAY()` | Converted |
| 9 | CVSS Running Average | `RUNNING_AVG(AVG([CVSS_Score]))` | `VAR + AVERAGEX + FILTER(ALL(...))` | Converted |
| 10 | Asset Vulnerability Rank | `RANK(COUNTD([CVE_ID]))` with Top N=10 | `RANKX + ALL + DISTINCTCOUNT` | Converted |
| 11 | Medium Open Count | _(additional)_ | `CALCULATE + COUNTROWS` | Added |
| 12 | Low Open Count | _(additional)_ | `CALCULATE + COUNTROWS` | Added |
| 13 | Total Open Vulnerabilities | _(additional)_ | `CALCULATE + COUNTROWS` | Added |
| 14 | In Progress Count | _(additional)_ | `CALCULATE + COUNTROWS` | Added |
| 15 | Accepted Risk Count | _(additional)_ | `CALCULATE + COUNTROWS` | Added |
| 16 | Average CVSS Score | _(additional)_ | `AVERAGE` | Added |
| 17 | Critical High Open Count | _(additional)_ | `CALCULATE + COUNTROWS + IN` | Added |
| 18 | Days Since Last Scan | _(additional)_ | `DATEDIFF + MAX + TODAY` | Added |
| 19 | Remediation Rate % | _(additional)_ | `FORMAT([Remediation Rate], "0.0%")` | Added |
| 20 | SLA Breach Count | _(additional)_ | `CALCULATE + COUNTROWS + FILTER` | Added |

---

## 2. Data Model Validation

### Star Schema Structure

| Table | Type | Primary Key | Row Source | Columns |
|-------|------|-------------|-----------|---------|
| `fact_vulnerabilities` | Fact | `CVE_ID` | vulnerabilities.csv | 13 columns |
| `dim_severity` | Dimension | `Severity` | Hardcoded reference | 5 columns (Severity, CVSS_Range_Low, CVSS_Range_High, Color_Code, Sort_Order) |
| `dim_assets` | Dimension | `Asset_Hostname` | Derived from CSV | 6 columns (Asset_Hostname, Asset_OS, Asset_IP, Business_Unit, Asset_Type, Criticality) |
| `dim_business_units` | Dimension | `Business_Unit` | Hardcoded reference | 3 columns (Business_Unit, BU_Head, Risk_Tolerance) |

### Relationships

| From (Many) | To (One) | Join Column | Direction |
|-------------|----------|-------------|-----------|
| `fact_vulnerabilities.Severity` | `dim_severity.Severity` | Severity | Single |
| `fact_vulnerabilities.Asset_Hostname` | `dim_assets.Asset_Hostname` | Asset_Hostname | Single |
| `fact_vulnerabilities.Business_Unit` | `dim_business_units.Business_Unit` | Business_Unit | Single |

### Row-Level Security

- Role `Business Unit Viewer` defined with `[Business_Unit] = USERNAME()` filter on `dim_business_units`

---

## 3. LOD Expression Conversion Detail

### Tableau `{ FIXED [Business_Unit]: SUM(IF...THEN...END) }`

The Level of Detail (LOD) expression computes a risk score at the Business Unit grain, independent of visualization-level filters.

**DAX Equivalent:**
```dax
Risk Score by Business Unit =
CALCULATE(
    SUMX(
        fact_vulnerabilities,
        fact_vulnerabilities[CVSS_Score] *
        SWITCH(
            fact_vulnerabilities[Severity],
            "Critical", 4,
            "High", 3,
            "Medium", 2,
            1
        )
    ),
    ALLEXCEPT(fact_vulnerabilities, fact_vulnerabilities[Business_Unit])
)
```

**Conversion Notes:**
- `ALLEXCEPT` removes all filter context except Business_Unit, replicating the FIXED LOD behavior
- `SWITCH` replaces nested `IF/ELSEIF` for cleaner code
- Severity multipliers: Critical=4x, High=3x, Medium=2x, Low=1x

---

## 4. Table Calculation Conversion Detail

### Tableau `RUNNING_AVG(AVG([CVSS_Score]))`

**DAX Equivalent:**
```dax
CVSS Running Average =
VAR CurrentDate = MAX(fact_vulnerabilities[First_Seen])
RETURN
AVERAGEX(
    FILTER(
        ALL(fact_vulnerabilities[First_Seen]),
        fact_vulnerabilities[First_Seen] <= CurrentDate
    ),
    CALCULATE(AVERAGE(fact_vulnerabilities[CVSS_Score]))
)
```

**Conversion Notes:**
- Tableau's `RUNNING_AVG` operates across the visualization partition; DAX requires explicit date filtering
- `ALL(fact_vulnerabilities[First_Seen])` removes the date filter to enable the running window
- For Power BI 2023+, the newer `WINDOW` DAX function could provide cleaner syntax

---

## 5. Dashboard Layout Validation

### Page 1: Executive Summary

| Visual | Type | Measure(s) | Status |
|--------|------|-----------|--------|
| Date Range Slicer | Slicer (dateRange) | First_Seen | Specified |
| Business Unit Slicer | Slicer (dropdown) | Business_Unit | Specified |
| OS Slicer | Slicer (dropdown) | Asset_OS | Specified |
| Critical KPI Card | Card | Critical Open Count | Specified |
| High KPI Card | Card | High Open Count | Specified |
| Medium KPI Card | Card | Medium Open Count | Specified |
| Low KPI Card | Card | Low Open Count | Specified |
| Total Vulns KPI Card | Card | Total Vulnerabilities | Specified |
| Severity Distribution | Donut Chart | Vuln Count by Severity | Specified |
| Remediation Rate | Gauge | Remediation Rate + MTTR | Specified |
| MTTR Trend | Line Chart | MTTR (Days) over time | Specified |
| Top 10 Assets | Horizontal Bar | Total Vulnerabilities + Rank filter | Specified |
| Remediation Funnel | Funnel | Total/Open/InProgress/Accepted/Remediated | Specified |

### Page 2: Risk Heatmap

| Visual | Type | Measure(s) | Status |
|--------|------|-----------|--------|
| Risk Heatmap Matrix | Matrix | Vuln Count by Severity + Risk Score, conditional formatting | Specified |
| Aging Vulnerabilities | Scatter Plot | Days Open (x) vs CVSS Score (y), severity legend | Specified |

---

## 6. Power Query Validation

| Query | Purpose | Source | Status |
|-------|---------|--------|--------|
| fact_vulnerabilities (CSV) | Local CSV import with type conversions | vulnerabilities.csv | Implemented |
| dim_severity | Static severity reference table | Hardcoded M table | Implemented |
| dim_assets | Asset dimension derived from CSV | vulnerabilities.csv (deduplicated) | Implemented |
| dim_business_units | BU reference with metadata | Hardcoded M table | Implemented |
| Tenable.io API Template | Production API connection | cloud.tenable.com/vulns/export | Template provided |

### Data Type Conversions

| Column | Source Type | Power BI Type |
|--------|-----------|--------------|
| CVE_ID | text | text |
| Severity | text | text |
| Asset_Hostname | text | text |
| Plugin_ID | text | Int64.Type |
| Plugin_Name | text | text |
| First_Seen | text | type date |
| Last_Seen | text | type date |
| Remediated_Date | text | type date (nullable) |
| Remediation_Status | text | text |
| CVSS_Score | text | type number |
| Asset_OS | text | text |
| Asset_IP | text | text |
| Business_Unit | text | text |

---

## 7. Theme Validation

| Element | Value | Purpose |
|---------|-------|---------|
| Background | `#1A1A2E` (dark navy) | Cybersecurity dark mode |
| Foreground | `#ECEFF1` (light gray) | High contrast text |
| Critical color | `#D32F2F` (red) | Critical severity |
| High color | `#FF6D00` (orange) | High severity |
| Medium color | `#FFB300` (amber) | Medium severity |
| Low color | `#388E3C` (green) | Low severity |
| Info color | `#1976D2` (blue) | Informational |
| Accent | `#42A5F5` (light blue) | Interactive elements |
| Grid/border | `#37474F` (dark gray) | Subtle dividers |

---

## 8. Artifacts Inventory

| File | Description | NIST Control |
|------|-------------|--------------|
| `dax_measures.dax` | All 20 DAX measures with Tableau source comments | SA-11 |
| `model.tmdl` | Star schema TMDL with tables, relationships, measures, RLS | SA-11 |
| `layout.json` | 2-page dashboard layout specification | N/A |
| `power_query.pq` | Power Query M scripts (CSV + API template) | SI-12 |
| `theme.json` | Cybersecurity-themed Power BI JSON theme | N/A |
| `validation_report.md` | This validation document | SA-11(1) |

---

## 9. Validation Approach

### Recommended Automated Checks

1. **Row Count**: Verify Power BI imports all ~200 rows from `vulnerabilities.csv`
2. **KPI Validation**: Compare Critical/High/Medium/Low counts between Python baseline and DAX measures
3. **MTTR Calculation**: Compute MTTR independently in Python and compare (tolerance: +/-0.1 days)
4. **LOD Validation**: Verify Risk Score by BU matches Python `groupby` calculation
5. **Remediation Rate**: Cross-check percentage against manual count
6. **Top 10 Assets**: Verify ranking order matches Python `value_counts().head(10)`

### Python Validation Script

```python
import pandas as pd

df = pd.read_csv("vulnerabilities.csv")

# KPI validation
critical_open = len(df[(df["Severity"] == "Critical") & (df["Remediation_Status"] == "Open")])
high_open = len(df[(df["Severity"] == "High") & (df["Remediation_Status"] == "Open")])
medium_open = len(df[(df["Severity"] == "Medium") & (df["Remediation_Status"] == "Open")])
low_open = len(df[(df["Severity"] == "Low") & (df["Remediation_Status"] == "Open")])
total_vulns = df["CVE_ID"].nunique()

# MTTR validation
remediated = df[df["Remediation_Status"] == "Remediated"].copy()
remediated["First_Seen"] = pd.to_datetime(remediated["First_Seen"])
remediated["Remediated_Date"] = pd.to_datetime(remediated["Remediated_Date"])
mttr = (remediated["Remediated_Date"] - remediated["First_Seen"]).dt.days.mean()

# Risk Score by Business Unit
severity_weights = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}
df["Weighted_CVSS"] = df.apply(
    lambda r: r["CVSS_Score"] * severity_weights.get(r["Severity"], 1), axis=1
)
risk_by_bu = df.groupby("Business_Unit")["Weighted_CVSS"].sum()

# Remediation Rate
remediation_rate = df[df["Remediation_Status"] == "Remediated"]["CVE_ID"].nunique() / total_vulns

print(f"Critical Open: {critical_open}")
print(f"High Open: {high_open}")
print(f"Medium Open: {medium_open}")
print(f"Low Open: {low_open}")
print(f"Total Vulnerabilities: {total_vulns}")
print(f"MTTR: {mttr:.1f} days")
print(f"Remediation Rate: {remediation_rate:.1%}")
print(f"\nRisk Score by BU:\n{risk_by_bu}")
```

---

## 10. Known Limitations & Notes

1. **Tenable.io API Template**: The Power Query template for Tenable.io is provided as a reference; actual API keys must be configured via Power BI Parameters (never hardcoded)
2. **FedRAMP Compliance**: For GCC High deployments, update the Tenable base URL to the FedRAMP endpoint
3. **Running Average (Measure 9)**: The `WINDOW` DAX function (Power BI 2023+) may provide cleaner syntax for running calculations
4. **Row-Level Security**: The `Business Unit Viewer` role uses `USERNAME()` which maps to the user's UPN in Power BI Service
5. **SLA Thresholds**: Default SLA thresholds are Critical=7d, High=30d, Medium=90d; adjust per organizational policy
6. **Accepted Risk Status**: Some vulnerabilities have `Accepted` status (risk accepted) which is tracked separately from Open/Remediated
