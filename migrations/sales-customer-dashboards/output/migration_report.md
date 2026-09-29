# Tableau migration report: Sales & Customer Dashboards

## Tables and extracted rows

| Table | Hyper table | Rows | Columns |
|---|---|---:|---:|
| Customers | `Customers.csv_6DC64CBD7A91476C8367C3011943FE6B` | 793 | 2 |
| Location | `Location.csv_DF4EAC7E83794D459E9117839A9D605A` | 630 | 5 |
| Orders | `Orders.csv_905AF3F5FECA431C80766E0C0C188760` | 9994 | 13 |
| Products | `Products.csv_62ED95945D1146228C3236829E70736C` | 1862 | 4 |

## Relationships

- `Orders.Customer ID` → `Customers.Customer ID`
- `Orders.Postal Code` → `Location.Postal Code`
- `Orders.Product ID` → `Products.Product ID`

## Calculations

| Caption | Class | Status | DAX / reason |
|---|---|---|---|
| % Diff Orders | aggregate | supported | `DIVIDE((COUNTROWS(FILTER(DISTINCT(SELECTCOLUMNS('Orders', "__v", IF((YEAR('Orders'[Order Date]) = SELECTEDVALUE('Select Year'[Select Year], 2023)), 'Orders'[Order ID]))), NOT ISBLANK([__v]))) - COUNTROWS(FILTER(DISTINCT(SELECTCOLUMNS('Orders', "__v", IF((YEAR('Orders'[Order Date]) = (SELECTEDVALUE('Select Year'[Select Year], 2023) - 1)), 'Orders'[Order ID]))), NOT ISBLANK([__v])))), COUNTROWS(FILTER(DISTINCT(SELECTCOLUMNS('Orders', "__v", IF((YEAR('Orders'[Order Date]) = (SELECTEDVALUE('Select Year'[Select Year], 2023) - 1)), 'Orders'[Order ID]))), NOT ISBLANK([__v]))))` |
| % Diff Customers | aggregate | supported | `DIVIDE((COUNTROWS(FILTER(DISTINCT(SELECTCOLUMNS('Orders', "__v", IF((YEAR('Orders'[Order Date]) = SELECTEDVALUE('Select Year'[Select Year], 2023)), 'Orders'[Customer ID]))), NOT ISBLANK([__v]))) - COUNTROWS(FILTER(DISTINCT(SELECTCOLUMNS('Orders', "__v", IF((YEAR('Orders'[Order Date]) = (SELECTEDVALUE('Select Year'[Select Year], 2023) - 1)), 'Orders'[Customer ID]))), NOT ISBLANK([__v])))), COUNTROWS(FILTER(DISTINCT(SELECTCOLUMNS('Orders', "__v", IF((YEAR('Orders'[Order Date]) = (SELECTEDVALUE('Select Year'[Select Year], 2023) - 1)), 'Orders'[Customer ID]))), NOT ISBLANK([__v]))))` |
| % Diff Quantity | aggregate | supported | `DIVIDE((SUMX('Orders', IF((YEAR('Orders'[Order Date]) = SELECTEDVALUE('Select Year'[Select Year], 2023)), 'Orders'[Quantity])) - SUMX('Orders', IF((YEAR('Orders'[Order Date]) = (SELECTEDVALUE('Select Year'[Select Year], 2023) - 1)), 'Orders'[Quantity]))), SUMX('Orders', IF((YEAR('Orders'[Order Date]) = (SELECTEDVALUE('Select Year'[Select Year], 2023) - 1)), 'Orders'[Quantity])))` |
| % Diff Profit | aggregate | supported | `DIVIDE((SUMX('Orders', IF((YEAR('Orders'[Order Date]) = SELECTEDVALUE('Select Year'[Select Year], 2023)), 'Orders'[Profit])) - SUMX('Orders', IF((YEAR('Orders'[Order Date]) = (SELECTEDVALUE('Select Year'[Select Year], 2023) - 1)), 'Orders'[Profit]))), SUMX('Orders', IF((YEAR('Orders'[Order Date]) = SELECTEDVALUE('Select Year'[Select Year], 2023)), 'Orders'[Profit])))` |
| % Diff Sales per Customers | aggregate | supported | `DIVIDE(([CY Sales per Customer] - [PY Sales per Customer]), [PY Sales per Customer])` |
| PY Customers | row | supported | `IF((YEAR('Orders'[Order Date]) = (SELECTEDVALUE('Select Year'[Select Year], 2023) - 1)), 'Orders'[Customer ID])` |
| CY Sales per Customer | aggregate | supported | `DIVIDE(SUMX('Orders', IF((YEAR('Orders'[Order Date]) = SELECTEDVALUE('Select Year'[Select Year], 2023)), 'Orders'[Sales])), COUNTROWS(FILTER(DISTINCT(SELECTCOLUMNS('Orders', "__v", IF((YEAR('Orders'[Order Date]) = SELECTEDVALUE('Select Year'[Select Year], 2023)), 'Orders'[Customer ID]))), NOT ISBLANK([__v]))))` |
| CY Quantity | row | supported | `IF((YEAR('Orders'[Order Date]) = SELECTEDVALUE('Select Year'[Select Year], 2023)), 'Orders'[Quantity])` |
| CY Profit | row | supported | `IF((YEAR('Orders'[Order Date]) = SELECTEDVALUE('Select Year'[Select Year], 2023)), 'Orders'[Profit])` |
| CY Customers | row | supported | `IF((YEAR('Orders'[Order Date]) = SELECTEDVALUE('Select Year'[Select Year], 2023)), 'Orders'[Customer ID])` |
| CY Orders | row | supported | `IF((YEAR('Orders'[Order Date]) = SELECTEDVALUE('Select Year'[Select Year], 2023)), 'Orders'[Order ID])` |
| PY Sales | row | supported | `IF((YEAR('Orders'[Order Date]) = (SELECTEDVALUE('Select Year'[Select Year], 2023) - 1)), 'Orders'[Sales])` |
| PY Sales per Customer | aggregate | supported | `DIVIDE(SUMX('Orders', IF((YEAR('Orders'[Order Date]) = (SELECTEDVALUE('Select Year'[Select Year], 2023) - 1)), 'Orders'[Sales])), COUNTROWS(FILTER(DISTINCT(SELECTCOLUMNS('Orders', "__v", IF((YEAR('Orders'[Order Date]) = (SELECTEDVALUE('Select Year'[Select Year], 2023) - 1)), 'Orders'[Customer ID]))), NOT ISBLANK([__v]))))` |
| Current Year | row | supported | `SELECTEDVALUE('Select Year'[Select Year], 2023)` |
| Previous Year | row | supported | `(SELECTEDVALUE('Select Year'[Select Year], 2023) - 1)` |
| KPI CY Less PY | aggregate | supported | `IF((SUMX('Orders', IF((YEAR('Orders'[Order Date]) = SELECTEDVALUE('Select Year'[Select Year], 2023)), 'Orders'[Sales])) < SUMX('Orders', IF((YEAR('Orders'[Order Date]) = (SELECTEDVALUE('Select Year'[Select Year], 2023) - 1)), 'Orders'[Sales]))), "⬤", "")` |
| KPI Sales Avg | table_calc | table_calc | `` |
| CY Sales | row | supported | `IF((YEAR('Orders'[Order Date]) = SELECTEDVALUE('Select Year'[Select Year], 2023)), 'Orders'[Sales])` |
| Order Date (Year) | row | supported | `YEAR('Orders'[Order Date])` |
| % Diff Sales | aggregate | supported | `DIVIDE((SUMX('Orders', IF((YEAR('Orders'[Order Date]) = SELECTEDVALUE('Select Year'[Select Year], 2023)), 'Orders'[Sales])) - SUMX('Orders', IF((YEAR('Orders'[Order Date]) = (SELECTEDVALUE('Select Year'[Select Year], 2023) - 1)), 'Orders'[Sales]))), SUMX('Orders', IF((YEAR('Orders'[Order Date]) = (SELECTEDVALUE('Select Year'[Select Year], 2023) - 1)), 'Orders'[Sales])))` |
| Min/Max Sales | table_calc | table_calc | `` |
| {SUM([CY Sales])} | lod | supported (semantics approximated) | `CALCULATE(SUMX('Orders', IF((YEAR('Orders'[Order Date]) = SELECTEDVALUE('Select Year'[Select Year], 2023)), 'Orders'[Sales])), REMOVEFILTERS())` |
| Nr of Orders per Customers | lod | needs_override | `` |
| KPI Profit Avg | table_calc | table_calc | `` |
| Min/Max Sales Per Customers | table_calc | table_calc | `` |
| Min/Max Customers | table_calc | table_calc | `` |
| Min/Max Quantity | table_calc | table_calc | `` |
| Min/Max Profit | table_calc | table_calc | `` |
| Min/Max Orders | table_calc | table_calc | `` |
| PY Quantity | row | supported | `IF((YEAR('Orders'[Order Date]) = (SELECTEDVALUE('Select Year'[Select Year], 2023) - 1)), 'Orders'[Quantity])` |
| PY Profit | row | supported | `IF((YEAR('Orders'[Order Date]) = (SELECTEDVALUE('Select Year'[Select Year], 2023) - 1)), 'Orders'[Profit])` |
| PY Orders | row | supported | `IF((YEAR('Orders'[Order Date]) = (SELECTEDVALUE('Select Year'[Select Year], 2023) - 1)), 'Orders'[Order ID])` |
| Select Year | row | supported | `2023` |

