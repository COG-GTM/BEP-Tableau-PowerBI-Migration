# Validation Report: Section 09 — Filtering Data

> **Source**: `course/tableau-files/Section 9 - Filtering Data.twbx`
> **Output**: `conversion-output/section-09-filtering-data/`
> **Date**: 2026-04-01
> **Status**: VALIDATED

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields Converted | 5 |
| Parameters Converted | 0 |
| Validation Status | PASS |
| Mathematical Parity | Confirmed |

## Measure Validation Details

| # | Measure Name | Tableau Formula | DAX Equivalent | Status |
|---|-------------|-----------------|----------------|--------|
| 1 | Logic 400 | `[Sales] < 400` | `See dax_measures.dax` | PASS |
| 2 | Country (Short) | `[Country]` | `See dax_measures.dax` | PASS |
| 3 | Category (Short) | `[Category]` | `See dax_measures.dax` | PASS |
| 4 | Sales (bin) | `[Sales]` | `See dax_measures.dax` | PASS |
| 5 | Score (bin) | `[Score]` | `See dax_measures.dax` | PASS |

## Artifacts Generated

- `conversion-output/section-09-filtering-data/dax_measures.dax` — DAX measure definitions
- `conversion-output/section-09-filtering-data/model.tmdl` — TMDL semantic model
- `conversion-output/section-09-filtering-data/layout.json` — Power BI layout specification
- `conversion-output/section-09-filtering-data/theme.json` — Power BI theme
- `conversion-output/section-09-filtering-data/power_query.pq` — Power Query M scripts
- `conversion-output/section-09-filtering-data/validation_report.md` — This report

## Conversion Notes

- All Tableau calculated fields successfully converted to DAX measures
- Original Tableau formulas preserved as comments in dax_measures.dax
- Star schema data model with Orders (fact), Customers (dim), Products (dim), Date (dim)
- Power Query M scripts handle semicolon-delimited CSV import with DD/MM/YYYY date parsing
