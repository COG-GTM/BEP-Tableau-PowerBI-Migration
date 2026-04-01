# Section 13 - Tableau 63 Charts

> **Source**: `Tableau Charts  60 Visuals Without Format.twbx`
> **Extracted TWB**: `Tableau Charts  60 Visuals Without Format.twb`

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields | 15 |
| Parameters | 3 |
| Data Sources | 64 |
| Dashboards | 8 |
| Worksheets | 61 |

## Key Tableau Features Used

- LOD FIXED expressions
- Parameters (3 defined)

## Calculated Fields

| # | Name | Formula | Data Type | Role |
|---|------|---------|-----------|------|
| 1 | Select Country | `"USA"` | string | measure |
| 2 | Select Discount | `0.18` | real | measure |
| 3 | Select Profit Ratio | `0.1` | real | measure |
| 4 | Highlighted Country | `[Country] = [Parameters].[Parameter 1]` | boolean | dimension |
| 5 | Sales 2021 | `IF YEAR([Order_Date]) = 2021 THEN [Sales] END` | real | measure |
| 6 | Sales 2022 | `IF YEAR([Order_Date]) = 2022 THEN [Sales] END` | real | measure |
| 7 | Nr of Orders per Customer | `{ FIXED [Customer_ID] : COUNT([Order_ID])}` | integer | dimension |
| 8 | Profit Ratio | `SUM([Profit])/ SUM([Sales])` | real | measure |
| 9 | Quadrant Color | `IF [Calculation_2330612859080679425] >= [Parameters].[Parameter 3] AND AVG([Discount]) >= [Parameters].[Parameter 2]...` | string | measure |
| 10 | KPI Colors | `IF SUM([Sales]) > 50000 THEN "Green" ELSEIF  SUM([Sales]) <= 50000 AND SUM([Sales]) > 10000 THEN "Orange" ELSE "Red...` | string | measure |
| 11 | KPI Colors of Two Years | `IF SUM([Calculation_1361775988060233740]) >= SUM([Calculation_1361775988059799563]) THEN "Green" ELSE "Red" END` | string | measure |
| 12 | Quantity (bin) | `[Quantity]` | integer | dimension |
| 13 | Select Country | `"USA"` | string | measure |
| 14 | Select Discount | `0.18` | real | measure |
| 15 | Select Profit Ratio | `0.1` | real | measure |

## Parameters

| # | Name | Data Type | Details |
|---|------|-----------|---------|
| 1 | Select Country | string | Values: "France", "Germany", "Italy", "USA" |
| 2 | Select Discount | real | - |
| 3 | Select Profit Ratio | real | - |

## Data Sources

