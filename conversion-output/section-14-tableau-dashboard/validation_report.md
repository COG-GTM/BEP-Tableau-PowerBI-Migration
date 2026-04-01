# Validation Report: Section 14 - Tableau Dashboard

> **Source**: `course/tableau-files/Section 14 - Tableau Dashboard.twbx`
> **Output**: `conversion-output/section-14-tableau-dashboard/`
> **Date**: 2026-04-01
> **Status**: VALIDATED

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields Converted | 3 |
| Parameters Converted | 0 |
| Dashboards Mapped | 1 |
| Validation Status | PASS |

## Measure Validation Details

| # | Measure Name | Tableau Formula | DAX Conversion | Status |
|---|-------------|-----------------|----------------|--------|
| 1 | Category (Short) | `[Category]` (alias) | `Orders[Category]` (calculated column) | PASS |
| 2 | Logic 400 | `[Sales] < 400` | `IF(Orders[Sales] < 400, TRUE(), FALSE())` | PASS |
| 3 | Country (Short) | `[Country]` (alias) | `Orders[Country]` (calculated column) | PASS |

## Dashboard Layout Mapping

| Tableau Element | Power BI Equivalent |
|----------------|-------------------|
| Map worksheet | map visual |
| Bar chart (Category) | clusteredBarChart |
| Bar chart (Sub-Category) | clusteredBarChart with conditional formatting |
| Line chart (trend) | lineChart |
| Filter (Segment) | slicer |
| Filter (Region) | slicer |
| Fixed-size containers | Absolute positioning in layout.json |

## Conversion Notes

- Dashboard layout with fixed positioning mapped to Power BI page layout
- Conditional formatting (Sales < 400) implemented via calculated column + visual rules
- Aliases mapped to calculated columns (Category Short, Country Short)
- Cross-filter and cross-highlight interactions preserved
- Star schema: Orders (fact), Customers (dim), Products (dim), Date (dim)
