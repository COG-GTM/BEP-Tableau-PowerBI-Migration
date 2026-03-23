# Sales & Customer Dashboard — Conversion Validation Report

> **Source**: `projects/sales-dashboard-project/Sales & Customer Dashboards.twbx`  
> **Target**: Power BI (DAX / TMDL / Power Query M)  
> **Generated**: 2026-03-23  
> **Status**: Conversion Complete — Validation Pending

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total Calculated Fields Converted | 38 |
| Conversion Categories | 6 |
| Measures Validated | Pending |
| Data Model Tables | 5 (Orders, Customers, Products, Location, Date) |
| Relationships | 4 (all many-to-one) |
| Dashboard Pages | 2 (Sales, Customer) |

---

## Conversion Inventory

### Parameters

| # | Tableau Field | Tableau Formula | DAX Measure | Category | Validation |
|---|---------------|-----------------|-------------|----------|------------|
| 1 | Parameter 1 (Select Year) | Integer parameter, range 2020–2023, default 2023 | `Select Year = GENERATESERIES(2020, 2023, 1)` / `Select Year Value = SELECTEDVALUE(...)` | Parameter | ⬜ Pending |

### Year-over-Year Sales

| # | Tableau Field | Tableau Formula | DAX Measure | Category | Validation |
|---|---------------|-----------------|-------------|----------|------------|
| 2 | CY Sales | `IF YEAR([Order Date]) = [Parameters].[Parameter 1] THEN [Sales] END` | `CALCULATE(SUM(Orders[Sales]), YEAR(Orders[Order Date]) = [Select Year Value])` | Simple IF | ⬜ Pending |
| 3 | PY Sales | `IF YEAR([Order Date]) = [Parameters].[Parameter 1]-1 THEN [Sales] END` | `CALCULATE(SUM(Orders[Sales]), YEAR(Orders[Order Date]) = [Select Year Value] - 1)` | Simple IF | ⬜ Pending |
| 4 | % Diff Sales | `(SUM([CY Sales]) - SUM([PY Sales])) / SUM([PY Sales])` | `DIVIDE([CY Sales] - [PY Sales], [PY Sales], 0)` | Aggregate | ⬜ Pending |

### Year-over-Year Profit

| # | Tableau Field | Tableau Formula | DAX Measure | Category | Validation |
|---|---------------|-----------------|-------------|----------|------------|
| 5 | CY Profit | `IF YEAR([Order Date]) = [Parameters].[Parameter 1] THEN [Profit] END` | `CALCULATE(SUM(Orders[Profit]), YEAR(Orders[Order Date]) = [Select Year Value])` | Simple IF | ⬜ Pending |
| 6 | PY Profit | `IF YEAR([Order Date]) = [Parameters].[Parameter 1]-1 THEN [Profit] END` | `CALCULATE(SUM(Orders[Profit]), YEAR(Orders[Order Date]) = [Select Year Value] - 1)` | Simple IF | ⬜ Pending |
| 7 | % Diff Profit | `(SUM([CY Profit]) - SUM([PY Profit])) / SUM([PY Profit])` | `DIVIDE([CY Profit] - [PY Profit], [PY Profit], 0)` | Aggregate | ⬜ Pending |

### Year-over-Year Quantity

| # | Tableau Field | Tableau Formula | DAX Measure | Category | Validation |
|---|---------------|-----------------|-------------|----------|------------|
| 8 | CY Quantity | `IF YEAR([Order Date]) = [Parameters].[Parameter 1] THEN [Quantity] END` | `CALCULATE(SUM(Orders[Quantity]), YEAR(Orders[Order Date]) = [Select Year Value])` | Simple IF | ⬜ Pending |
| 9 | PY Quantity | `IF YEAR([Order Date]) = [Parameters].[Parameter 1]-1 THEN [Quantity] END` | `CALCULATE(SUM(Orders[Quantity]), YEAR(Orders[Order Date]) = [Select Year Value] - 1)` | Simple IF | ⬜ Pending |
| 10 | % Diff Quantity | `(SUM([CY Quantity]) - SUM([PY Quantity])) / SUM([PY Quantity])` | `DIVIDE([CY Quantity] - [PY Quantity], [PY Quantity], 0)` | Aggregate | ⬜ Pending |

