# Section 10 - Parameters

> **Source**: `Section 10 - Parameters.twbx`
> **Extracted TWB**: `Section 10 - Parameters.twb`

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields | 17 |
| Parameters | 5 |
| Data Sources | 6 |
| Dashboards | 0 |
| Worksheets | 4 |

## Key Tableau Features Used

- CASE/WHEN switching
- Parameters (5 defined)

## Calculated Fields

| # | Name | Formula | Data Type | Role |
|---|------|---------|-----------|------|
| 1 | Logic 400 | `[Sales] < 400` | boolean | dimension |
| 2 | Country (Short) | `[Country]` | string | dimension |
| 3 | KPI Colors | `If SUM([Profit]) < [Parameters].[Parameter 4] THEN 'Red' ELSE 'Green' END` | string | measure |
| 4 | Dynamic Dimension | `CASE [Parameters].[Parameter 1] WHEN 'Country' THEN [Country] WHEN 'Category' THEN [Category] END` | string | dimension |
| 5 | Dynamic Measure | `CASE [Parameters].[Parameter 2] WHEN 'Sales' THEN [Sales] WHEN 'Profit' THEN [Profit] WHEN 'Quantity' THEN [Quanti...` | real | measure |
| 6 | Category (Short) | `[Category]` | string | dimension |
| 7 | Sales (bin) | `[Sales]` | integer | dimension |
| 8 | Score (bin) | `[Score]` | integer | dimension |
| 9 | Choose Dimension | `"Country"` | string | measure |
| 10 | Choose Measure | `"Sales"` | string | measure |
| 11 | Choose Size of Bins | `20.` | real | measure |
| 12 | Choose Threshold | `10000` | integer | measure |
| 13 | Choose Dimension | `"Country"` | string | measure |
| 14 | Choose Measure | `"Sales"` | string | measure |
| 15 | Choose Size of Bins | `20.` | real | measure |
| 16 | Choose Threshold | `10000` | integer | measure |
| 17 | Choose Top N Products | `15` | integer | measure |

## Parameters

| # | Name | Data Type | Details |
|---|------|-----------|---------|
| 1 | Choose Dimension | string | Values: "Country", "Category" |
| 2 | Choose Measure | string | Values: "Sales", "Profit", "Quantity" |
| 3 | Choose Size of Bins | real | Range: 5.0-25.0 |
| 4 | Choose Threshold | integer | - |
| 5 | Choose Top N Products | integer | Range: 0-50 |

## Data Sources

| # | Name | Connection Type | Tables/Files |
|---|------|----------------|--------------|
| 1 | Small Data Source | federated | Customers.csv, Customers_Details.csv, Orders.csv+, Orders.csv, Orders_Archive.csv |
| 2 | Big Data Source | federated | Orders.csv, Customers.csv, Products.csv, Orders.csv_110301F4E5AB49989DD4872054A4FFED, Customers.csv_3C3F46320B514C9094F99AB28CF639A7 |
| 3 | Big Data Source | unknown | - |
| 4 | Big Data Source | unknown | - |
| 5 | Big Data Source | unknown | - |
| 6 | Big Data Source | unknown | - |

## Worksheets

- Parameters Swap Dimensions & Meausres
- Parameters in Bins
- Parameters in Calc & Reference Line
- Parameters in Filters

## Extracted Files

- `Data/TableauTemp/TEMP_0vpn5800cp41xw162pbt01xewzsj.hyper`
- `Data/TableauTemp/TEMP_197qc3x005h1ey1g3ggnt06hpxug.hyper`
- `Section 10 - Parameters.twb`
