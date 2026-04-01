# Section 07 - Renaming

> **Source**: `Section 7 - Renaming.twbx`
> **Extracted TWB**: `Section 7 - Renaming.twb`

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields | 3 |
| Parameters | 0 |
| Data Sources | 4 |
| Dashboards | 0 |
| Worksheets | 2 |

## Calculated Fields

| # | Name | Formula | Data Type | Role |
|---|------|---------|-----------|------|
| 1 | Category (Short) | `[Category]` | string | dimension |
| 2 | Logic 400 | `[Sales] < 400` | boolean | dimension |
| 3 | Country (Short) | `[Country]` | string | dimension |

## Data Sources

| # | Name | Connection Type | Tables/Files |
|---|------|----------------|--------------|
| 1 | Big Data Source | federated | Orders.csv, Customers.csv, Products.csv, Orders.csv_110301F4E5AB49989DD4872054A4FFED, Customers.csv_3C3F46320B514C9094F99AB28CF639A7 |
| 2 | Small Data Source | federated | Customers.csv, Customers_Details.csv, Orders.csv+, Orders.csv, Orders_Archive.csv |
| 3 | Small Data Source | unknown | - |
| 4 | Big Data Source | unknown | - |

## Worksheets

- Sheet 2
- Sheet 3

## Extracted Files

- `Data/TableauTemp/#TableauTemp_1kehhbv0ht1nhx19i48bi1a8690b.hyper`
- `Data/TableauTemp/#TableauTemp_1l6kvja1hyb4oq1b6xahy0c5xkvl.hyper`
- `Section 7 - Renaming.twb`