## Auto measures

- **CNTD CY Customers**: `COUNTROWS(FILTER(DISTINCT(SELECTCOLUMNS('Orders', "__v", IF((YEAR('Orders'[Order Date]) = SELECTEDVALUE('Select Year'[Select Year], 2023)), 'Orders'[Customer ID]))), NOT ISBLANK([__v])))`
- **MIN Order Date**: `MIN('Orders'[Order Date])`
- **CNTD PY Customers**: `COUNTROWS(FILTER(DISTINCT(SELECTCOLUMNS('Orders', "__v", IF((YEAR('Orders'[Order Date]) = (SELECTEDVALUE('Select Year'[Select Year], 2023) - 1)), 'Orders'[Customer ID]))), NOT ISBLANK([__v])))`
- **CNTD CY Orders**: `COUNTROWS(FILTER(DISTINCT(SELECTCOLUMNS('Orders', "__v", IF((YEAR('Orders'[Order Date]) = SELECTEDVALUE('Select Year'[Select Year], 2023)), 'Orders'[Order ID]))), NOT ISBLANK([__v])))`
- **CNTD PY Orders**: `COUNTROWS(FILTER(DISTINCT(SELECTCOLUMNS('Orders', "__v", IF((YEAR('Orders'[Order Date]) = (SELECTEDVALUE('Select Year'[Select Year], 2023) - 1)), 'Orders'[Order ID]))), NOT ISBLANK([__v])))`
- **CY Profit**: `SUMX('Orders', IF((YEAR('Orders'[Order Date]) = SELECTEDVALUE('Select Year'[Select Year], 2023)), 'Orders'[Profit]))`
- **PY Profit**: `SUMX('Orders', IF((YEAR('Orders'[Order Date]) = (SELECTEDVALUE('Select Year'[Select Year], 2023) - 1)), 'Orders'[Profit]))`
- **CY Quantity**: `SUMX('Orders', IF((YEAR('Orders'[Order Date]) = SELECTEDVALUE('Select Year'[Select Year], 2023)), 'Orders'[Quantity]))`
- **PY Quantity**: `SUMX('Orders', IF((YEAR('Orders'[Order Date]) = (SELECTEDVALUE('Select Year'[Select Year], 2023) - 1)), 'Orders'[Quantity]))`
- **CY Sales**: `SUMX('Orders', IF((YEAR('Orders'[Order Date]) = SELECTEDVALUE('Select Year'[Select Year], 2023)), 'Orders'[Sales]))`
- **PY Sales**: `SUMX('Orders', IF((YEAR('Orders'[Order Date]) = (SELECTEDVALUE('Select Year'[Select Year], 2023) - 1)), 'Orders'[Sales]))`
- **MAX Order Date**: `MAX('Orders'[Order Date])`

## Duplicate-key conflicts

- Location.Postal Code: 1 duplicate-key groups; City (1 duplicate-key groups).
- Products.Product ID: 32 duplicate-key groups; Product Name (32 duplicate-key groups).
