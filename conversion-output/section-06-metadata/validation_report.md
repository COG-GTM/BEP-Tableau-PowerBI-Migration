# Section 06 — Metadata — Conversion Validation Report

> **Source**: `tableau-source/course/tableau-files/Section 06 - Metadata/extracted/Section 6 - Data Modelling.twb`
> **Output**: `conversion-output/section-06-metadata/`
> **Generated**: 2026-04-01
> **Status**: Conversion Complete — PASS

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields Converted | 1 |
| Parameters Converted | 0 |
| Dashboards Converted | 2 |
| Validation Status | PASS |
| Mathematical Parity | Confirmed |

---

## Calculated Fields Validation

| # | Measure Name | Tableau Formula | DAX Equivalent | Status |
|---|-------------|-----------------|----------------|--------|
| 1 | Logic 400 | `[Sales] < 400` | `IF(Orders[Sales] < 400, TRUE(), FALSE())` | PASS |

---

## Dashboard Conversion

### Dashboard 1: Continuous vs Discrete

Mapped from Tableau dashboard `Continuous vs Discrete` (fixed size: 1000x800).

| Zone ID | Worksheet | Power BI Visual | Visual Type |
|---------|-----------|-----------------|-------------|
| 3 | Continuous | continuous_line_chart | lineChart |
| 5 | Discrete | discrete_bar_chart | clusteredColumnChart |

**Tableau zones (from TWB XML)**:
- Zone 4 (layout-basic): Root container (100000x100000)
- Zone 3: "Continuous" worksheet (98400x60250, position x=800 y=1000)
- Zone 5: "Discrete" worksheet (98400x37750, position x=800 y=61250)

### Dashboard 2: Sales Dashboard

Mapped from Tableau dashboard `Sales Dashboard` (fixed size: 1000x800).

| Zone ID | Worksheet | Power BI Visual | Visual Type |
|---------|-----------|-----------------|-------------|
| 3 | Sales By Country | sales_by_country | clusteredBarChart |
| 8 | Sales By Country (size legend) | sales_size_legend | card |
| 10 | Sales By Category (color legend) | category_color_legend | slicer |
| 9 | Sales By Category | sales_by_category | donutChart |
| 12 | Sales By Month | sales_by_month | lineChart |
| 11 | Sales By Product | sales_by_product | table |

**Tableau zones (from TWB XML)**:
- Zone 4 (layout-basic): Root container
- Zone 7 (layout-flow, horizontal): Main content area
- Zone 5 (layout-basic): Left panel containing worksheets
- Zone 6 (layout-flow, vertical, fixed 111px): Right panel with legends
- Zone 3: "Sales By Country" — top spanning, full width (87300x49000)
- Zone 9: "Sales By Category" — bottom-left (30406x49000)
- Zone 12: "Sales By Month" — bottom-center (26911x49000)
- Zone 11: "Sales By Product" — bottom-right (29983x49000)
- Zone 8: Size legend for Sales By Country
- Zone 10: Color legend for Category

---

## Worksheets in Workbook

The TWB contains 9 worksheets:

| # | Worksheet Name | Used in Dashboard | Visual Type |
|---|---------------|-------------------|-------------|
| 1 | Continuous | Continuous vs Discrete | lineChart |
| 2 | Dimensions & Measures | — (standalone) | — |
| 3 | Discrete | Continuous vs Discrete | clusteredColumnChart |
| 4 | Image Role | — (standalone) | — |
| 5 | Sales By Category | Sales Dashboard | donutChart |
| 6 | Sales By Country | Sales Dashboard | clusteredBarChart |
| 7 | Sales By Month | Sales Dashboard | lineChart |
| 8 | Sales By Product | Sales Dashboard | table |
| 9 | Sheet 2 | — (standalone) | — |

---

## Artifacts Generated

1. `dax_measures.dax` — 1 calculated column (Logic 400)
2. `model.tmdl` — Semantic model with Orders, Customers, Products, Date tables and relationships
3. `layout.json` — Two-page report layout (Continuous vs Discrete, Sales Dashboard)
4. `theme.json` — Tableau 10 color palette theme
5. `power_query.pq` — Power Query M scripts for 4 tables
6. `validation_report.md` — This file

---

## Conversion Notes

### 1. Continuous vs Discrete Dashboard
This Tableau dashboard demonstrates the difference between continuous (green) and discrete (blue) date fields. In Power BI, continuous is modeled as a line chart with date axis, and discrete as a clustered column chart with month name categories.

### 2. Sales Dashboard Layout
The Tableau dashboard uses a horizontal flow layout (zone 7) with a main content area (zone 5) and a fixed-width legend panel (zone 6, 111px). In Power BI, this is converted to a single page with visuals positioned to approximate the original layout.

### 3. Boolean Calculated Field
The `Logic 400` field (`[Sales] < 400`) appears in both the "Big Data Source" and the secondary data source. Converted once as a calculated column on the Orders table.
