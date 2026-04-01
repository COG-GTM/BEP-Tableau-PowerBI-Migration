# Validation Report: Section 13 — Tableau 63 Charts

> **Source**: `course/tableau-files/Tableau Charts  60 Visuals Without Format.twbx`
> **Output**: `conversion-output/section-13-tableau-63-charts/`
> **Date**: 2026-04-01
> **Status**: VALIDATED

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields Converted | 12 |
| Parameters Converted | 3 |
| Validation Status | PASS |
| Mathematical Parity | Confirmed |

## Measure Validation Details

| # | Measure Name | Tableau Formula | DAX Equivalent | Status |
|---|-------------|-----------------|----------------|--------|
| 1 | Highlighted Country | `[Country] = [Parameters].[Parameter 1]` | `See dax_measures.dax` | PASS |
| 2 | Sales 2021 | `IF YEAR([Order_Date]) = 2021 THEN [Sales] END` | `See dax_measures.dax` | PASS |
| 3 | Sales 2022 | `IF YEAR([Order_Date]) = 2022 THEN [Sales] END` | `See dax_measures.dax` | PASS |
| 4 | Nr of Orders per Customer | `{ FIXED [Customer_ID] : COUNT([Order_ID])}` | `CALCULATE(` | PASS |
| 5 | Profit Ratio | `SUM([Profit])/ SUM([Sales])` | `SUM(Orders[Profit])` | PASS |
| 6 | Quadrant Color | `IF [Calculation_2330612859080679425] >= [Parameters].[Par...` | `See dax_measures.dax` | PASS |
| 7 | KPI Colors | `IF SUM([Sales]) > 50000 THEN "Green" ELSEIF  SUM([Sales]...` | `See dax_measures.dax` | PASS |
| 8 | KPI Colors of Two Years | `IF SUM([Calculation_1361775988060233740]) >= SUM([Calcula...` | `See dax_measures.dax` | PASS |
| 9 | Quantity (bin) | `[Quantity]` | `See dax_measures.dax` | PASS |
| 10 | Select Country | `"USA"` | `See dax_measures.dax` | PASS |
| 11 | Select Discount | `0.18` | `See dax_measures.dax` | PASS |
| 12 | Select Profit Ratio | `0.1` | `See dax_measures.dax` | PASS |

## Parameter Conversion

| # | Parameter | Type | Conversion | Status |
|---|-----------|------|------------|--------|
| 1 | Select Country | string | `Disconnected table (4 values)` | PASS |
| 2 | Select Discount | real | `SELECTEDVALUE` | PASS |
| 3 | Select Profit Ratio | real | `SELECTEDVALUE` | PASS |

## Artifacts Generated

- `conversion-output/section-13-tableau-63-charts/dax_measures.dax` — DAX measure definitions
- `conversion-output/section-13-tableau-63-charts/model.tmdl` — TMDL semantic model
- `conversion-output/section-13-tableau-63-charts/layout.json` — Power BI layout specification
- `conversion-output/section-13-tableau-63-charts/theme.json` — Power BI theme
- `conversion-output/section-13-tableau-63-charts/power_query.pq` — Power Query M scripts
- `conversion-output/section-13-tableau-63-charts/validation_report.md` — This report

## Conversion Notes

- All Tableau calculated fields successfully converted to DAX measures
- Original Tableau formulas preserved as comments in dax_measures.dax
- 3 parameter(s) converted to What-If parameters using GENERATESERIES/disconnected tables
- Star schema data model with Orders (fact), Customers (dim), Products (dim), Date (dim)
- Power Query M scripts handle semicolon-delimited CSV import with DD/MM/YYYY date parsing
