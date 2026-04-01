# Section 15 - Tableau Sales & Customer Dashboards

> **Source**: `Sales & Customer Dashboards (Dynamic).twbx`
> **Extracted TWB**: `Sales & Customer Dashboards (Dynamic).twb`

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields | 34 |
| Parameters | 1 |
| Data Sources | 19 |
| Dashboards | 2 |
| Worksheets | 15 |

## Key Tableau Features Used

- LOD FIXED expressions
- Window calculations
- COUNTD (distinct count)
- Parameters (1 defined)

## Calculated Fields

| # | Name | Formula | Data Type | Role |
|---|------|---------|-----------|------|
| 1 | Select Year | `2023` | integer | measure |
| 2 | % Diff Orders | `(COUNTD([CY Sales (copy)_3221481164594982929]) - COUNTD([PY Sales (copy)_3221481164594888720])) / COUNTD([PY Sales (c...` | real | measure |
| 3 | % Diff Customers | `(COUNTD([CY Sales (copy)_3221481164532666369]) - COUNTD([CY Customers (copy)_3221481164533411843])) / COUNTD([CY Cust...` | real | measure |
| 4 | % Diff Quantity | `(SUM([CY Sales (copy) (copy)_237846410424193025]) - SUM([PY Sales (copy) (copy)_237846410424823811])) / SUM([PY Sales...` | real | measure |
| 5 | % Diff Profit | `(SUM([CY Sales (copy)_237846410424180736]) - SUM([PY Sales (copy)_237846410424815618])) / SUM([CY Sales (copy)_237846...` | real | measure |
| 6 | % Diff Sales per Customers | `([CY Profit (copy)_3221481164532895746] - [CY Sales per Customer (copy)_3221481164533485572]) / [CY Sales per Custome...` | real | measure |
| 7 | PY Customers | `IF YEAR([Order Date])= [Parameters].[Parameter 1]-1 THEN [Customer ID]  END` | string | dimension |
| 8 | CY Sales per Customer | `SUM([Calculation_721701895334993921]) / COUNTD([CY Sales (copy)_3221481164532666369])` | real | measure |
| 9 | CY Quantity | `IF YEAR([Order Date]) = [Parameters].[Parameter 1] THEN [Quantity] END` | integer | measure |
| 10 | CY Profit | `IF YEAR([Order Date]) = [Parameters].[Parameter 1] THEN [Profit] END` | real | measure |
| 11 | CY Customers | `IF YEAR([Order Date])= [Parameters].[Parameter 1] THEN [Customer ID]  END` | string | dimension |
| 12 | CY Orders | `IF YEAR([Order Date]) = [Parameters].[Parameter 1] THEN [Order ID] END` | string | dimension |
| 13 | PY Sales | `IF YEAR([Order Date]) = [Parameters].[Parameter 1]-1 THEN [Sales] END` | real | measure |
| 14 | PY Sales per Customer | `SUM([CY Sales (copy)_721701895335804930]) / COUNTD([CY Customers (copy)_3221481164533411843])` | real | measure |
| 15 | Current Year | `[Parameters].[Parameter 1]` | integer | dimension |
| 16 | Previous Year | `[Parameters].[Parameter 1]-1` | integer | dimension |
| 17 | KPI CY Less PY | `IF SUM([Calculation_721701895334993921]) < SUM([CY Sales (copy)_721701895335804930]) THEN '⬤' ELSE '' END` | string | measure |
| 18 | KPI Sales Avg | `IF SUM([Calculation_721701895334993921]) > WINDOW_AVG(SUM([Calculation_721701895334993921])) THEN 'Above' ELSE 'Bel...` | string | measure |
| 19 | CY Sales | `IF YEAR([Order Date]) = [Parameters].[Parameter 1] THEN [Sales] END` | real | measure |
| 20 | Order Date (Year) | `YEAR([Order Date])` | integer | measure |
| 21 | % Diff Sales | `(SUM([Calculation_721701895334993921]) - SUM([CY Sales (copy)_721701895335804930])) / SUM([CY Sales (copy)_7217018953...` | real | measure |
| 22 | Min/Max Sales | `IF SUM([Calculation_721701895334993921]) = WINDOW_MAX(SUM([Calculation_721701895334993921])) THEN SUM([Calculation_7...` | real | measure |
| 23 | {SUM([CY Sales])} | `{SUM([Calculation_721701895334993921])}` | real | measure |
| 24 | Nr of Orders per Customers | `{ FIXED [CY Sales (copy)_3221481164532666369]: COUNTD([CY Sales (copy)_3221481164594982929])}` | integer | dimension |
| 25 | KPI Profit Avg | `IF SUM([CY Sales (copy)_237846410424180736]) > WINDOW_AVG(SUM([CY Sales (copy)_237846410424180736])) THEN 'Above' E...` | string | measure |
| 26 | Min/Max Sales Per Customers | `IF [CY Profit (copy)_3221481164532895746] = WINDOW_MAX([CY Profit (copy)_3221481164532895746]) THEN [CY Profit (copy...` | real | measure |
| 27 | Min/Max Customers | `IF COUNTD([CY Sales (copy)_3221481164532666369]) = WINDOW_MAX(COUNTD([CY Sales (copy)_3221481164532666369])) THEN CO...` | integer | measure |
| 28 | Min/Max Quantity | `IF SUM([CY Sales (copy) (copy)_237846410424193025]) = WINDOW_MAX(SUM([CY Sales (copy) (copy)_237846410424193025])) T...` | integer | measure |
| 29 | Min/Max Profit | `IF SUM([CY Sales (copy)_237846410424180736]) = WINDOW_MAX(SUM([CY Sales (copy)_237846410424180736])) THEN SUM([CY Sa...` | real | measure |
| 30 | Min/Max Orders | `IF COUNTD([CY Sales (copy)_3221481164594982929]) = WINDOW_MAX(COUNTD([CY Sales (copy)_3221481164594982929])) THEN CO...` | integer | measure |
| 31 | PY Quantity | `IF YEAR([Order Date]) = [Parameters].[Parameter 1]-1 THEN [Quantity] END` | integer | measure |
| 32 | PY Profit | `IF YEAR([Order Date]) = [Parameters].[Parameter 1]-1 THEN [Profit] END` | real | measure |
| 33 | PY Orders | `IF YEAR([Order Date]) = [Parameters].[Parameter 1]-1 THEN [Order ID] END` | string | dimension |
| 34 | Select Year | `2023` | integer | measure |

