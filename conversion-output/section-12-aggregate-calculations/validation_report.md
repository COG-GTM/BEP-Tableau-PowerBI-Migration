# Validation Report: Section 12 -- Aggregate Calculations

> **Source**: `tableau-source/course/tableau-files/Section 12 - Aggregate Calculations/extracted/Section 11 -  Attribute.twb`
> **Output**: `conversion-output/section-12-aggregate-calculations/`
> **Date**: 2026-04-01
> **Status**: VALIDATED

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields Converted | 7 |
| Parameters Converted | 0 |
| Dashboards Converted | 0 |
| Worksheets | 5 |
| Validation Status | PASS |
| Mathematical Parity | Confirmed |

## Measure Validation Details

| # | Measure Name | Tableau Formula | DAX Equivalent | Status |
|---|-------------|-----------------|----------------|--------|
| 1 | Total Sales | `SUM([Sales])` | `SUM(Orders[Sales])` | PASS |
| 2 | Avg. Sales | `AVG([Sales])` | `AVERAGE(Orders[Sales])` | PASS |
| 3 | Nr. of Orders | `COUNT([Order_ID])` | `COUNT(Orders[Order ID])` | PASS |
| 4 | Nr. Of Products | `COUNTD([Product_ID])` | `DISTINCTCOUNT(Orders[Product ID])` | PASS |
| 5 | Highest Sales | `MAX([Sales])` | `MAX(Orders[Sales])` | PASS |
| 6 | Lowest Sales | `MIN([Sales])` | `MIN(Orders[Sales])` | PASS |
| 7 | Attr(Postal Code) | `ATTR([Postal_Code])` | `IF(HASONEVALUE(Orders[Postal Code]), VALUES(Orders[Postal Code]))` | PASS |

## Worksheets (from TWB XML)

| # | Worksheet Name | Description |
|---|---------------|-------------|
| 1 | Aggregate Calc | Main aggregate calculations view |
| 2 | Attr | ATTR function demonstration |
| 3 | Attr (ToolTip) | Tooltip version of ATTR |
| 4 | Sales By Postal Code | Geographic sales visualization |
| 5 | Sheet 5 | Additional data view |

## Data Source Mapping

| TWB Source | Power BI Table |
|-----------|---------------|
| Small Data Source (federated.0mnok8g1jr2xrc1d2pdje1l9u16p) | Orders |
| Big Data Source (federated.1hpyone17bxgk51b0kg750hoe27w) | Orders (alternate) |

## Artifacts Generated

- `dax_measures.dax` -- DAX measure definitions (7 aggregate calculations)
- `model.tmdl` -- TMDL semantic model (Orders, Customers, Products, Date)
- `layout.json` -- Power BI layout with 1 page, 5 visuals
- `theme.json` -- Tableau 10 color palette, Segoe UI fonts
- `power_query.pq` -- Power Query M scripts for data import
- `validation_report.md` -- This report

## Conversion Notes

- All 7 Tableau aggregate calculated fields parsed from TWB XML and converted to DAX
- Original Tableau formulas preserved as comments in dax_measures.dax
- ATTR function correctly converted to IF(HASONEVALUE(...), VALUES(...)) pattern
- Column name mappings: Order_ID -> Order ID, Product_ID -> Product ID, Postal_Code -> Postal Code
- Star schema: Orders (fact), Customers (dim), Products (dim), Date (dim)
- CSV delimiter: semicolon (;), encoding: UTF-8 (65001)
