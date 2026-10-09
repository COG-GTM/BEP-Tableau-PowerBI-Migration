# Tableau workbook inventory: Sales & Customer Dashboards (Dynamic).twb

Built with Tableau 2023.2.0 (20232.23.0611.2007).

## Data
- `customers` — 793 rows, 2 columns → `data/customers.csv`
- `orders` — 9,994 rows, 13 columns → `data/orders.csv`
- `location` — 632 rows, 5 columns → `data/location.csv`
- `products` — 1,894 rows, 4 columns → `data/products.csv`

## Parameters
- **Select Year** (integer), default `2023`, values ['2020', '2021', '2022', '2023']

## Calculated fields (32)

| Name | Type | Tableau formula |
|---|---|---|
| % Diff Orders | real | `(COUNTD([CY Orders]) - COUNTD([PY Orders])) / COUNTD([PY Orders])` |
| % Diff Customers | real | `(COUNTD([CY Customers]) - COUNTD([PY Customers])) / COUNTD([PY Customers])` |
| % Diff Quantity | real | `(SUM([CY Quantity]) - SUM([PY Quantity])) / SUM([PY Quantity])` |
| % Diff Profit | real | `(SUM([CY Profit]) - SUM([PY Profit])) / SUM([CY Profit])` |
| % Diff Sales per Customers | real | `([CY Sales per Customer] - [PY Sales per Customer]) / [PY Sales per Customer]` |
| PY Customers | string | `IF YEAR([Order Date])= [Parameters].[Select Year]-1 THEN [Customer ID]  END` |
| CY Sales per Customer | real | `SUM([CY Sales]) / COUNTD([CY Customers])` |
| CY Quantity | integer | `IF YEAR([Order Date]) = [Parameters].[Select Year] THEN [Quantity] END` |
| CY Profit | real | `IF YEAR([Order Date]) = [Parameters].[Select Year] THEN [Profit] END` |
| CY Customers | string | `IF YEAR([Order Date])= [Parameters].[Select Year] THEN [Customer ID]  END` |
| CY Orders | string | `IF YEAR([Order Date]) = [Parameters].[Select Year] THEN [Order ID] END` |
| PY Sales | real | `IF YEAR([Order Date]) = [Parameters].[Select Year]-1 THEN [Sales] END` |
| PY Sales per Customer | real | `SUM([PY Sales]) / COUNTD([PY Customers])` |
| Current Year | integer | `[Parameters].[Select Year]` |
| Previous Year | integer | `[Parameters].[Select Year]-1` |
| KPI CY Less PY | string | `IF SUM([CY Sales]) < SUM([PY Sales]) THEN '⬤' ELSE '' END` |
| KPI Sales Avg | string | `IF SUM([CY Sales]) > WINDOW_AVG(SUM([CY Sales])) THEN 'Above' ELSE 'Below' END` |
| CY Sales | real | `IF YEAR([Order Date]) = [Parameters].[Select Year] THEN [Sales] END` |
| Order Date (Year) | integer | `YEAR([Order Date])` |
| % Diff Sales | real | `(SUM([CY Sales]) - SUM([PY Sales])) / SUM([PY Sales])` |
| Min/Max Sales | real | `IF SUM([CY Sales]) = WINDOW_MAX(SUM([CY Sales])) THEN SUM([CY Sales]) ELSEIF SUM([CY Sales]) = WINDOW_MIN(SUM([CY Sales])) THEN SUM([CY Sales]) END` |
| {SUM([CY Sales])} | real | `{SUM([CY Sales])}` |
| Nr of Orders per Customers | integer | `{ FIXED [CY Customers]: COUNTD([CY Orders])}` |
| KPI Profit Avg | string | `IF SUM([CY Profit]) > WINDOW_AVG(SUM([CY Profit])) THEN 'Above' ELSE 'Below' END` |
| Min/Max Sales Per Customers | real | `IF [CY Sales per Customer] = WINDOW_MAX([CY Sales per Customer]) THEN [CY Sales per Customer]  ELSEIF [CY Sales per Customer] = WINDOW_MIN([CY Sales per Customer]) THEN [CY Sales per Customer] END` |
| Min/Max Customers | integer | `IF COUNTD([CY Customers]) = WINDOW_MAX(COUNTD([CY Customers])) THEN COUNTD([CY Customers]) ELSEIF COUNTD([CY Customers]) = WINDOW_MIN(COUNTD([CY Customers])) THEN COUNTD([CY Customers]) END` |
| Min/Max Quantity | integer | `IF SUM([CY Quantity]) = WINDOW_MAX(SUM([CY Quantity])) THEN SUM([CY Quantity]) ELSEIF SUM([CY Quantity]) = WINDOW_MIN(SUM([CY Quantity])) THEN SUM([CY Quantity]) END` |
| Min/Max Profit | real | `IF SUM([CY Profit]) = WINDOW_MAX(SUM([CY Profit])) THEN SUM([CY Profit]) ELSEIF SUM([CY Profit]) = WINDOW_MIN(SUM([CY Profit])) THEN SUM([CY Profit]) END` |
| Min/Max Orders | integer | `IF COUNTD([CY Orders]) = WINDOW_MAX(COUNTD([CY Orders])) THEN COUNTD([CY Orders]) ELSEIF COUNTD([CY Orders]) = WINDOW_MIN(COUNTD([CY Orders])) THEN COUNTD([CY Orders]) END` |
| PY Quantity | integer | `IF YEAR([Order Date]) = [Parameters].[Select Year]-1 THEN [Quantity] END` |
| PY Profit | real | `IF YEAR([Order Date]) = [Parameters].[Select Year]-1 THEN [Profit] END` |
| PY Orders | string | `IF YEAR([Order Date]) = [Parameters].[Select Year]-1 THEN [Order ID] END` |