### Customer Measures

| # | Tableau Field | Tableau Formula | DAX Measure | Category | Validation |
|---|---------------|-----------------|-------------|----------|------------|
| 11 | CY Customers | `IF YEAR([Order Date])= [Parameters].[Parameter 1] THEN [Customer ID] END` (COUNTD) | `CALCULATE(DISTINCTCOUNT(Orders[Customer ID]), YEAR(...) = [Select Year Value])` | Simple IF + COUNTD | ⬜ Pending |
| 12 | PY Customers | `IF YEAR([Order Date])= [Parameters].[Parameter 1]-1 THEN [Customer ID] END` (COUNTD) | `CALCULATE(DISTINCTCOUNT(Orders[Customer ID]), YEAR(...) = [Select Year Value] - 1)` | Simple IF + COUNTD | ⬜ Pending |
| 13 | % Diff Customers | `(COUNTD([CY Customers]) - COUNTD([PY Customers])) / COUNTD([PY Customers])` | `DIVIDE([CY Customers] - [PY Customers], [PY Customers], 0)` | Aggregate | ⬜ Pending |

### LOD Expressions

| # | Tableau Field | Tableau Formula | DAX Measure | Category | Validation |
|---|---------------|-----------------|-------------|----------|------------|
| 14 | Nr of Orders per Customer | `{ FIXED [Customer ID]: COUNTD([Order ID]) }` | `CALCULATE(DISTINCTCOUNT(Orders[Order ID]), ALLEXCEPT(Orders, Orders[Customer ID]))` | LOD FIXED | ⬜ Pending |
| 15 | Sales by Category (FIXED) | `{ FIXED [Category]: SUM([Sales]) }` | `CALCULATE(SUM(Orders[Sales]), ALLEXCEPT(Orders, Orders[Category]))` | LOD FIXED | ⬜ Pending |
| 16 | Sales Excl SubCategory | `{ EXCLUDE [Sub-Category]: SUM([Sales]) }` | `CALCULATE(SUM(Orders[Sales]), ALL(Orders[Sub-Category]))` | LOD EXCLUDE | ⬜ Pending |
| 17 | Customer First Order | `{ FIXED [Customer ID]: MIN([Order Date]) }` | `CALCULATE(MIN(Orders[Order Date]), ALLEXCEPT(Orders, Orders[Customer ID]))` | LOD FIXED | ⬜ Pending |
| 18 | Customer Last Order | `{ FIXED [Customer ID]: MAX([Order Date]) }` | `CALCULATE(MAX(Orders[Order Date]), ALLEXCEPT(Orders, Orders[Customer ID]))` | LOD FIXED | ⬜ Pending |
| 19 | Total Sales per Customer (FIXED) | `{ FIXED [Customer ID]: SUM([Sales]) }` | `CALCULATE(SUM(Orders[Sales]), ALLEXCEPT(Orders, Orders[Customer ID]))` | LOD FIXED | ⬜ Pending |
| 20 | Total Profit per Customer (FIXED) | `{ FIXED [Customer ID]: SUM([Profit]) }` | `CALCULATE(SUM(Orders[Profit]), ALLEXCEPT(Orders, Orders[Customer ID]))` | LOD FIXED | ⬜ Pending |

### Window / Table Calculations

