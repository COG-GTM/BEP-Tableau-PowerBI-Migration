# Section 12 - Aggregate Calculations

> **Source**: `Section 11 -  Attribute.twbx`
> **Extracted TWB**: `Section 11 -  Attribute.twb`

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields | 7 |
| Parameters | 0 |
| Data Sources | 7 |
| Dashboards | 0 |
| Worksheets | 5 |

## Key Tableau Features Used

- COUNTD (distinct count)

## Calculated Fields

| # | Name | Formula | Data Type | Role |
|---|------|---------|-----------|------|
| 1 | Total Sales | `SUM([Sales])` | real | measure |
| 2 |  Avg. Sales | `AVG([Sales])` | real | measure |
| 3 | Nr. of Orders | `COUNT([Order_ID])` | integer | measure |
| 4 | Nr. Of Products | `COUNTD([Product_ID])` | integer | measure |
| 5 | Highest Sales | `MAX([Sales])` | real | measure |
| 6 | Lowest Sales | `MIN([Sales])` | real | measure |
| 7 | Attr(Postal Code) | `ATTR([Postal_Code])` | string | measure |

## Data Sources

| # | Name | Connection Type | Tables/Files |
|---|------|----------------|--------------|
| 1 | Small Data Source | federated | Customers.csv, Customers_Details.csv, Orders.csv+, Orders.csv, Orders_Archive.csv |
| 2 | Big Data Source | federated | Orders.csv, Customers.csv, Products.csv, Orders.csv_5AF5F66F4EC84139B3533FCBFC0437BE, Customers.csv_90819B9BAE6E4CCA87ED07457EF68A05 |
| 3 | Small Data Source | unknown | - |
| 4 | Small Data Source | unknown | - |
| 5 | Big Data Source | unknown | - |
| 6 | Big Data Source | unknown | - |
| 7 | Big Data Source | unknown | - |

## Worksheets

- Aggregate Calc
- Attr
- Attr (ToolTip)
- Sales By Postal Code
- Sheet 5

## Extracted Files

- `Data/TableauTemp/TEMP_0iouo9m1naecvi13s6kh90z4pm75.hyper`
- `Data/TableauTemp/TEMP_10ujyt50kzhho31a53fum1vejt7f.hyper`
- `Section 11 -  Attribute.twb`
