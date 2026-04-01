# Validation Report: Section 12 — Aggregate Calculations

> **Source**: `course/tableau-files/Section 11 -  Attribute.twbx`
> **Output**: `conversion-output/section-12-aggregate-calculations/`
> **Date**: 2026-04-01
> **Status**: VALIDATED

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields Converted | 7 |
| Parameters Converted | 0 |
| Validation Status | PASS |
| Mathematical Parity | Confirmed |

## Measure Validation Details

| # | Measure Name | Tableau Formula | DAX Equivalent | Status |
|---|-------------|-----------------|----------------|--------|
| 1 | Total Sales | `SUM([Sales])` | `SUM(Orders[Sales])` | PASS |
| 2 |  Avg. Sales | `AVG([Sales])` | `AVERAGE(Orders[Sales])` | PASS |
| 3 | Nr. of Orders | `COUNT([Order_ID])` | `COUNT(Orders[Order_ID])` | PASS |
| 4 | Nr. Of Products | `COUNTD([Product_ID])` | `DISTINCTCOUNT(Orders[Product_ID])` | PASS |
| 5 | Highest Sales | `MAX([Sales])` | `MAX(Orders[Sales])` | PASS |
| 6 | Lowest Sales | `MIN([Sales])` | `MIN(Orders[Sales])` | PASS |
| 7 | Attr(Postal Code) | `ATTR([Postal_Code])` | `See dax_measures.dax` | PASS |

## Artifacts Generated

- `conversion-output/section-12-aggregate-calculations/dax_measures.dax` — DAX measure definitions
- `conversion-output/section-12-aggregate-calculations/model.tmdl` — TMDL semantic model
- `conversion-output/section-12-aggregate-calculations/layout.json` — Power BI layout specification
- `conversion-output/section-12-aggregate-calculations/theme.json` — Power BI theme
- `conversion-output/section-12-aggregate-calculations/power_query.pq` — Power Query M scripts
- `conversion-output/section-12-aggregate-calculations/validation_report.md` — This report

## Conversion Notes

- All Tableau calculated fields successfully converted to DAX measures
- Original Tableau formulas preserved as comments in dax_measures.dax
- Star schema data model with Orders (fact), Customers (dim), Products (dim), Date (dim)
- Power Query M scripts handle semicolon-delimited CSV import with DD/MM/YYYY date parsing
