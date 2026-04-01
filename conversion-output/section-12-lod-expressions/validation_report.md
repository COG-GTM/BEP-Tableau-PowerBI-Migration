# Validation Report: Section 12 — LOD Expressions

> **Source**: `course/tableau-files/LOD Expressions.twbx`
> **Output**: `conversion-output/section-12-lod-expressions/`
> **Date**: 2026-04-01
> **Status**: VALIDATED

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields Converted | 8 |
| Parameters Converted | 0 |
| Validation Status | PASS |
| Mathematical Parity | Confirmed |

## Measure Validation Details

| # | Measure Name | Tableau Formula | DAX Equivalent | Status |
|---|-------------|-----------------|----------------|--------|
| 1 | Sales By Category | `{ FIXED [Category] : SUM([Sales]) }` | `CALCULATE(` | PASS |
| 2 | Sales Exclude Category | `{ EXCLUDE [Category] : SUM([Sales]) }` | `CALCULATE(` | PASS |
| 3 | Calculation1 | `{ INCLUDE [First_Name] : SUM([Sales]) }` | `See dax_measures.dax` | PASS |
| 4 | Avg Sales of Customers | `{ INCLUDE [First_Name] : SUM([Sales]) }` | `See dax_measures.dax` | PASS |
| 5 | Nr. of Orders per Customer | `{ FIXED [Customer_ID]: COUNT([Order_ID]) }` | `CALCULATE(` | PASS |
| 6 | Sales of Tables | `IF [Sub_Category] = "Tables" THEN [Sales] END` | `See dax_measures.dax` | PASS |
| 7 | Exclude Sub Category | `{ EXCLUDE [Sub_Category]: SUM([Calculation_15965261055957...` | `CALCULATE(` | PASS |
| 8 | Difference | `SUM([Sales]) - SUM([Calculation_1596526105598066726])` | `SUM(Orders[Sales])` | PASS |

## Artifacts Generated

- `conversion-output/section-12-lod-expressions/dax_measures.dax` — DAX measure definitions
- `conversion-output/section-12-lod-expressions/model.tmdl` — TMDL semantic model
- `conversion-output/section-12-lod-expressions/layout.json` — Power BI layout specification
- `conversion-output/section-12-lod-expressions/theme.json` — Power BI theme
- `conversion-output/section-12-lod-expressions/power_query.pq` — Power Query M scripts
- `conversion-output/section-12-lod-expressions/validation_report.md` — This report

## Conversion Notes

- All Tableau calculated fields successfully converted to DAX measures
- Original Tableau formulas preserved as comments in dax_measures.dax
- Star schema data model with Orders (fact), Customers (dim), Products (dim), Date (dim)
- Power Query M scripts handle semicolon-delimited CSV import with DD/MM/YYYY date parsing
