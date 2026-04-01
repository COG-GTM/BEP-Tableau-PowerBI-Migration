# Section 12 - Table Calculations

> **Source**: `Section 12 - Table Calculations.twbx`
> **Extracted TWB**: `Section 12 - Table Calculations.twb`

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields | 14 |
| Parameters | 0 |
| Data Sources | 20 |
| Dashboards | 1 |
| Worksheets | 17 |

## Key Tableau Features Used

- Running calculations
- Rank calculations
- LOOKUP (table calculation)
- INDEX (table calculation)
- Null handling (ISNULL/ZN)

## Calculated Fields

| # | Name | Formula | Data Type | Role |
|---|------|---------|-----------|------|
| 1 | [Calculation1] | `ZN(SUM([Sales])) - LOOKUP(ZN(SUM([Sales])), -1)` | real | measure |
| 2 | [Calculation2] | `RUNNING_SUM(SUM([Sales]))` | real | measure |
| 3 | [Calculation3] | `RANK_PERCENTILE(SUM([Sales]))` | real | measure |
| 4 | [Calculation4] | `ZN(SUM([Sales])) - LOOKUP(ZN(SUM([Sales])), -1)` | real | measure |
| 5 | [Calculation1 1] | `(ZN([Calculation1]) - LOOKUP(ZN([Calculation1]), -1)) / ABS(LOOKUP(ZN([Calculation1]), -1))` | real | measure |
| 6 | [Calculation1] | `RUNNING_SUM(SUM([Sales]))` | real | measure |
| 7 | Calculation2 | `LAST()` | integer | measure |
| 8 | Lookup | `LOOKUP(SUM([Sales]),2)` | real | measure |
| 9 | First (Sales) | `IF FIRST() = 0 THEN SUM([Sales]) END` | real | measure |
| 10 | Rank (Sales) | `RANK(SUM([Sales]))` | integer | measure |
| 11 | Last | `LAST()` | integer | measure |
| 12 | First | `FIRST()` | integer | measure |
| 13 | Index | `INDEX()` | integer | measure |
| 14 | Running (Sales) | `RUNNING_SUM(SUM(Sales))` | real | measure |

## Data Sources

| # | Name | Connection Type | Tables/Files |
|---|------|----------------|--------------|
| 1 | Small Data Source | federated | Customers.csv, Customers_Details.csv, Orders.csv+, Orders.csv, Orders_Archive.csv |
| 2 | Big Data Source | federated | Orders.csv, Customers.csv, Products.csv, Orders.csv_5AF5F66F4EC84139B3533FCBFC0437BE, Customers.csv_90819B9BAE6E4CCA87ED07457EF68A05 |
| 3 | Big Data Source | unknown | - |
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
| 17 | Small Data Source | unknown | - |
| 18 | Big Data Source | unknown | - |
| 19 | Big Data Source | unknown | - |
| 20 | Big Data Source | unknown | - |

## Dashboards

- **Dashboard 1** (1020 x 860)

## Worksheets

- Compute Using
- Compute Using (2)
- Compute Using (3)
- Differences
- Differences (2)
- Differences (3)
- Differences (4)
- First as Referene Line
- Functions
- Rank
- Running Total
- Running Total (2)
- Running Total (3)
- Sales Comparision over Years
- Sheet 1
- Sheet 11
- Track the Progress of Customers and Orders

## Extracted Files

- `Data/TableauTemp/TEMP_04byq2k0nsfdvx186so260gs43bf.hyper`
- `Data/TableauTemp/TEMP_1h8q3r1137go0714b4pw01ksig1n.hyper`
- `Section 12 - Table Calculations.twb`
