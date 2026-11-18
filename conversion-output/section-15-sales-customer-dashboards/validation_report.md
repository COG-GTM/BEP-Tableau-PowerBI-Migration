# Validation Report: Section 15 - Sales & Customer Dashboards

> **Source**: `course/tableau-files/Section 15 - Tableau Sales & Customer Dashboards.twbx`
> **Output**: `conversion-output/section-15-sales-customer-dashboards/`
> **Date**: 2026-04-01
> **Status**: VALIDATED

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields Converted | 33 |
| Parameters Converted | 1 |
| Dashboards Mapped | 2 |
| LOD Expressions | 2 |
| Window Calculations | 8 |
| Validation Status | PASS |

## Measure Validation Details

| # | Measure Name | Type | Tableau Pattern | DAX Conversion | Status |
|---|-------------|------|-----------------|----------------|--------|
| 1 | Select Year Value | Parameter | `[Parameters].[Parameter 1]` | `SELECTEDVALUE('Select Year'[Select Year], 2023)` | PASS |
| 2 | Current Year | Reference | `[Parameters].[Parameter 1]` | `[Select Year Value]` | PASS |
| 3 | Previous Year | Reference | `[Parameters].[Parameter 1]-1` | `[Select Year Value] - 1` | PASS |
| 4 | Order Date Year | Row-level | `YEAR([Order Date])` | `YEAR(Orders[Order Date])` | PASS |
| 5 | CY Sales | YoY | `IF YEAR([Order Date]) = [Param] THEN [Sales]` | `CALCULATE(SUM(...), YEAR(...) = [Select Year Value])` | PASS |
| 6 | CY Profit | YoY | `IF YEAR([Order Date]) = [Param] THEN [Profit]` | `CALCULATE(SUM(...), ...)` | PASS |
| 7 | CY Quantity | YoY | `IF YEAR([Order Date]) = [Param] THEN [Quantity]` | `CALCULATE(SUM(...), ...)` | PASS |
| 8 | CY Customers | YoY | `IF YEAR([Order Date]) = [Param] THEN [Customer ID]` | `CALCULATE(DISTINCTCOUNT(...), ...)` | PASS |
| 9 | CY Orders | YoY | `IF YEAR([Order Date]) = [Param] THEN [Order ID]` | `CALCULATE(DISTINCTCOUNT(...), ...)` | PASS |
| 10 | CY Sales per Customer | Derived | `SUM([CY Sales]) / COUNTD(...)` | `DIVIDE([CY Sales], [CY Customers], 0)` | PASS |
| 11 | PY Sales | YoY | `IF YEAR(...) = [Param]-1 THEN [Sales]` | `CALCULATE(SUM(...), ... = [Select Year Value] - 1)` | PASS |
| 12 | PY Profit | YoY | same pattern | same pattern | PASS |
| 13 | PY Quantity | YoY | same pattern | same pattern | PASS |
| 14 | PY Customers | YoY | same pattern | same pattern | PASS |
| 15 | PY Orders | YoY | same pattern | same pattern | PASS |
| 16 | PY Sales per Customer | Derived | `SUM([PY Sales]) / COUNTD(...)` | `DIVIDE([PY Sales], [PY Customers], 0)` | PASS |
| 17 | % Diff Sales | YoY % | `(SUM(CY) - SUM(PY)) / SUM(PY)` | `DIVIDE([CY Sales] - [PY Sales], [PY Sales], 0)` | PASS |
| 18 | % Diff Profit | YoY % | same pattern | same pattern | PASS |
| 19 | % Diff Quantity | YoY % | same pattern | same pattern | PASS |
| 20 | % Diff Customers | YoY % | same pattern | same pattern | PASS |
| 21 | % Diff Orders | YoY % | same pattern | same pattern | PASS |
| 22 | % Diff Sales per Customers | YoY % | same pattern | same pattern | PASS |
| 23 | Min/Max Sales | Window | `WINDOW_MAX/MIN(SUM([CY Sales]))` | `MAXX/MINX(ALLSELECTED(...), ...)` | PASS |
| 24 | Min/Max Customers | Window | same pattern | same pattern | PASS |
| 25 | Min/Max Quantity | Window | same pattern | same pattern | PASS |
| 26 | Min/Max Profit | Window | same pattern | same pattern | PASS |
| 27 | Min/Max Orders | Window | same pattern | same pattern | PASS |
| 28 | Min/Max Sales Per Customers | Window | same pattern | same pattern | PASS |
| 29 | KPI Sales Avg | Window | `WINDOW_AVG(SUM([CY Sales]))` | `AVERAGEX(ALLSELECTED(...), ...)` | PASS |
| 30 | KPI Profit Avg | Window | same pattern | same pattern | PASS |
| 31 | KPI CY Less PY | Comparison | `IF SUM(PY) < SUM(CY) THEN circle` | `IF([PY Sales] < [CY Sales], UNICHAR(11044), "")` | PASS |
| 32 | Grand Total CY Sales | LOD | `{SUM([CY Sales])}` | `CALCULATE([CY Sales], ALL(Orders))` | PASS |
| 33 | Nr of Orders per Customers | LOD | `{ FIXED [Customer ID]: COUNTD([Order ID]) }` | `CALCULATE(DISTINCTCOUNT(...), ALLEXCEPT(...))` | PASS |

## Parameter Conversion

| # | Parameter | Type | Default | DAX Conversion | Status |
|---|-----------|------|---------|----------------|--------|
| 1 | Select Year | integer | 2023 | GENERATESERIES(2020, 2023, 1) + SELECTEDVALUE | PASS |

## Conversion Notes

- Production-grade dashboard with 33 calculated fields (most complex course workbook)
- Year-over-Year pattern: CY/PY measures with parameter-driven year selection
- 6 Window calculations (Min/Max) converted to MAXX/MINX with ALLSELECTED
- 2 KPI Avg measures converted to AVERAGEX with ALLSELECTED
- 2 LOD expressions: FIXED -> ALLEXCEPT, grand total -> ALL
- UNICHAR(11044) used for bullet character in KPI CY Less PY
- Closely follows the sales-dashboard project conversion pattern
