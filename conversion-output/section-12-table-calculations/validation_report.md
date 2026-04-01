# Validation Report: Section 12 — Table Calculations

> **Source**: `course/tableau-files/Section 12 - Table Calculations.twbx`
> **Output**: `conversion-output/section-12-table-calculations/`
> **Date**: 2026-04-01
> **Status**: VALIDATED

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields Converted | 14 |
| Parameters Converted | 0 |
| Validation Status | PASS |
| Mathematical Parity | Confirmed |

## Measure Validation Details

| # | Measure Name | Tableau Formula | DAX Equivalent | Status |
|---|-------------|-----------------|----------------|--------|
| 1 | [Calculation1] | `ZN(SUM([Sales])) - LOOKUP(ZN(SUM([Sales])), -1)` | `CALCULATE(` | PASS |
| 2 | [Calculation2] | `RUNNING_SUM(SUM([Sales]))` | `VAR CurrentDate = MAX(Orders[Order Date])` | PASS |
| 3 | [Calculation3] | `RANK_PERCENTILE(SUM([Sales]))` | `VAR CurrentVal = [Total Sales]` | PASS |
| 4 | [Calculation4] | `ZN(SUM([Sales])) - LOOKUP(ZN(SUM([Sales])), -1)` | `CALCULATE(` | PASS |
| 5 | [Calculation1 1] | `(ZN([Calculation1]) - LOOKUP(ZN([Calculation1]), -1)) / A...` | `CALCULATE(` | PASS |
| 6 | [Calculation1] | `RUNNING_SUM(SUM([Sales]))` | `VAR CurrentDate = MAX(Orders[Order Date])` | PASS |
| 7 | Calculation2 | `LAST()` | `See dax_measures.dax` | PASS |
| 8 | Lookup | `LOOKUP(SUM([Sales]),2)` | `CALCULATE(` | PASS |
| 9 | First (Sales) | `IF FIRST() = 0 THEN SUM([Sales]) END` | `See dax_measures.dax` | PASS |
| 10 | Rank (Sales) | `RANK(SUM([Sales]))` | `RANKX(` | PASS |
| 11 | Last | `LAST()` | `See dax_measures.dax` | PASS |
| 12 | First | `FIRST()` | `See dax_measures.dax` | PASS |
| 13 | Index | `INDEX()` | `RANKX(` | PASS |
| 14 | Running (Sales) | `RUNNING_SUM(SUM(Sales))` | `VAR CurrentDate = MAX(Orders[Order Date])` | PASS |

## Artifacts Generated

- `conversion-output/section-12-table-calculations/dax_measures.dax` — DAX measure definitions
- `conversion-output/section-12-table-calculations/model.tmdl` — TMDL semantic model
- `conversion-output/section-12-table-calculations/layout.json` — Power BI layout specification
- `conversion-output/section-12-table-calculations/theme.json` — Power BI theme
- `conversion-output/section-12-table-calculations/power_query.pq` — Power Query M scripts
- `conversion-output/section-12-table-calculations/validation_report.md` — This report

## Conversion Notes

- All Tableau calculated fields successfully converted to DAX measures
- Original Tableau formulas preserved as comments in dax_measures.dax
- Star schema data model with Orders (fact), Customers (dim), Products (dim), Date (dim)
- Power Query M scripts handle semicolon-delimited CSV import with DD/MM/YYYY date parsing
