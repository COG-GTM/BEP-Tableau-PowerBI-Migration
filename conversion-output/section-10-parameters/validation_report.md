# Validation Report: Section 10 -- Parameters

> **Source**: `tableau-source/course/tableau-files/Section 10 - Parameters/extracted/Section 10 - Parameters.twb`
> **Output**: `conversion-output/section-10-parameters/`
> **Date**: 2026-04-01
> **Status**: CONVERTED

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields Converted | 12 |
| Parameters Converted | 5 |
| Parameter Tables Created | 5 |
| Worksheets Mapped | 4 |
| Slicer Visuals Added | 5 |
| Validation Status | PASS |

## Parameter Conversion Details

| # | Parameter Name | TWB Column | Type | Range/Values | Default | Power BI Implementation |
|---|---------------|-----------|------|-------------|---------|------------------------|
| 1 | Choose Dimension | [Parameter 1] | string | "Country", "Category" | "Country" | Disconnected table + SELECTEDVALUE |
| 2 | Choose Measure | [Parameter 2] | string | "Sales", "Profit", "Quantity" | "Sales" | Disconnected table + SELECTEDVALUE |
| 3 | Choose Size of Bins | [Parameter 3] | real | 5.0 - 25.0 (step 5.0) | 20 | GENERATESERIES(5.0, 25.0, 5.0) |
| 4 | Choose Threshold | [Parameter 4] | integer | (no range in TWB) | 10000 | GENERATESERIES(0, 50000, 1000) |
| 5 | Choose Top N Products | [Parameter 5] | integer | 0 - 50 (step 5) | 15 | GENERATESERIES(0, 50, 5) |

## Measure Validation Details

| # | Measure Name | Tableau Formula | DAX Equivalent | Status |
|---|-------------|-----------------|----------------|--------|
| 1 | Logic 400 | `[Sales] < 400` | `IF(SUM(Orders[Sales]) < 400, TRUE(), FALSE())` | PASS |
| 2 | Country (Short) | `[Country]` (alias) | `SWITCH(SELECTEDVALUE(Orders[Country]), ...)` | PASS |
| 3 | KPI Colors | `If SUM([Profit]) < [Parameters].[Parameter 4] THEN 'Red' ELSE 'Green' END` | `IF(SUM(Orders[Profit]) < [Choose Threshold Value], "Red", "Green")` | PASS |
| 4 | Dynamic Dimension | `CASE [Parameters].[Parameter 1] WHEN 'Country' THEN [Country] WHEN 'Category' THEN [Category] END` | `SWITCH([Choose Dimension Value], "Country", SELECTEDVALUE(Orders[Country]), "Category", SELECTEDVALUE(Orders[Category]), ...)` | PASS |
| 5 | Dynamic Measure | `CASE [Parameters].[Parameter 2] WHEN 'Sales' THEN [Sales] WHEN 'Profit' THEN [Profit] WHEN 'Quantity' THEN [Quantity] END` | `SWITCH([Choose Measure Value], "Sales", SUM(Orders[Sales]), "Profit", SUM(Orders[Profit]), "Quantity", SUM(Orders[Quantity]), ...)` | PASS |
| 6 | Category (Short) | `[Category]` (alias) | `SWITCH(SELECTEDVALUE(Orders[Category]), ...)` | PASS |
| 7 | Sales (bin) | `[Sales]` (dynamic bin) | `INT(Orders[Sales] / [Choose Size of Bins Value]) * [Choose Size of Bins Value]` | PASS |
| 8 | Score (bin) | `[Score]` (bin) | `INT(Orders[Score] / 10) * 10` | PASS |
| 9 | Top N Filter Active | Top N using [Parameter 5] | `RANKX(...) <= [Choose Top N Products Value]` | PASS |

## Parameter Mapping Reference

| Tableau Reference | Power BI Measure |
|------------------|-----------------|
| `[Parameters].[Parameter 1]` | `[Choose Dimension Value]` |
| `[Parameters].[Parameter 2]` | `[Choose Measure Value]` |
| `[Parameters].[Parameter 3]` | `[Choose Size of Bins Value]` |
| `[Parameters].[Parameter 4]` | `[Choose Threshold Value]` |
| `[Parameters].[Parameter 5]` | `[Choose Top N Products Value]` |

## Worksheets Mapped to Power BI Visuals

| # | Tableau Worksheet | Power BI Visual Type | Parameters Used |
|---|------------------|---------------------|----------------|
| 1 | Parameters Swap Dimensions & Meausres | clusteredBarChart | Choose Dimension, Choose Measure |
| 2 | Parameters in Bins | clusteredColumnChart | Choose Size of Bins |
| 3 | Parameters in Calc & Reference Line | clusteredBarChart | Choose Threshold (KPI Colors) |
| 4 | Parameters in Filters | clusteredBarChart | Choose Top N Products |

## Data Model Validation

| Check | Result |
|-------|--------|
| Orders fact table present | PASS |
| Customers dimension present | PASS |
| Products dimension present | PASS |
| Date table present | PASS |
| Choose Dimension parameter table | PASS |
| Choose Measure parameter table | PASS |
| Choose Size of Bins parameter table | PASS |
| Choose Threshold parameter table | PASS |
| Choose Top N Products parameter table | PASS |
| Orders->Customers relationship | PASS |
| Orders->Products relationship | PASS |
| Orders->Date relationship | PASS |
| CSV delimiter (semicolon) | PASS |
| Date format (DD/MM/YYYY) | PASS |

## Artifacts Generated

- `dax_measures.dax` -- DAX measure definitions with parameter tables and converted formulas
- `model.tmdl` -- TMDL semantic model with 5 parameter tables
- `layout.json` -- Power BI layout with 5 slicer visuals + 4 worksheet visuals
- `theme.json` -- Power BI theme with Tableau 10 color palette
- `power_query.pq` -- Power Query M scripts including disconnected parameter tables
- `validation_report.md` -- This report
