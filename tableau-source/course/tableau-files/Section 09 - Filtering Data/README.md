# Section 09 - Filtering Data

> **Source**: `Section 9 - Filtering Data.twbx`
> **Extracted TWB**: `Section 9 - Filtering Data.twb`

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields | 5 |
| Parameters | 0 |
| Data Sources | 10 |
| Dashboards | 0 |
| Worksheets | 8 |

## Calculated Fields

| # | Name | Formula | Data Type | Role |
|---|------|---------|-----------|------|
| 1 | Logic 400 | `[Sales] < 400` | boolean | dimension |
| 2 | Country (Short) | `[Country]` | string | dimension |
| 3 | Category (Short) | `[Category]` | string | dimension |
| 4 | Sales (bin) | `[Sales]` | integer | dimension |
| 5 | Score (bin) | `[Score]` | integer | dimension |

## Data Sources

| # | Name | Connection Type | Tables/Files |
|---|------|----------------|--------------|
| 1 | Small Data Source | federated | Customers.csv, Customers_Details.csv, Orders.csv+, Orders.csv, Orders_Archive.csv |
| 2 | Big Data Source | federated | Orders.csv, Customers.csv, Products.csv, Orders.csv_110301F4E5AB49989DD4872054A4FFED, Customers.csv_3C3F46320B514C9094F99AB28CF639A7 |
| 3 | Big Data Source | unknown | - |
| 4 | Big Data Source | unknown | - |
| 5 | Big Data Source | unknown | - |
| 6 | Big Data Source | unknown | - |
| 7 | Big Data Source | unknown | - |
| 8 | Big Data Source | unknown | - |
| 9 | Big Data Source | unknown | - |
| 10 | Big Data Source | unknown | - |

## Worksheets

- Apply Filter
- Context Filter - Office Supplies
- Context Filter - Security Problem
- DataSouce Filter - Country
- DataSource Filter - Years
- Order
- Order2
- Tips & Tricks

## Extracted Files

- `Data/TableauTemp/#TableauTemp_1n7abki0r4vjjs17400pc1lx4qka.hyper`
- `Data/TableauTemp/TEMP_04rany70dzgr3v1ewy36g1gqiuiy.hyper`
- `Section 9 - Filtering Data.twb`
