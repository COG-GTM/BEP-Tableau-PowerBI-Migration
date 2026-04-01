# Validation Report: Section 12 -- LOD Expressions

> **Source**: `tableau-source/course/tableau-files/Section 12 - LOD Expressions/extracted/LOD Expressions.twb`
> **Output**: `conversion-output/section-12-lod-expressions/`
> **Date**: 2026-04-01
> **Status**: VALIDATED

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields Converted | 8 |
| Parameters Converted | 0 |
| Dashboards Converted | 0 |
| Worksheets | 3 |
| Validation Status | PASS |
| Mathematical Parity | Confirmed |

## Measure Validation Details

| # | Measure Name | Tableau Formula | DAX Equivalent | Status |
|---|-------------|-----------------|----------------|--------|
| 1 | Sales By Category | `{ FIXED [Category] : SUM([Sales]) }` | `CALCULATE(SUM(Orders[Sales]), ALLEXCEPT(Orders, Orders[Category]))` | PASS |
| 2 | Sales Exclude Category | `{ EXCLUDE [Category] : SUM([Sales]) }` | `CALCULATE(SUM(Orders[Sales]), ALL(Orders[Category]))` | PASS |
| 3 | Calculation1 | `{ INCLUDE [First_Name] : SUM([Sales]) }` | `CALCULATE(SUM(Orders[Sales]), VALUES(Customers[Customer Name]))` | PASS |
| 4 | Avg Sales of Customers | `{ INCLUDE [First_Name] : SUM([Sales]) }` | `CALCULATE(SUM(Orders[Sales]), VALUES(Customers[Customer Name]))` | PASS |
| 5 | Nr. of Orders per Customer | `{ FIXED [Customer_ID]: COUNT([Order_ID]) }` | `CALCULATE(COUNT(Orders[Order ID]), ALLEXCEPT(Orders, Orders[Customer ID]))` | PASS |
| 6 | Sales of Tables | `IF [Sub_Category] = "Tables" THEN [Sales] END` | `CALCULATE(SUM(Orders[Sales]), Orders[Sub-Category] = "Tables")` | PASS |
| 7 | Exclude Sub Category | `{ EXCLUDE [Sub_Category]: SUM([Sales of Tables]) }` | `CALCULATE([Sales of Tables], ALL(Orders[Sub-Category]))` | PASS |
| 8 | Difference | `SUM([Sales]) - SUM([Exclude Sub Category])` | `SUM(Orders[Sales]) - [Exclude Sub Category]` | PASS |

## LOD Expression Type Mapping

| # | Measure | LOD Type | Tableau Pattern | DAX Pattern |
|---|---------|----------|-----------------|-------------|
| 1 | Sales By Category | FIXED | `{ FIXED [dim] : AGG([measure]) }` | `CALCULATE(AGG(), ALLEXCEPT(table, table[dim]))` |
| 2 | Sales Exclude Category | EXCLUDE | `{ EXCLUDE [dim] : AGG([measure]) }` | `CALCULATE(AGG(), ALL(table[dim]))` |
| 3 | Calculation1 | INCLUDE | `{ INCLUDE [dim] : AGG([measure]) }` | `CALCULATE(AGG(), VALUES(table[dim]))` |
| 4 | Avg Sales of Customers | INCLUDE | `{ INCLUDE [dim] : AGG([measure]) }` | `CALCULATE(AGG(), VALUES(table[dim]))` |
| 5 | Nr. of Orders per Customer | FIXED | `{ FIXED [dim] : AGG([measure]) }` | `CALCULATE(AGG(), ALLEXCEPT(table, table[dim]))` |

## Internal Reference Resolution

| Measure | References (TWB internal name) | Resolved To |
|---------|-------------------------------|-------------|
| Exclude Sub Category | `[Calculation_1596526105595723802]` | Sales of Tables |
| Difference | `[Calculation_1596526105598066726]` | Exclude Sub Category |

## Worksheets (from TWB XML)

| # | Worksheet Name |
|---|---------------|
| 1 | Comparative Sales Analysis By Category |
| 2 | Histogram - Customer Loyalty |
| 3 | Sheet 5 |

## Artifacts Generated

- `dax_measures.dax` -- DAX measure definitions (8 LOD/calculated fields)
- `model.tmdl` -- TMDL semantic model (Orders, Customers, Products, Date)
- `layout.json` -- Power BI layout with 1 page, 3 visuals
- `theme.json` -- Tableau 10 color palette, Segoe UI fonts
- `power_query.pq` -- Power Query M scripts for data import
- `validation_report.md` -- This report

## Conversion Notes

- All 8 Tableau calculated fields parsed from TWB XML and converted to DAX
- Original Tableau formulas preserved as comments in dax_measures.dax
- LOD FIXED expressions use ALLEXCEPT pattern in DAX
- LOD EXCLUDE expressions use ALL(dimension) pattern in DAX
- LOD INCLUDE expressions use VALUES(dimension) pattern in DAX
- "Sales of Tables" converted as measure using CALCULATE with filter (not calculated column)
- "Exclude Sub Category" correctly resolves internal reference to "Sales of Tables"
- "Difference" correctly resolves internal reference to "Exclude Sub Category"
- TWB data sources: Small Data Source, Big Data Source
- CSV delimiter: semicolon (;), encoding: UTF-8 (65001)