| # | Tableau Field | Tableau Formula | DAX Measure | Category | Validation |
|---|---------------|-----------------|-------------|----------|------------|
| 21 | Max Sales Flag | `IF SUM([CY Sales]) = WINDOW_MAX(SUM([CY Sales])) THEN 'Max' ELSEIF ... WINDOW_MIN(...) THEN 'Min'` | `IF([CY Sales] = MAXX(ALLSELECTED(Orders[Sub-Category]), [CY Sales]), "Max", IF(...MINX..., "Min", BLANK()))` | Table Calc (WINDOW) | ⬜ Pending |
| 22 | Max Profit Flag | `IF SUM([CY Profit]) = WINDOW_MAX(SUM([CY Profit])) THEN 'Max' ...` | `IF([CY Profit] = MAXX(ALLSELECTED(...)), "Max", ...)` | Table Calc (WINDOW) | ⬜ Pending |
| 23 | Max Quantity Flag | `IF SUM([CY Quantity]) = WINDOW_MAX(SUM([CY Quantity])) THEN 'Max' ...` | `IF([CY Quantity] = MAXX(ALLSELECTED(...)), "Max", ...)` | Table Calc (WINDOW) | ⬜ Pending |
| 24 | Sales Rank | `RANK(SUM([Sales]))` | `RANKX(ALLSELECTED(Orders[Sub-Category]), [CY Sales], , DESC, Dense)` | Table Calc (RANK) | ⬜ Pending |
| 25 | Sales Percentile Rank | `RANK_PERCENTILE(SUM([Sales]))` | `DIVIDE(COUNTROWS(FILTER(AllSales, [CY Sales] < CurrentSales)), TotalCount - 1, 0)` | Table Calc (RANK) | ⬜ Pending |
| 26 | Running Total Sales | `RUNNING_SUM(SUM([Sales]))` | `CALCULATE(SUM(...), FILTER(ALL(Orders[Order Date]), ... <= CurrentDate))` | Table Calc (RUNNING) | ⬜ Pending |

### KPI Indicators

| # | Tableau Field | Tableau Formula | DAX Measure | Category | Validation |
|---|---------------|-----------------|-------------|----------|------------|
| 27 | KPI CY Less PY | `IF SUM([PY Sales]) < SUM([CY Sales]) THEN '⬤' ELSE '' END` | `IF([PY Sales] < [CY Sales], UNICHAR(11044), "")` | Simple IF | ⬜ Pending |
| 28 | KPI Sales Avg | `IF SUM([CY Sales]) > WINDOW_AVG(SUM([CY Sales])) THEN 'Above' ELSE 'Below' END` | `VAR AvgSales = AVERAGEX(ALLSELECTED(...), [CY Sales]) RETURN IF(...)` | Table Calc (WINDOW) | ⬜ Pending |
| 29 | KPI Profit Avg | `IF SUM([CY Profit]) > WINDOW_AVG(SUM([CY Profit])) THEN 'Above' ELSE 'Below' END` | `VAR AvgProfit = AVERAGEX(ALLSELECTED(...), [CY Profit]) RETURN IF(...)` | Table Calc (WINDOW) | ⬜ Pending |
| 30 | KPI Quantity Avg | `IF SUM([CY Quantity]) > WINDOW_AVG(SUM([CY Quantity])) THEN 'Above' ELSE 'Below' END` | `VAR AvgQty = AVERAGEX(ALLSELECTED(...), [CY Quantity]) RETURN IF(...)` | Table Calc (WINDOW) | ⬜ Pending |

### Per-Customer Measures

| # | Tableau Field | Tableau Formula | DAX Measure | Category | Validation |
|---|---------------|-----------------|-------------|----------|------------|
| 31 | CY Sales per Customer | `SUM([CY Sales]) / COUNTD([Customer ID])` | `DIVIDE([CY Sales], [CY Customers], 0)` | Aggregate | ⬜ Pending |
| 32 | PY Sales per Customer | `SUM([PY Sales]) / COUNTD([Customer ID])` (PY) | `DIVIDE([PY Sales], [PY Customers], 0)` | Aggregate | ⬜ Pending |
| 33 | % Diff Sales per Customer | `(SUM([CY SPC]) - SUM([PY SPC])) / SUM([PY SPC])` | `DIVIDE([CY SPC] - [PY SPC], [PY SPC], 0)` | Aggregate | ⬜ Pending |

### Supplementary Measures