## Worksheets (15)

| Worksheet | Mark | Columns shelf | Rows shelf |
|---|---|---|---|
| Customer Distribution | Bar | `[Nr of Orders per Customers]` | `COUNTD([CY Customers])` |
| KPI Customers | Automatic | `MIN([Order Date])` | `([Multiple Values] + [Min/Max Customers])` |
| KPI Orders | Automatic | `MIN([Order Date])` | `([Multiple Values] + [Min/Max Orders])` |
| KPI Profit | Automatic | `MIN([Order Date])` | `([Multiple Values] + [Min/Max Profit])` |
| KPI Quantity | Automatic | `MIN([Order Date])` | `([Multiple Values] + [Min/Max Quantity])` |
| KPI Sales | Automatic | `MIN([Order Date])` | `([Multiple Values] + [Min/Max Sales])` |
| KPI Sales Per Customers | Automatic | `MIN([Order Date])` | `([Multiple Values] + [Min/Max Sales Per Customers])` |
| Legend KPI | Automatic | `` | `` |
| Legend Subcategory | Automatic | `` | `` |
| Subcategory Comparison | Bar | `(SUM([PY Sales]) + (SUM([CY Sales]) + SUM([CY Profit])))` | `([Sub-Category] / [KPI CY Less PY])` |
| Test KPI | Automatic | `[:Measure Names]` | `YEAR([Order Date])` |
| Test KPI2 | Automatic | `` | `[:Measure Names]` |
| Test Max Min | Automatic | `[:Measure Names]` | `MIN([Order Date])` |
| Top Customers | Automatic | `[:Measure Names]` | `([INDEX()] / ([Customer Name] / MAX([Order Date])))` |
| Weekly Trends | Automatic | `WEEK([Order Date])` | `(SUM([CY Sales]) + SUM([CY Profit]))` |

## Dashboards (2)
- **Customer Dashboard** (1200x800): Customer Distribution, KPI Customers, KPI Orders, KPI Sales Per Customers, Legend KPI, Top Customers
- **Sales Dashboard** (1200x800): KPI Profit, KPI Quantity, KPI Sales, Legend KPI, Legend Subcategory, Subcategory Comparison, Weekly Trends
