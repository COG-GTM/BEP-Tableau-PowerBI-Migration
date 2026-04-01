# Redundancy Analysis Report

## Cross-Dashboard DAX Pattern Redundancy

This report documents duplicated DAX measure patterns found across the 4 independently
converted Tableau dashboards: **Sales**, **HR**, **CISO Cybersecurity**, and
**IT Project Management**.

---

## Summary Table

| # | Pattern Family | Total Measures | Sales | HR | CISO | IT PM |
|---|---------------|:-:|:-:|:-:|:-:|:-:|
| 1 | STATUS_COUNT | 13 | -- | 2 | 7 | 4 |
| 2 | YOY_PCT_DIFF | 6 | 6 | -- | -- | -- |
| 3 | FILTERED_RATIO | 7 | 3 | 1 | 1 | 3 |
| 4 | RANK | 3 | 2 | -- | 1 | -- |
| 5 | WINDOW_FLAG | 4 | 3 | 1 | -- | -- |
| 6 | AVG_TIME_BETWEEN_DATES | 4 | -- | 1 | 1 | 2 |
| 7 | RUNNING_AGGREGATE | 3 | 1 | -- | 1 | 1 |
| 8 | LOD_FIXED | 7 | 6 | -- | 1 | -- |
| 9 | SHARED_DATE_TABLE | 3 tables | Date (2020-2023) | DateTable (2000-2030) | -- | Calendar (2025-2026) |
| | **Totals** | **47+ measures** | **21** | **5** | **11** | **10** |

### Before / After

| Metric | Before | After |
|--------|--------|-------|
| Redundant measure implementations | 47+ across 4 dashboards | 9 shared patterns + dashboard-specific instantiations |
| `_float_close()` test helper definitions | 4 (one per test file) | 1 (shared in `conftest.py`) |
| `TODAY` timestamp definitions | 3 (HR, CISO, IT PM test files) | 1 (shared in `conftest.py`) |
| Date dimension tables | 3 separate tables with varying ranges | 1 unified `SharedDate` (2000-2030) |
| Cross-dashboard validation tests | 0 | 5 (in `test_shared_patterns.py`) |

---

## Pattern 1: STATUS_COUNT_PATTERN

**DAX Shape:** `CALCULATE(COUNTROWS/DISTINCTCOUNT(table), table[column] = "value")`

**Tableau Source:** `IF [Status] = 'X' THEN 1 ELSE 0 END` or `COUNTD(IF [Status] = 'X' THEN [Key] END)`

### Measures (13 total)

| Dashboard | Measure | Filter Column(s) | Filter Value(s) |
|-----------|---------|-------------------|------------------|
| CISO | Critical Open Count | Severity, Remediation_Status | "Critical", "Open" |
| CISO | High Open Count | Severity, Remediation_Status | "High", "Open" |
| CISO | Medium Open Count | Severity, Remediation_Status | "Medium", "Open" |
| CISO | Low Open Count | Severity, Remediation_Status | "Low", "Open" |
| CISO | Total Open Vulnerabilities | Remediation_Status | "Open" |
| CISO | In Progress Count | Remediation_Status | "In Progress" |
| CISO | Accepted Risk Count | Remediation_Status | "Accepted" |
| IT PM | Issues To Do | Status | "To Do" |
| IT PM | Issues In Progress | Status | "In Progress" |
| IT PM | Issues In Review | Status | "In Review" |
| IT PM | Issues Done | Status | "Done" |
| HR | Total Terminated | Termdate | NOT ISBLANK |
| HR | Total Active | Termdate | ISBLANK |

---

## Pattern 2: YOY_PCT_DIFF_PATTERN

**DAX Shape:** `DIVIDE([CY Measure] - [PY Measure], [PY Measure], 0)`

**Tableau Source:** `(SUM([CY X]) - SUM([PY X])) / SUM([PY X])`

### Measures (6 total -- all in Sales)

