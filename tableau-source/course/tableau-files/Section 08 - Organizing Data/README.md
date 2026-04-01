# Section 08 - Organizing Data

> **Source**: `Section 8 - Organizing Data.twbx`
> **Extracted TWB**: `Section 8 - Organizing Data.twb`

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields | 5 |
| Parameters | 0 |
| Data Sources | 13 |
| Dashboards | 0 |
| Worksheets | 11 |

## Calculated Fields

| # | Name | Formula | Data Type | Role |
|---|------|---------|-----------|------|
| 1 | Category (Short) | `[Category]` | string | dimension |
| 2 | Sales (bin) | `[Sales]` | integer | dimension |
| 3 | Score (bin) | `[Score]` | integer | dimension |
| 4 | Logic 400 | `[Sales] < 400` | boolean | dimension |
| 5 | Country (Short) | `[Country]` | string | dimension |

## Data Sources

| # | Name | Connection Type | Tables/Files |
|---|------|----------------|--------------|
| 1 | Big Data Source | federated | Orders.csv, Customers.csv, Products.csv, Orders.csv_110301F4E5AB49989DD4872054A4FFED, Customers.csv_3C3F46320B514C9094F99AB28CF639A7 |
| 2 | Small Data Source | federated | Customers.csv, Customers_Details.csv, Orders.csv+, Orders.csv, Orders_Archive.csv |
| 3 | Big Data Source | unknown | - |
| 4 | Big Data Source | unknown | - |
| 5 | Big Data Source | unknown | - |
| 6 | Big Data Source | unknown | - |
| 7 | Small Data Source | unknown | - |
| 8 | Big Data Source | unknown | - |
| 9 | Big Data Source | unknown | - |
| 10 | Big Data Source | unknown | - |
| 11 | Big Data Source | unknown | - |
| 12 | Small Data Source | unknown | - |
| 13 | Big Data Source | unknown | - |

## Worksheets

- Cluster - Customers
- Cluster - Products
- Group - Continent
- Group - Customers
- Group - Customers (2)
- Hierarchy - Date
- Hierarchy - Location
- Histogram Sales
- Histogram Scores
- Sets - Customers
- Sets - High Performers

## Extracted Files

- `Data/TableauTemp/TEMP_04rany70dzgr3v1ewy36g1gqiuiy.hyper`
- `Data/TableauTemp/TEMP_0d7ptjb19t0bct1bkakgf1rvlphb.hyper`
- `Section 8 - Organizing Data.twb`
