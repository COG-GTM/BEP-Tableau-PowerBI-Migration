# Validation Report: Section 11 -- Actions

> **Source**: `tableau-source/course/tableau-files/Section 11 - Actions/extracted/Section 11 - Tableau Actions.twb`
> **Output**: `conversion-output/section-11-actions/`
> **Date**: 2026-04-01
> **Status**: VALIDATED

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields Converted | 5 |
| Parameters Converted | 1 |
| Dashboards Converted | 4 |
| Actions Converted | 5 |
| Worksheets | 9 |
| Validation Status | PASS |

## Measure Validation Details

| # | Measure Name | Tableau Formula | DAX Equivalent | Status |
|---|-------------|-----------------|----------------|--------|
| 1 | Calculation1 | `[Parameters].[Parameter 1]` | `[Total Value]` | PASS |
| 2 | Total (param default) | `0.` | `SELECTEDVALUE('Total Parameter'[Total], 0)` | PASS |
| 3 | Total Big DS | `[Parameters].[Parameter 1]` | `[Total Value]` | PASS |
| 4 | Sales Bin | `[Sales]` (bin) | `FLOOR(Orders[Sales], 100)` | PASS |
| 5 | Score Bin | `[Score]` (bin) | `FLOOR(Orders[Score], 10)` | PASS |

## Parameter Conversion

| # | Parameter | Type | Default | Format | DAX Conversion | Status |
|---|-----------|------|---------|--------|----------------|--------|
| 1 | Total | real | 0 | C1033% | `SELECTEDVALUE('Total Parameter'[Total], 0)` via What-If table | PASS |

## Dashboard & Action Conversion

| # | Dashboard | Zones | Tableau Actions | Power BI Equivalent | Status |
|---|-----------|-------|-----------------|---------------------|--------|
| 1 | Dashboard 4 | 9 | Parameter display + Sales chart | Card + Line Chart | PASS |
| 2 | Filter Dashboard | 9 | Filter Action (on-select, on-hover) | Cross-filter interactions | PASS |
| 3 | GoTo - Dashboard | 7 | Navigation between sheets | Page navigation button | PASS |
| 4 | Highlight Dashboard | 7 | Highlight + URL Actions | Cross-highlight + Web URL button | PASS |

## Action Detail Mapping

| # | Tableau Action | Type | Activation | Power BI Equivalent |
|---|---------------|------|------------|---------------------|
| 1 | Filter Action - Sheets | Filter | on-select | Edit Interactions > Filter |
| 2 | Filter Action - Dashboard | Filter | on-hover | Edit Interactions > Filter (on-click) |
| 3 | Highlight Action - Sheets | Highlight | on-select | Edit Interactions > Highlight |
| 4 | Highlight Action - Dashboard | Highlight | on-hover | Edit Interactions > Highlight (on-click) |
| 5 | Read More about Sub_Category | URL | click | Button > Web URL with DAX measure |

## Data Source Mapping

| TWB Source | CSV Files | Power BI Table |
|-----------|-----------|---------------|
| Small Data Source | Orders.csv, Orders_Archive.csv (union) | Orders |
| Small Data Source | Customers.csv | Customers |
| Small Data Source | Products.csv | Products |
| Parameter | Total (real, default=0) | Total Parameter |

## Artifacts Generated

- `dax_measures.dax` -- DAX measure definitions (5 calcs + 1 parameter + 1 URL measure)
- `model.tmdl` -- TMDL semantic model (Orders, Customers, Products, Total Parameter, Date)
- `layout.json` -- Power BI layout with 4 dashboard pages and action configurations
- `theme.json` -- Tableau 10 color palette, Segoe UI fonts
- `power_query.pq` -- Power Query M scripts for 5 tables
- `validation_report.md` -- This report

## Conversion Notes

- All Tableau calculated fields parsed from TWB XML and converted to DAX
- Original Tableau formulas preserved as comments in dax_measures.dax
- Parameter "Total" converted to What-If parameter using GENERATESERIES disconnected table
- 5 Tableau actions mapped to Power BI interaction equivalents
- On-hover activation noted as Power BI limitation -- converted to on-click
- URL action converted to DAX URL measure `Sub-Category URL`
- CSV delimiter: semicolon (;), encoding: UTF-8 (65001)
