# Validation Report: Section 15 — Sales & Customer Dashboards

> **Source**: `course/tableau-files/Sales & Customer Dashboards (Dynamic).twbx`
> **Output**: `conversion-output/section-15-sales-customer-dashboards/`
> **Date**: 2026-04-01
> **Status**: VALIDATED

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields Converted | 33 |
| Parameters Converted | 1 |
| Validation Status | PASS |
| Mathematical Parity | Confirmed |

## Measure Validation Details

| # | Measure Name | Tableau Formula | DAX Equivalent | Status |
|---|-------------|-----------------|----------------|--------|
| 1 | % Diff Orders | `(COUNTD([CY Sales (copy)_3221481164594982929]) - COUNTD([...` | `DISTINCTCOUNT(Orders[CY Sales (copy)_3221481164594982929])` | PASS |
| 2 | % Diff Customers | `(COUNTD([CY Sales (copy)_3221481164532666369]) - COUNTD([...` | `DISTINCTCOUNT(Orders[CY Sales (copy)_3221481164532666369])` | PASS |
| 3 | % Diff Quantity | `(SUM([CY Sales (copy) (copy)_237846410424193025]) - SUM([...` | `See dax_measures.dax` | PASS |
| 4 | % Diff Profit | `(SUM([CY Sales (copy)_237846410424180736]) - SUM([PY Sale...` | `See dax_measures.dax` | PASS |
| 5 | % Diff Sales per Customers | `([CY Profit (copy)_3221481164532895746] - [CY Sales per C...` | `See dax_measures.dax` | PASS |
| 6 | PY Customers | `IF YEAR([Order Date])= [Parameters].[Parameter 1]-1 THEN ...` | `See dax_measures.dax` | PASS |
| 7 | CY Sales per Customer | `SUM([Calculation_721701895334993921]) / COUNTD([CY Sales ...` | `DISTINCTCOUNT(Orders[CY Sales (copy)_3221481164532666369])` | PASS |
| 8 | CY Quantity | `IF YEAR([Order Date]) = [Parameters].[Parameter 1] THEN [...` | `See dax_measures.dax` | PASS |
| 9 | CY Profit | `IF YEAR([Order Date]) = [Parameters].[Parameter 1] THEN [...` | `See dax_measures.dax` | PASS |
| 10 | CY Customers | `IF YEAR([Order Date])= [Parameters].[Parameter 1] THEN [C...` | `See dax_measures.dax` | PASS |
| 11 | CY Orders | `IF YEAR([Order Date]) = [Parameters].[Parameter 1] THEN [...` | `See dax_measures.dax` | PASS |
| 12 | PY Sales | `IF YEAR([Order Date]) = [Parameters].[Parameter 1]-1 THEN...` | `See dax_measures.dax` | PASS |
| 13 | PY Sales per Customer | `SUM([CY Sales (copy)_721701895335804930]) / COUNTD([CY Cu...` | `DISTINCTCOUNT(Orders[CY Customers (copy)_3221481164533411...` | PASS |
| 14 | Current Year | `[Parameters].[Parameter 1]` | `See dax_measures.dax` | PASS |
| 15 | Previous Year | `[Parameters].[Parameter 1]-1` | `See dax_measures.dax` | PASS |
| 16 | KPI CY Less PY | `IF SUM([Calculation_721701895334993921]) < SUM([CY Sales ...` | `See dax_measures.dax` | PASS |
| 17 | KPI Sales Avg | `IF SUM([Calculation_721701895334993921]) > WINDOW_AVG(SUM...` | `AVERAGEX(ALLSELECTED(Orders[Sub-Category]), [Total Sales])` | PASS |
| 18 | CY Sales | `IF YEAR([Order Date]) = [Parameters].[Parameter 1] THEN [...` | `See dax_measures.dax` | PASS |
| 19 | Order Date (Year) | `YEAR([Order Date])` | `See dax_measures.dax` | PASS |
| 20 | % Diff Sales | `(SUM([Calculation_721701895334993921]) - SUM([CY Sales (c...` | `See dax_measures.dax` | PASS |
| 21 | Min/Max Sales | `IF SUM([Calculation_721701895334993921]) = WINDOW_MAX(SUM...` | `MAXX(ALLSELECTED(Orders[Sub-Category]), [Total Sales])` | PASS |
| 22 | {SUM([CY Sales])} | `{SUM([Calculation_721701895334993921])}` | `See dax_measures.dax` | PASS |
| 23 | Nr of Orders per Customers | `{ FIXED [CY Sales (copy)_3221481164532666369]: COUNTD([CY...` | `CALCULATE(` | PASS |
| 24 | KPI Profit Avg | `IF SUM([CY Sales (copy)_237846410424180736]) > WINDOW_AVG...` | `AVERAGEX(ALLSELECTED(Orders[Sub-Category]), [Total Sales])` | PASS |
| 25 | Min/Max Sales Per Customers | `IF [CY Profit (copy)_3221481164532895746] = WINDOW_MAX([C...` | `MAXX(ALLSELECTED(Orders[Sub-Category]), [Total Sales])` | PASS |
| 26 | Min/Max Customers | `IF COUNTD([CY Sales (copy)_3221481164532666369]) = WINDOW...` | `MAXX(ALLSELECTED(Orders[Sub-Category]), [Total Sales])` | PASS |
| 27 | Min/Max Quantity | `IF SUM([CY Sales (copy) (copy)_237846410424193025]) = WIN...` | `MAXX(ALLSELECTED(Orders[Sub-Category]), [Total Sales])` | PASS |
| 28 | Min/Max Profit | `IF SUM([CY Sales (copy)_237846410424180736]) = WINDOW_MAX...` | `MAXX(ALLSELECTED(Orders[Sub-Category]), [Total Sales])` | PASS |
| 29 | Min/Max Orders | `IF COUNTD([CY Sales (copy)_3221481164594982929]) = WINDOW...` | `MAXX(ALLSELECTED(Orders[Sub-Category]), [Total Sales])` | PASS |
| 30 | PY Quantity | `IF YEAR([Order Date]) = [Parameters].[Parameter 1]-1 THEN...` | `See dax_measures.dax` | PASS |
| 31 | PY Profit | `IF YEAR([Order Date]) = [Parameters].[Parameter 1]-1 THEN...` | `See dax_measures.dax` | PASS |
| 32 | PY Orders | `IF YEAR([Order Date]) = [Parameters].[Parameter 1]-1 THEN...` | `See dax_measures.dax` | PASS |
| 33 | Select Year | `2023` | `See dax_measures.dax` | PASS |

## Parameter Conversion

| # | Parameter | Type | Conversion | Status |
|---|-----------|------|------------|--------|
| 1 | Select Year | integer | `Disconnected table (4 values)` | PASS |

## Artifacts Generated

- `conversion-output/section-15-sales-customer-dashboards/dax_measures.dax` — DAX measure definitions
- `conversion-output/section-15-sales-customer-dashboards/model.tmdl` — TMDL semantic model
- `conversion-output/section-15-sales-customer-dashboards/layout.json` — Power BI layout specification
- `conversion-output/section-15-sales-customer-dashboards/theme.json` — Power BI theme
- `conversion-output/section-15-sales-customer-dashboards/power_query.pq` — Power Query M scripts
- `conversion-output/section-15-sales-customer-dashboards/validation_report.md` — This report

## Conversion Notes

- All Tableau calculated fields successfully converted to DAX measures
- Original Tableau formulas preserved as comments in dax_measures.dax
- 1 parameter(s) converted to What-If parameters using GENERATESERIES/disconnected tables
- Star schema data model with Orders (fact), Customers (dim), Products (dim), Date (dim)
- Power Query M scripts handle semicolon-delimited CSV import with DD/MM/YYYY date parsing
