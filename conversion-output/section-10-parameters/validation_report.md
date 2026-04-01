# Validation Report: Section 10 — Parameters

> **Source**: `course/tableau-files/Section 10 - Parameters.twbx`
> **Output**: `conversion-output/section-10-parameters/`
> **Date**: 2026-04-01
> **Status**: VALIDATED

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields Converted | 12 |
| Parameters Converted | 5 |
| Validation Status | PASS |
| Mathematical Parity | Confirmed |

## Measure Validation Details

| # | Measure Name | Tableau Formula | DAX Equivalent | Status |
|---|-------------|-----------------|----------------|--------|
| 1 | Logic 400 | `[Sales] < 400` | `See dax_measures.dax` | PASS |
| 2 | Country (Short) | `[Country]` | `See dax_measures.dax` | PASS |
| 3 | KPI Colors | `If SUM([Profit]) < [Parameters].[Parameter 4] THEN 'Red'...` | `See dax_measures.dax` | PASS |
| 4 | Dynamic Dimension | `CASE [Parameters].[Parameter 1] WHEN 'Country' THEN [Cou...` | `See dax_measures.dax` | PASS |
| 5 | Dynamic Measure | `CASE [Parameters].[Parameter 2] WHEN 'Sales' THEN [Sales...` | `See dax_measures.dax` | PASS |
| 6 | Category (Short) | `[Category]` | `See dax_measures.dax` | PASS |
| 7 | Sales (bin) | `[Sales]` | `See dax_measures.dax` | PASS |
| 8 | Score (bin) | `[Score]` | `See dax_measures.dax` | PASS |
| 9 | Choose Dimension | `"Country"` | `See dax_measures.dax` | PASS |
| 10 | Choose Measure | `"Sales"` | `See dax_measures.dax` | PASS |
| 11 | Choose Size of Bins | `20.` | `See dax_measures.dax` | PASS |
| 12 | Choose Threshold | `10000` | `See dax_measures.dax` | PASS |

## Parameter Conversion

| # | Parameter | Type | Conversion | Status |
|---|-----------|------|------------|--------|
| 1 | Choose Dimension | string | `Disconnected table (2 values)` | PASS |
| 2 | Choose Measure | string | `Disconnected table (3 values)` | PASS |
| 3 | Choose Size of Bins | real | `GENERATESERIES(5.0, 25.0, 1)` | PASS |
| 4 | Choose Threshold | integer | `SELECTEDVALUE` | PASS |
| 5 | Choose Top N Products | integer | `GENERATESERIES(0, 50, 1)` | PASS |

## Artifacts Generated

- `conversion-output/section-10-parameters/dax_measures.dax` — DAX measure definitions
- `conversion-output/section-10-parameters/model.tmdl` — TMDL semantic model
- `conversion-output/section-10-parameters/layout.json` — Power BI layout specification
- `conversion-output/section-10-parameters/theme.json` — Power BI theme
- `conversion-output/section-10-parameters/power_query.pq` — Power Query M scripts
- `conversion-output/section-10-parameters/validation_report.md` — This report

## Conversion Notes

- All Tableau calculated fields successfully converted to DAX measures
- Original Tableau formulas preserved as comments in dax_measures.dax
- 5 parameter(s) converted to What-If parameters using GENERATESERIES/disconnected tables
- Star schema data model with Orders (fact), Customers (dim), Products (dim), Date (dim)
- Power Query M scripts handle semicolon-delimited CSV import with DD/MM/YYYY date parsing
