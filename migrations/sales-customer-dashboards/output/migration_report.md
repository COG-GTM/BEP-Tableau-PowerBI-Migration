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

## Lead overrides

- Measure **KPI Total CY Sales**: `CALCULATE([CY Sales], REMOVEFILTERS('Orders'[Order Date (Month)]))` (format `"$"#,##0,K`)
- Measure **KPI Diff Sales**: `CALCULATE([% Diff Sales], REMOVEFILTERS('Orders'[Order Date (Month)]))` (format `0.0%`)
- Measure **KPI Total CY Profit**: `CALCULATE([CY Profit], REMOVEFILTERS('Orders'[Order Date (Month)]))` (format `"$"#,##0,K`)
- Measure **KPI Diff Profit**: `CALCULATE([% Diff Profit], REMOVEFILTERS('Orders'[Order Date (Month)]))` (format `0.0%`)
- Measure **KPI Total CY Quantity**: `CALCULATE([CY Quantity], REMOVEFILTERS('Orders'[Order Date (Month)]))` (format `"$"#,##0,K`)
- Measure **KPI Diff Quantity**: `CALCULATE([% Diff Quantity], REMOVEFILTERS('Orders'[Order Date (Month)]))` (format `0.0%`)
- Measure **KPI Total CY Customers**: `CALCULATE([CNTD CY Customers], REMOVEFILTERS('Orders'[Order Date (Month)]))` (format `#,##0`)
- Measure **KPI Diff Customers**: `CALCULATE([% Diff Customers], REMOVEFILTERS('Orders'[Order Date (Month)]))` (format `0.0%`)
- Measure **KPI Total CY Sales per Customer**: `CALCULATE([CY Sales per Customer], REMOVEFILTERS('Orders'[Order Date (Month)]))` (format `"$"#,##0`)
- Measure **KPI Diff Sales per Customers**: `CALCULATE([% Diff Sales per Customers], REMOVEFILTERS('Orders'[Order Date (Month)]))` (format `0.0%`)
- Measure **KPI Total CY Orders**: `CALCULATE([CNTD CY Orders], REMOVEFILTERS('Orders'[Order Date (Month)]))` (format `#,##0`)
- Measure **KPI Diff Orders**: `CALCULATE([% Diff Orders], REMOVEFILTERS('Orders'[Order Date (Month)]))` (format `0.0%`)
- Measure **Current Year Value**: `SELECTEDVALUE('Select Year'[Select Year], 2023)` (format `0`)
- Measure **Previous Year Value**: `SELECTEDVALUE('Select Year'[Select Year], 2023) - 1` (format `0`)
- Measure **Customers by Nr of Orders**: `[CNTD CY Customers] + 0` (format `#,##0`)
- Calculated column **Orders.Order Date (Month)**: `MONTH('Orders'[Order Date])` (int64)
- Calculated column **Orders.Order Date (Week)**: `WEEKNUM('Orders'[Order Date], 1)` (int64)
- Calculated table **Customer Orders by Year**: columns Customer ID (string), Year (int64), Nr of Orders per Customers (int64); DAX `GENERATE(
  CROSSJOIN(
    DISTINCT(SELECTCOLUMNS('Orders', "Customer ID", 'Orders'[Customer ID])),
    SELECTCOLUMNS('Select Year', "Year", 'Select Year'[Select Year])
  ),
  VAR c = [Customer ID]
  VAR y = [Year]
  RETURN ROW(
    "Nr of Orders per Customers",
    COUNTROWS(DISTINCT(SELECTCOLUMNS(
      FILTER(ALL('Orders'), 'Orders'[Customer ID] = c && YEAR('Orders'[Order Date]) = y),
      "o", 'Orders'[Order ID]))) + 0
  )
)`
- Relationship `Customer Orders by Year.Year` → `Select Year.Select Year` (oneDirection)
- Relationship `Customer Orders by Year.Customer ID` → `Customers.Customer ID` (bothDirections)

## Visuals

| Dashboard | ID | Type | Position | Fields |
|---|---|---|---|---|
| - | - | - | - | - |

## Duplicate-key conflicts

- Location.Postal Code: 1 duplicate-key groups; City (1 duplicate-key groups).
- Products.Product ID: 32 duplicate-key groups; Product Name (32 duplicate-key groups).
