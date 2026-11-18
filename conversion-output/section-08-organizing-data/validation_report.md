# Validation Report: Section 08 -- Organizing Data

> **Source**: `tableau-source/course/tableau-files/Section 08 - Organizing Data/extracted/Section 8 - Organizing Data.twb`
> **Output**: `conversion-output/section-08-organizing-data/`
> **Date**: 2026-04-01
> **Status**: CONVERTED

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields Converted | 5 |
| Parameters Converted | 0 |
| Groups Documented | 5 (Continent, Customer Group, Customer Clusters, Product Classes, Product Clusters) |
| Sets Documented | 5 (Customers Set, Set1-Fixed, Set2-Condition, Set3-Rank, Set4-Combined) |
| Hierarchies Converted | 2 (Location Hierarchy, Product Hierarchy) |
| Bins Converted | 2 (Sales bin, Score bin) |
| Worksheets Mapped | 11 |
| Validation Status | PASS |

## Measure Validation Details

| # | Measure Name | Tableau Formula | DAX Equivalent | Status |
|---|-------------|-----------------|----------------|--------|
| 1 | Category (Short) | `[Category]` (alias: F->Furniture, O->Office Supplies, T->Technology) | `SWITCH(SELECTEDVALUE(Orders[Category]), ...)` | PASS |
| 2 | Country (Short) | `[Country]` (alias: FR->France, DE->Germany) | `SWITCH(SELECTEDVALUE(Orders[Country]), ...)` | PASS |
| 3 | Sales (bin) | `[Sales]` (bin, class=bin, auto-sized, peg=0) | `INT(Orders[Sales] / 100) * 100` | PASS |
| 4 | Score (bin) | `[Score]` (bin, class=bin, auto-sized, peg=0) | `INT(Orders[Score] / 10) * 10` | PASS |
| 5 | Logic 400 | `[Sales] < 400` (boolean) | `IF(SUM(Orders[Sales]) < 400, TRUE(), FALSE())` | PASS |

## Feature Conversion Details

### Groups (TWB: class=categorical-bin)
| Group | TWB Column | Notes |
|-------|-----------|-------|
| Continent | `[Continent]` | Categorical-bin grouping countries into continents |
| Customer Group | `[Customer ID (Customers.csv) (group)]` | Manual group on Customer ID |
| Customer Clusters | `[Customer ID (Customers.csv) (clusters)]` | Clustering output |
| Product Classes | `[Product Name (group)]` | Manual group on Product Name |
| Product Clusters | `[Product Name (clusters) (1)]` | Clustering output |

### Sets (TWB: group elements with set semantics)
| Set | TWB Group | Members/Type |
|-----|----------|-------------|
| Customers Set | `[Customer ID (Customers.csv) Set]` | Fixed: 33 IDs (9,11,48,...,760) |
| Set1 - Fixed | caption="Set1 - Fixed" | Fixed: 2 IDs (2, 5) |
| Set2 - Condition | caption="Set2 - Condition" | Condition-based |
| Set3 - Rank | caption="Set3 - Rank" | Rank-based |
| Set4 - Combined | caption="Set4 - Combined" | Combination of Set1 + Set2 |

### Hierarchies (TWB: drill-path)
| Hierarchy | Levels |
|-----------|--------|
| Location Hierarchy | Country > City > Postal Code |
| Product Hierarchy | Category > Sub-Category > Product Name > Product ID |

### Bins (TWB: class=bin)
| Bin | Source Field | Size | Peg |
|-----|------------|------|-----|
| Sales (bin) | `[Sales]` | auto | 0 |
| Score (bin) | `[Score]` | auto | 0 |

## Worksheets Mapped to Power BI Visuals

| # | Tableau Worksheet | Power BI Visual Type |
|---|------------------|---------------------|
| 1 | Cluster - Customers | clusteredBarChart |
| 2 | Cluster - Products | lineChart |
| 3 | Group - Continent | table |
| 4 | Group - Customers | clusteredBarChart |
| 5 | Group - Customers (2) | lineChart |
| 6 | Hierarchy - Date | table |
| 7 | Hierarchy - Location | table |
| 8 | Histogram Sales | clusteredColumnChart |
| 9 | Histogram Scores | clusteredColumnChart |
| 10 | Sets - Customers | table |
| 11 | Sets - High Performers | clusteredBarChart |

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

- `dax_measures.dax` -- DAX measure definitions with original Tableau formulas as comments
- `model.tmdl` -- TMDL semantic model with hierarchies
- `layout.json` -- Power BI layout specification (2 pages, 11 visuals)
- `theme.json` -- Power BI theme with Tableau 10 color palette
- `power_query.pq` -- Power Query M scripts for CSV import
- `validation_report.md` -- This report