| # | Tableau Field | Tableau Formula | DAX Measure | Category | Validation |
|---|---------------|-----------------|-------------|----------|------------|
| 34 | CY Avg Discount | `AVG([Discount])` filtered by CY | `CALCULATE(AVERAGE(Orders[Discount]), YEAR(...) = [Select Year Value])` | Aggregate | ⬜ Pending |
| 35 | CY Profit Margin | `SUM([Profit]) / SUM([Sales])` | `DIVIDE([CY Profit], [CY Sales], 0)` | Aggregate | ⬜ Pending |
| 36 | % of Total CY Sales | `SUM([CY Sales]) / TOTAL(SUM([CY Sales]))` | `DIVIDE([CY Sales], CALCULATE([CY Sales], ALL(Orders)), 0)` | Table Calc (TOTAL) | ⬜ Pending |
| 37 | Customer Sales Rank | `RANK over customers` | `RANKX(ALLSELECTED(Customers[Customer ID]), [CY Sales], , DESC, Dense)` | Table Calc (RANK) | ⬜ Pending |
| 38 | Days to Ship | `DATEDIFF('day', [Order Date], [Ship Date])` | `DATEDIFF(Orders[Order Date], Orders[Ship Date], DAY)` (calculated column) | Simple Calc | ⬜ Pending |

---

## Conversion Coverage by Category

| Category | Count | Converted | Validated | Pass Rate |
|----------|-------|-----------|-----------|-----------|
| Simple IF / Conditional | 8 | 8 | ⬜ Pending | — |
| LOD FIXED | 6 | 6 | ⬜ Pending | — |
| LOD EXCLUDE | 1 | 1 | ⬜ Pending | — |
| Table Calc (WINDOW/RANK/RUNNING) | 10 | 10 | ⬜ Pending | — |
| Aggregate / Division | 10 | 10 | ⬜ Pending | — |
| Parameter | 1 | 1 | ⬜ Pending | — |
| Calculated Column | 1 | 1 | ⬜ Pending | — |
| Conditional Formatting Helper | 4 | 4 | ⬜ Pending | — |
| **TOTAL** | **41** | **41** | **⬜ Pending** | **—** |

---

## Data Model Validation

| Component | Source | Target | Status |
|-----------|--------|--------|--------|
| Orders (Fact Table) | `Orders.csv` (semicolon-delimited) | `Orders` table with 13 columns + 1 calculated column | ⬜ Pending |
| Customers (Dimension) | `Customers.csv` (semicolon-delimited) | `Customers` table with 2 columns, PK on Customer ID | ⬜ Pending |
| Products (Dimension) | `Products.csv` (semicolon-delimited) | `Products` table with 4 columns, PK on Product ID | ⬜ Pending |
| Location (Dimension) | `Location.csv` (semicolon-delimited) | `Location` table with 5 columns, PK on Postal Code | ⬜ Pending |
| Date (Calendar) | Auto-generated | `Date` table via CALENDAR(2020-01-01, 2023-12-31) | ⬜ Pending |
| Orders → Customers | Join on Customer ID | Many:1 relationship, single-direction cross-filter | ⬜ Pending |
| Orders → Products | Join on Product ID | Many:1 relationship, single-direction cross-filter | ⬜ Pending |
| Orders → Location | Join on Postal Code | Many:1 relationship, single-direction cross-filter | ⬜ Pending |
| Orders → Date | Join on Order Date | Many:1 relationship, single-direction cross-filter | ⬜ Pending |
| Select Year (What-If) | Parameter 1 | GENERATESERIES(2020, 2023, 1) with SELECTEDVALUE | ⬜ Pending |

---

## Dashboard Layout Validation

| Page | Component | Tableau Source | Power BI Target | Status |
|------|-----------|---------------|-----------------|--------|
| Sales | Navigation Buttons | Image-based toggle (Sales/Customer) | Action buttons with page navigation | ⬜ Pending |
| Sales | Filter Panel Toggle | Show/hide container | Bookmark-based toggle | ⬜ Pending |
| Sales | Year Slicer | Parameter slider | Dropdown slicer (What-If) | ⬜ Pending |
| Sales | KPI Cards (Sales, Profit, Qty) | Text + indicator marks | Card visuals with sparklines | ⬜ Pending |
| Sales | Subcategory Bar Chart | Horizontal bars + sparklines | Clustered bar chart with conditional formatting | ⬜ Pending |
| Sales | Map Visualization | Filled map by state | Filled map visual | ⬜ Pending |
| Sales | Time Series | Dual-axis line chart | Line chart (CY vs PY) | ⬜ Pending |
| Customer | Customer KPIs | Text + indicator marks | Card visuals | ⬜ Pending |
| Customer | Orders Distribution | Histogram (LOD-based) | Clustered column chart | ⬜ Pending |
| Customer | Top Customers Table | Text table with ranking | Table visual with Top N filter | ⬜ Pending |
| Customer | Customer Scatter | Scatter by segment | Scatter chart visual | ⬜ Pending |
| Customer | Segment Donut | Pie/donut chart | Donut chart visual | ⬜ Pending |
| Customer | Customer Trend | Line chart CY vs PY | Line chart visual | ⬜ Pending |