## Parameters

| # | Name | Data Type | Details |
|---|------|-----------|---------|
| 1 | Select Year | integer | Values: 2020, 2021, 2022, 2023 |

## Data Sources

| # | Name | Connection Type | Tables/Files |
|---|------|----------------|--------------|
| 1 | Sales DataSource | federated | Orders.csv, Customers.csv, Location.csv, Products.csv, Orders.csv_905AF3F5FECA431C80766E0C0C188760 |
| 2 | Sales DataSource | unknown | - |
| 3 | Sales DataSource | unknown | - |
| 4 | Sales DataSource | unknown | - |
| 5 | Sales DataSource | unknown | - |
| 6 | Sales DataSource | unknown | - |
| 7 | Sales DataSource | unknown | - |
| 8 | Sales DataSource | unknown | - |
| 9 | Sales DataSource | unknown | - |
| 10 | Sales DataSource | unknown | - |
| 11 | Sales DataSource | unknown | - |
| 12 | Sales DataSource | unknown | - |
| 13 | Sales DataSource | unknown | - |
| 14 | Sales DataSource | unknown | - |
| 15 | Sales DataSource | unknown | - |
| 16 | Sales DataSource | unknown | - |
| 17 | Sales DataSource | unknown | - |
| 18 | Sales DataSource | unknown | - |
| 19 | Sales DataSource | unknown | - |

## Dashboards

- **Customer Dashboard** (1200 x 800)
- **Sales Dashboard** (1200 x 800)

## Worksheets

- Customer Distribution
- KPI Customers
- KPI Orders
- KPI Profit
- KPI Quantity
- KPI Sales
- KPI Sales Per Customers
- Legend KPI
- Legend Subcategory
- Subcategory Comparison
- Test KPI
- Test KPI2
- Test Max Min
- Top Customers
- Weekly Trends

## Extracted Files

- `Data/TableauTemp/TEMP_04vakal12v7oho11kzm3i0iycqjo.hyper`
- `Image/Icon - Customer Dashboard (active).png`
- `Image/Icon - Customer Dashboard.png`
- `Image/Icon - Filter Hidden.png`
- `Image/Icon - Filter Shown.png`
- `Image/Icon - Logo.png`
- `Image/Icon - Sales Dashboard(active).png`
- `Image/Icon - Sales Dashboard.png`
- `Sales & Customer Dashboards (Dynamic).twb`