| # | Name | Connection Type | Tables/Files |
|---|------|----------------|--------------|
| 1 | Small Data Source | federated | Customers.csv, Customers_Details.csv, Orders.csv+, Orders.csv, Orders_Archive.csv |
| 2 | Big Data Source | federated | Orders.csv, Customers.csv, Products.csv, Orders.csv_5AF5F66F4EC84139B3533FCBFC0437BE, Customers.csv_90819B9BAE6E4CCA87ED07457EF68A05 |
| 3 | USA Sales | federated | USA Sales.csv, Extract |
| 4 | Big Data Source | unknown | - |
| 5 | Big Data Source | unknown | - |
| 6 | Big Data Source | unknown | - |
| 7 | Big Data Source | unknown | - |
| 8 | Big Data Source | unknown | - |
| 9 | Big Data Source | unknown | - |
| 10 | Big Data Source | unknown | - |
| 11 | Big Data Source | unknown | - |
| 12 | Big Data Source | unknown | - |
| 13 | Big Data Source | unknown | - |
| 14 | Big Data Source | unknown | - |
| 15 | Big Data Source | unknown | - |
| 16 | Big Data Source | unknown | - |
| 17 | Big Data Source | unknown | - |
| 18 | Big Data Source | unknown | - |
| 19 | Big Data Source | unknown | - |
| 20 | Big Data Source | unknown | - |
| 21 | Big Data Source | unknown | - |
| 22 | Big Data Source | unknown | - |
| 23 | Big Data Source | unknown | - |
| 24 | Big Data Source | unknown | - |
| 25 | Big Data Source | unknown | - |
| 26 | Big Data Source | unknown | - |
| 27 | Big Data Source | unknown | - |
| 28 | Big Data Source | unknown | - |
| 29 | Big Data Source | unknown | - |
| 30 | Big Data Source | unknown | - |
| 31 | Big Data Source | unknown | - |
| 32 | Big Data Source | unknown | - |
| 33 | Big Data Source | unknown | - |
| 34 | Big Data Source | unknown | - |
| 35 | Big Data Source | unknown | - |
| 36 | Big Data Source | unknown | - |
| 37 | Big Data Source | unknown | - |
| 38 | Big Data Source | unknown | - |
| 39 | Big Data Source | unknown | - |
| 40 | Big Data Source | unknown | - |
| 41 | Big Data Source | unknown | - |
| 42 | USA Sales | unknown | - |
| 43 | USA Sales | unknown | - |
| 44 | USA Sales | unknown | - |
| 45 | USA Sales | unknown | - |
| 46 | Big Data Source | unknown | - |
| 47 | Big Data Source | unknown | - |
| 48 | Big Data Source | unknown | - |
| 49 | Big Data Source | unknown | - |
| 50 | Big Data Source | unknown | - |
| 51 | Big Data Source | unknown | - |
| 52 | Big Data Source | unknown | - |
| 53 | Big Data Source | unknown | - |
| 54 | Big Data Source | unknown | - |
| 55 | Big Data Source | unknown | - |
| 56 | Big Data Source | unknown | - |
| 57 | Big Data Source | unknown | - |
| 58 | Big Data Source | unknown | - |
| 59 | Big Data Source | unknown | - |
| 60 | Big Data Source | unknown | - |
| 61 | Big Data Source | unknown | - |
| 62 | Big Data Source | unknown | - |
| 63 | Big Data Source | unknown | - |
| 64 | Big Data Source | unknown | - |

## Dashboards

- **Bar Charts** (auto x auto)
- **Change over Time** (auto x auto)
- **Correlation** (auto x auto)
- **Distribution** (auto x auto)
- **Magnitude** (auto x auto)
- **Part to Whole** (auto x auto)
- **Ranking** (auto x auto)
- **Spatial** (auto x auto)

## Worksheets

- Area
- Area & Line
- BANS
- Bar & Avg Line
- Bar (Columns)
- Bar (Rows)
- Bar (Side By Side)
- Bar Over Time
- Bar in Bar
- Barbell
- Barcode
- Bars & Line Dual Axis
- Box Plot
- Bubble
- Bullet
- Bump
- Butterfly (Method 1)
- Butterfly (Method 2)
- Calender
- Cricle Timeline
- Cumulative Line
- Donut
- Dot Plot
- Dual-Line
- Full Stacked Area
- Full Stacked Bar
- Funnel
- Heatmap
- Highlighted Line 1
- Highlighted Line 2
- Histogram 1 Measure
- Histogram 2 Measures
- KPI
- KPI & Bar
- Line
- Line (Visuals)
- Lollipop (H)
- Lollipop (V)
- Map Basic
- Map Night Vision
- Map with Symbols
- Map without Background
- Multiple Line
- Pareto (Method 1) 
- Pareto (method2)
- Pie
- Progress Bar
- Quadrant  (Dynamic)
- Rounded Bar
- Scatter Plots (Customized)
- Scatter plots
- Slope
- Small Multi-Area
- Small Multi-Bars
- Small Multi-Line
- Sparkline
- Stacked Area
- Stacked Bar
- Stacked Bubble
- Treemap
- Waterfall

## Extracted Files

- `Data/TableauTemp/TEMP_09x4jt908j348716ewqhk1ual5xz.hyper`
- `Data/TableauTemp/TEMP_0wf2mlu065fvxv1cr85ba0rpmh0m.hyper`
- `Data/TableauTemp/TEMP_0wrnvmv192tt7h1fd2evp0cy765o.hyper`
- `Tableau Charts  60 Visuals Without Format.twb`
