# Validation Report: Section 09 -- Filtering Data

> **Source**: `tableau-source/course/tableau-files/Section 09 - Filtering Data/extracted/Section 9 - Filtering Data.twb`
> **Output**: `conversion-output/section-09-filtering-data/`
> **Date**: 2026-04-01
> **Status**: CONVERTED

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields Converted | 5 |
| Parameters Converted | 0 |
| Filter Patterns Documented | 5 (dimension, context, data source, date, measure) |
| Worksheets Mapped | 8 |
| Validation Status | PASS |

## Measure Validation Details

| # | Measure Name | Tableau Formula | DAX Equivalent | Status |
|---|-------------|-----------------|----------------|--------|
| 1 | Logic 400 | `[Sales] < 400` (boolean) | `IF(SUM(Orders[Sales]) < 400, TRUE(), FALSE())` | PASS |
| 2 | Country (Short) | `[Country]` (alias: FR->France, DE->Germany) | `SWITCH(SELECTEDVALUE(Orders[Country]), ...)` | PASS |
| 3 | Category (Short) | `[Category]` (alias: F->Furniture, O->Office Supplies, T->Technology) | `SWITCH(SELECTEDVALUE(Orders[Category]), ...)` | PASS |
| 4 | Sales (bin) | `[Sales]` (bin, class=bin, auto-sized) | `INT(Orders[Sales] / 100) * 100` | PASS |
| 5 | Score (bin) | `[Score]` (bin, class=bin, auto-sized) | `INT(Orders[Score] / 10) * 10` | PASS |

## Filter Pattern Conversion Details

| # | Filter Type | Tableau Pattern | Power BI Equivalent | Worksheet |
|---|------------|----------------|--------------------|-----------| 
| 1 | Dimension Filter | `[Category] = "Office Supplies"` (categorical) | Visual-level filter or slicer | Apply Filter |
| 2 | Context Filter | Category context filter + Sub-Category + Profit% | CALCULATE with ALL/KEEPFILTERS | Context Filter - Office Supplies |
| 3 | Context Filter (Security) | Category + Sub-Category + Profit (order matters) | Demonstrates filter evaluation order | Context Filter - Security Problem |
| 4 | DataSource Filter | Country filter at data source level | Power Query Table.SelectRows or report-level filter | DataSouce Filter - Country |
| 5 | Date Filter | Year range 2020-2022 (quantitative) | Date slicer or DATESBETWEEN | Tips & Tricks |
| 6 | Measure Filter | SUM(Profit) range | Visual-level filter on aggregated measure | Context Filter - Office Supplies |

## Worksheets Mapped to Power BI Visuals

| # | Tableau Worksheet | Power BI Visual Type | Filter Features |
|---|------------------|---------------------|-----------------|
| 1 | Apply Filter | clusteredBarChart | Dimension filter: Category |
| 2 | Context Filter - Office Supplies | table | Context + measure filters |
| 3 | Context Filter - Security Problem | table | Context filter order demo |
| 4 | DataSouce Filter - Country | clusteredBarChart | Data source filter |
| 5 | DataSource Filter - Years | lineChart | Date range filter |
| 6 | Order | table | Basic view |
| 7 | Order2 | table | Basic view |
| 8 | Tips & Tricks | table | Multi-filter: Category, City, Country, Year |

## Data Model Validation

| Check | Result |
|-------|--------|
| Orders fact table present | PASS |
| Customers dimension present | PASS |
| Products dimension present | PASS |
| Date table present | PASS |
| Orders->Customers relationship | PASS |
| Orders->Products relationship | PASS |
| Orders->Date relationship | PASS |
| CSV delimiter (semicolon) | PASS |
| Date format (DD/MM/YYYY) | PASS |

## Artifacts Generated

- `dax_measures.dax` -- DAX measure definitions with filter patterns documented
- `model.tmdl` -- TMDL semantic model
- `layout.json` -- Power BI layout specification (8 visuals with filter metadata)
- `theme.json` -- Power BI theme with Tableau 10 color palette
- `power_query.pq` -- Power Query M scripts for CSV import
- `validation_report.md` -- This report