| Measure | CY Measure | PY Measure |
|---------|-----------|-----------|
| % Diff Sales | CY Sales | PY Sales |
| % Diff Profit | CY Profit | PY Profit |
| % Diff Quantity | CY Quantity | PY Quantity |
| % Diff Customers | CY Customers | PY Customers |
| % Diff Sales per Customer | CY Sales per Customer | PY Sales per Customer |
| % Diff Profit Margin | CY Profit Margin | PY Profit Margin |

---

## Pattern 3: FILTERED_RATIO_PATTERN

**DAX Shape:** `DIVIDE(CALCULATE(agg, filter), agg_total, 0)`

**Tableau Source:** `SUM(IF cond THEN [X] END) / SUM([X])` or `[Measure] / TOTAL([Measure])`

### Measures (7 total)

| Dashboard | Measure | Numerator | Denominator |
|-----------|---------|-----------|-------------|
| Sales | % of Total CY Sales | CY Sales | CALCULATE(CY Sales, ALL(Orders)) |
| Sales | % of Total CY Profit | CY Profit | CALCULATE(CY Profit, ALL(Orders)) |
| Sales | CY Profit Margin | CY Profit | CY Sales |
| HR | % Total Hired | Total Hired | CALCULATE(Total Hired, ALL(HR)) |
| CISO | Remediation Rate | DISTINCTCOUNT(CVE_ID) where Remediated | DISTINCTCOUNT(CVE_ID) |
| IT PM | Completion Rate | Story Points Completed | Story Points Planned |
| IT PM | Bug Escape Rate | DISTINCTCOUNT where Bug | DISTINCTCOUNT total |
| IT PM | Sprint Completion % | DISTINCTCOUNT where Done | DISTINCTCOUNT total |

---

## Pattern 4: RANK_PATTERN

**DAX Shape:** `RANKX(ALL/ALLSELECTED(dim), measure, , DESC, Dense)`

**Tableau Source:** `RANK(SUM([Measure]))`

### Measures (3 total)

| Dashboard | Measure | Dimension | Ranked Measure |
|-----------|---------|-----------|----------------|
| Sales | Sales Rank | Orders[Sub-Category] | CY Sales |
| Sales | Customer Sales Rank | Customers[Customer ID] | CY Sales |
| CISO | Asset Vulnerability Rank | fact_vulnerabilities[Asset_Hostname] | DISTINCTCOUNT(CVE_ID) |

---

## Pattern 5: WINDOW_FLAG_PATTERN

**DAX Shape:** `IF(measure = MAXX(ALLSELECTED(dim), measure), "Max", IF(measure = MINX(...), "Min", BLANK()))`

**Tableau Source:** `IF SUM([X]) = WINDOW_MAX(SUM([X])) THEN 'Max' ...`

### Measures (4 total)

| Dashboard | Measure | Dimension | Flagged Measure |
|-----------|---------|-----------|-----------------|
| Sales | Max Sales Flag | Orders[Sub-Category] | CY Sales |
| Sales | Max Profit Flag | Orders[Sub-Category] | CY Profit |
| Sales | Max Quantity Flag | Orders[Sub-Category] | CY Quantity |
| HR | Highlight Max | HR[Department] | Total Hired |

---

## Pattern 6: AVG_TIME_BETWEEN_DATES_PATTERN

**DAX Shape:** `AVERAGEX(FILTER(table, condition), DATEDIFF(start, end, DAY))`

**Tableau Source:** `AVG(IF cond THEN DATEDIFF('day', [Start], [End]) END)`

### Measures (4 total)

| Dashboard | Measure | Start Date | End Date | Filter |
|-----------|---------|-----------|----------|--------|
| CISO | MTTR (Days) | First_Seen | Remediated_Date | Remediation_Status = "Remediated" |
| IT PM | Avg Cycle Time (Days) | Created_Date | Resolved_Date | Status = "Done" AND not blank |
| IT PM | Avg Lead Time (Days) | Created_Date | Resolved_Date or TODAY() | All issues |
| HR | Length of Hire | Hiredate | Termdate or TODAY() | Calculated column |

