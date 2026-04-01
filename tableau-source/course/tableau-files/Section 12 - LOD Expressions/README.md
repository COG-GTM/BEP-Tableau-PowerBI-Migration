# Section 12 - LOD Expressions

> **Source**: `LOD Expressions.twbx`
> **Extracted TWB**: `LOD Expressions.twb`

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields | 8 |
| Parameters | 0 |
| Data Sources | 5 |
| Dashboards | 0 |
| Worksheets | 3 |

## Key Tableau Features Used

- LOD FIXED expressions
- LOD INCLUDE expressions
- LOD EXCLUDE expressions

## Calculated Fields

| # | Name | Formula | Data Type | Role |
|---|------|---------|-----------|------|
| 1 | Sales By Category | `{ FIXED [Category] : SUM([Sales]) }` | real | measure |
| 2 | Sales Exclude Category | `{ EXCLUDE [Category] : SUM([Sales]) }` | real | measure |
| 3 | Calculation1 | `{ INCLUDE [First_Name] : SUM([Sales]) }` | real | measure |
| 4 | Avg Sales of Customers | `{ INCLUDE [First_Name] : SUM([Sales]) }` | real | measure |
| 5 | Nr. of Orders per Customer | `{ FIXED [Customer_ID]: COUNT([Order_ID]) }` | integer | measure |
| 6 | Sales of Tables | `IF [Sub_Category] = "Tables" THEN [Sales] END` | real | measure |
| 7 | Exclude Sub Category | `{ EXCLUDE [Sub_Category]: SUM([Calculation_1596526105595723802]) }` | real | measure |
| 8 | Difference | `SUM([Sales]) - SUM([Calculation_1596526105598066726])` | real | measure |

## Data Sources

| # | Name | Connection Type | Tables/Files |
|---|------|----------------|--------------|
| 1 | Small Data Source | federated | Customers.csv, Customers_Details.csv, Orders.csv+, Orders.csv, Orders_Archive.csv |
| 2 | Big Data Source | federated | Orders.csv, Customers.csv, Products.csv, Orders.csv_5AF5F66F4EC84139B3533FCBFC0437BE, Customers.csv_90819B9BAE6E4CCA87ED07457EF68A05 |
| 3 | Big Data Source | unknown | - |
| 4 | Big Data Source | unknown | - |
| 5 | Small Data Source | unknown | - |

## Worksheets

- Comparative Sales Analysis By Category
- Histogram - Customer Loyalty
- Sheet 5

## Extracted Files

- `Data/TableauTemp/TEMP_0b153ob16dzeur1dbtp1a0caq0a7.hyper`
- `Data/TableauTemp/TEMP_0h3u1jw0n7fmse1an8lb10huywvu.hyper`
- `LOD Expressions.twb`