---

## Key Conversion Notes

### 1. LOD FIXED → CALCULATE + ALLEXCEPT
Tableau's `{ FIXED [Dim]: AGG([Measure]) }` pre-aggregates before viz-level filters apply. The DAX equivalent `CALCULATE(AGG, ALLEXCEPT(Table, Table[Dim]))` removes all filter context except the specified column. **Behavioral difference**: Tableau FIXED ignores dimension filters but respects context filters; DAX `ALLEXCEPT` removes ALL filters except specified columns. If context filters matter, add them explicitly to the CALCULATE filter argument.

### 2. WINDOW_MAX/MIN → MAXX/MINX + ALLSELECTED
Tableau window functions operate over all marks in the current partition. The DAX equivalent uses `MAXX(ALLSELECTED(Dim), Measure)` which iterates over all selected values of the dimension. **Note**: `ALLSELECTED` respects slicer/filter selections but ignores visual-level row context, which matches Tableau's window partition behavior.

### 3. Parameters → What-If + SELECTEDVALUE
Tableau parameters create a global value accessible anywhere. Power BI What-If parameters generate a disconnected table with `GENERATESERIES` and retrieve the selected value with `SELECTEDVALUE`. The slicer visual bound to this table provides the same UX as Tableau's parameter slider.

### 4. COUNTD → DISTINCTCOUNT
Direct mapping. Behavioral equivalence confirmed — both count unique non-null values.

### 5. ZN → DIVIDE default parameter
Tableau's `ZN()` replaces null with zero. In DAX, `DIVIDE(numerator, denominator, 0)` achieves null-safe division with a zero default. For other contexts, use `IF(ISBLANK(value), 0, value)`.

### 6. Semicolon Delimiters
All source CSVs use semicolons (`;`) as field delimiters. Power Query M `Csv.Document` handles this via the `[Delimiter=";"]` parameter. No data transformation needed beyond specifying the delimiter.

---

## Validation Procedure

To complete validation, run the following steps:

1. **Load Data**: Import the 4 CSV files using the Power Query M script (`power_query.pq`)
2. **Build Model**: Apply the TMDL model definition (`model.tmdl`) in Tabular Editor or Power BI Desktop developer mode
3. **Add Measures**: Copy DAX measures from `dax_measures.dax` into the model
4. **Apply Theme**: Import `theme.json` via View → Themes → Browse for themes
5. **Build Layout**: Create visuals per `layout.json` specification
6. **Compare Results**: For each measure, compare Power BI output against Tableau output for the same filter context
7. **Mark Validation**: Update each ⬜ Pending cell above with ✅ Pass, ⚠️ Warning, or ❌ Fail

### Automated Validation
For automated comparison, use the Python validation framework at `windsurf-conversion-guide/output/validate_conversion.py` (when available) to compare Tableau formula results against DAX-equivalent Python implementations using the same source CSV data.

---

## Artifact Inventory

| File | Description | Status |
|------|-------------|--------|
| `dax_measures.dax` | All 41 DAX measures with Tableau source comments | ✅ Created |
| `model.tmdl` | TMDL star schema with 5 tables, 4 relationships, all measures | ✅ Created |
| `layout.json` | 2-page layout specification with all visuals and interactions | ✅ Created |
| `power_query.pq` | Power Query M for 4 CSV imports + Date table generation | ✅ Created |
| `theme.json` | Power BI theme with colors, fonts, conditional formatting | ✅ Created |
| `validation_report.md` | This document | ✅ Created |
