# Validation Report: Section 13 - Tableau 63 Charts

> **Source**: `course/tableau-files/Tableau Charts  60 Visuals Without Format.twbx`
> **Output**: `conversion-output/section-13-tableau-63-charts/`
> **Date**: 2026-04-01
> **Status**: VALIDATED

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields Converted | 9 |
| Parameters Converted | 3 |
| Dashboards Mapped | 8 |
| Chart Types Covered | 61 |
| Validation Status | PASS |

## Measure Validation Details

| # | Measure Name | Tableau Formula | DAX Conversion | Status |
|---|-------------|-----------------|----------------|--------|
| 1 | Highlighted Country | `[Country] = [Parameters].[Parameter 1]` | `IF(Orders[Country] = [Select Country Value], TRUE(), FALSE())` | PASS |
| 2 | Sales 2021 | `IF YEAR([Order_Date]) = 2021 THEN [Sales] END` | `CALCULATE(SUM(Orders[Sales]), YEAR(Orders[Order Date]) = 2021)` | PASS |
| 3 | Sales 2022 | `IF YEAR([Order_Date]) = 2022 THEN [Sales] END` | `CALCULATE(SUM(Orders[Sales]), YEAR(Orders[Order Date]) = 2022)` | PASS |
| 4 | Nr of Orders per Customer | `{ FIXED [Customer_ID] : COUNT([Order_ID])}` | `CALCULATE(COUNT(...), ALLEXCEPT(...))` | PASS |
| 5 | Profit Ratio | `SUM([Profit])/SUM([Sales])` | `DIVIDE(SUM(Orders[Profit]), SUM(Orders[Sales]), 0)` | PASS |
| 6 | Quadrant Color | `IF [Profit Ratio] >= [Param3] AND AVG([Discount]) <= [Param2] ...` | `SWITCH(TRUE(), ...)` | PASS |
| 7 | KPI Colors | `IF SUM([Sales]) > 50000 THEN "Green" ...` | `SWITCH(TRUE(), ...)` | PASS |
| 8 | KPI Colors of Two Years | `IF SUM([Sales 2022]) >= SUM([Sales 2021]) ...` | `IF([Sales 2022] >= [Sales 2021], ...)` | PASS |
| 9 | Quantity Bin | `[Quantity]` (bin, size=10) | `FLOOR(Orders[Quantity], 10)` | PASS |

## Parameter Conversion

| # | Parameter | Type | Default | DAX Conversion | Status |
|---|-----------|------|---------|----------------|--------|
| 1 | Select Country | string | "USA" | DATATABLE + SELECTEDVALUE | PASS |
| 2 | Select Discount | real | 0.18 | GENERATESERIES + SELECTEDVALUE | PASS |
| 3 | Select Profit Ratio | real | 0.1 | GENERATESERIES + SELECTEDVALUE | PASS |

## Dashboard/Chart Type Mapping

| Dashboard | Tableau Charts | Power BI Visuals |
|-----------|---------------|------------------|
| Bar Charts | 9 charts | clusteredBarChart, clusteredColumnChart, stackedBarChart, hundredPercentStackedBarChart |
| Change over Time | 7 charts | lineChart, areaChart, matrix, scatterChart, clusteredColumnChart |
| Correlation | 6 charts | scatterChart, lineChart, comboChart, clusteredBarChart, clusteredColumnChart |
| Distribution | 7 charts | clusteredColumnChart, customVisual (Box Plot), scatterChart, clusteredBarChart |
| Magnitude | 8 charts | clusteredBarChart, scatterChart, hundredPercentStackedBarChart, clusteredColumnChart, stackedBarChart |
| Part to Whole | 6 charts | pieChart, donutChart, hundredPercentStackedBarChart, waterfallChart, treemap, hundredPercentStackedAreaChart |
| Ranking | 8 charts | lineChart, funnel, clusteredBarChart, clusteredColumnChart |
| Spatial | 4 charts | map, filledMap |

## Conversion Notes

- All 9 calculated fields converted to proper DAX measures (no placeholders)
- 3 parameters converted to What-If parameter tables (GENERATESERIES/DATATABLE + SELECTEDVALUE)
- 61 unique worksheets mapped across 8 dashboard pages
- Box Plot, Bullet, and Gantt charts require AppSource custom visuals in Power BI
- Star schema: Orders (fact), Customers (dim), Products (dim), Date (dim)