---

## Pattern 7: RUNNING_AGGREGATE_PATTERN

**DAX Shape:** `AVERAGEX/SUMX(FILTER(ALL(date_dim), date <= CurrentDate), CALCULATE(agg))`

**Tableau Source:** `RUNNING_SUM(SUM([X]))` or `RUNNING_AVG(AVG([X]))` or `WINDOW_AVG(..., -N, 0)`

### Measures (3 total)

| Dashboard | Measure | Aggregation | Window |
|-----------|---------|-------------|--------|
| Sales | Running Total Sales | SUM (cumulative) | All dates <= current |
| CISO | CVSS Running Average | AVG (cumulative) | All dates <= current |
| IT PM | Velocity 3-Sprint Moving Avg | AVG (3-period window) | Sprint - 2 to current |

---

## Pattern 8: LOD_FIXED_PATTERN

**DAX Shape:** `CALCULATE(agg, ALLEXCEPT(table, table[dimension]))`

**Tableau Source:** `{ FIXED [Dimension]: AGG([Measure]) }`

### Measures (7 total)

| Dashboard | Measure | Fixed Dimension | Aggregation |
|-----------|---------|-----------------|-------------|
| Sales | Nr of Orders per Customer | Customer ID | DISTINCTCOUNT(Order ID) |
| Sales | Sales by Category (FIXED) | Category | SUM(Sales) |
| Sales | Sales Excl SubCategory | ALL(Sub-Category) | SUM(Sales) |
| Sales | Customer First Order | Customer ID | MIN(Order Date) |
| Sales | Customer Last Order | Customer ID | MAX(Order Date) |
| Sales | Total Sales per Customer (FIXED) | Customer ID | SUM(Sales) |
| Sales | Total Profit per Customer (FIXED) | Customer ID | SUM(Profit) |
| Sales | CY Sales by Segment | Segment | CY Sales |
| Sales | CY Customer Total Sales | Customer ID + Year | SUM(Sales) |
| CISO | Risk Score by Business Unit | Business_Unit | Weighted CVSS Sum |

---

## Pattern 9: SHARED_DATE_TABLE

Three dashboards independently define date dimension tables:

| Dashboard | Table Name | Range | Key Columns |
|-----------|-----------|-------|-------------|
| Sales | Date | 2020-01-01 to 2023-12-31 | Date, Year, Month, Month Name, Quarter, Day of Week, Week Number |
| HR | DateTable | 2000-01-01 to 2030-12-31 | Date, Year, Month, MonthNumber, Quarter, QuarterNumber, YearMonth, DayOfWeek, DayOfWeekNumber, IsWeekend |
| IT PM | Calendar | 2025-01-01 to 2026-12-31 | Date, Year, MonthNumber, MonthName, Quarter, WeekNumber, DayName, IsWeekday |

**Unified SharedDate** covers DATE(2000,1,1) to DATE(2030,12,31) with the union of
all columns. See `shared/model_shared_date.tmdl`.

---

## Duplicated Test Helper: _float_close()

The function `_float_close(a, b, tol=0.001)` was defined identically in all 4 test files.
It has been extracted to `validation/conftest.py` as a shared module-level function.
The `TODAY = pd.Timestamp.now().normalize()` constant was also centralized there.

---

## Shared Artifacts

| File | Description |
|------|-------------|
| `shared/redundancy_report.md` | This report |
| `shared/dax_common_library.dax` | Parameterized DAX templates for all 9 patterns |
| `shared/model_shared_date.tmdl` | Unified date dimension (2000-2030) |
| `validation/conftest.py` | Shared `_float_close()` + `TODAY` |
| `validation/test_shared_patterns.py` | Cross-dashboard pattern validation tests |
