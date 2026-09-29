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
- Measure **Customers by Nr of Orders**: `CALCULATE([CNTD CY Customers], KEEPFILTERS('Customer Orders by Year'[Year] = SELECTEDVALUE('Select Year'[Select Year], 2023))) + 0` (format `#,##0`)
- Measure **CY Last Order**: `MAXX(FILTER('Orders', YEAR('Orders'[Order Date]) = SELECTEDVALUE('Select Year'[Select Year], 2023)), 'Orders'[Order Date])` (format `m/d/yyyy`)
- Calculated column **Orders.Order Date (Month)**: `MONTH('Orders'[Order Date])` (int64)
- Calculated column **Orders.Order Date (Week)**: `WEEKNUM('Orders'[Order Date], 2)` (int64)
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
| Sales Dashboard | `s_logo` | image | `{"x":4,"y":4,"w":65,"h":51,"z":100}` | `[]` |
| Sales Dashboard | `s_title` | deneb | `{"x":73.01,"y":0,"w":820.01,"h":59,"z":200}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Sales Dashboard | `s_kpi_legend` | deneb | `{"x":0,"y":59,"w":900,"h":29,"z":300}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Sales Dashboard | `s_kpi_sales` | deneb | `{"x":10,"y":88,"w":380,"h":274,"z":1000}` | `[{"field": "Orders.Order Date (Month)", "as": "Month"}, {"field": "Orders.CY Sales", "as": "CY"}, {"field": "Orders.PY Sales", "as": "PY"}, {"field": "Orders.KPI Total CY Sales", "as": "Total"}, {"field": "Orders.KPI Diff Sales", "as": "Diff"}]` |
| Sales Dashboard | `s_kpi_profit` | deneb | `{"x":410,"y":88,"w":380,"h":274,"z":1001}` | `[{"field": "Orders.Order Date (Month)", "as": "Month"}, {"field": "Orders.CY Profit", "as": "CY"}, {"field": "Orders.PY Profit", "as": "PY"}, {"field": "Orders.KPI Total CY Profit", "as": "Total"}, {"field": "Orders.KPI Diff Profit", "as": "Diff"}]` |
| Sales Dashboard | `s_kpi_quantity` | deneb | `{"x":810,"y":88,"w":380,"h":274,"z":1002}` | `[{"field": "Orders.Order Date (Month)", "as": "Month"}, {"field": "Orders.CY Quantity", "as": "CY"}, {"field": "Orders.PY Quantity", "as": "PY"}, {"field": "Orders.KPI Total CY Quantity", "as": "Total"}, {"field": "Orders.KPI Diff Quantity", "as": "Diff"}]` |
| Sales Dashboard | `s_card_left` | shape | `{"x":10,"y":382,"w":580,"h":408,"z":1100}` | `[]` |
| Sales Dashboard | `s_card_right` | shape | `{"x":610,"y":382,"w":580,"h":408,"z":1101}` | `[]` |
| Sales Dashboard | `s_sub_title` | deneb | `{"x":16.99,"y":389,"w":566.02,"h":37,"z":1200}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Sales Dashboard | `s_sub_legend` | deneb | `{"x":16.99,"y":426,"w":374,"h":32,"z":1201}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Sales Dashboard | `s_profit_legend` | deneb | `{"x":391,"y":426,"w":192.01,"h":32,"z":1202}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Sales Dashboard | `s_subcategory` | deneb | `{"x":16.99,"y":458,"w":566.02,"h":324.9,"z":1203}` | `[{"field": "Products.Sub-Category", "as": "Category"}, {"field": "Orders.CY Sales", "as": "CY"}, {"field": "Orders.PY Sales", "as": "PY"}, {"field": "Orders.CY Profit", "as": "Signed"}, {"field": "Orders.KPI CY Less PY", "as": "Flag"}]` |
| Sales Dashboard | `s_trend_title` | deneb | `{"x":616.99,"y":389,"w":566.02,"h":37,"z":1300}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Sales Dashboard | `s_trend_legend` | deneb | `{"x":616.99,"y":426,"w":566.02,"h":28,"z":1301}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Sales Dashboard | `s_trends` | deneb | `{"x":616.99,"y":452,"w":566.02,"h":331,"z":1302}` | `[{"field": "Orders.Order Date (Week)", "as": "Week"}, {"field": "Orders.CY Sales", "as": "Sales"}, {"field": "Orders.CY Profit", "as": "Profit"}]` |
| Sales Dashboard | `s_fp_bg` | shape | `{"x":942,"y":0,"w":257,"h":799,"z":5000}` | `[]` |
| Sales Dashboard | `s_fp_heading` | deneb | `{"x":952,"y":96,"w":237,"h":37,"z":5100}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Sales Dashboard | `s_fp_year_label` | deneb | `{"x":952,"y":133,"w":237,"h":22,"z":5101}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Sales Dashboard | `s_fp_year` | slicer | `{"x":956,"y":155,"w":229,"h":26,"z":5102}` | `[{"field": "Select Year.Select Year"}]` |
| Sales Dashboard | `s_fp_product` | deneb | `{"x":952,"y":188,"w":237,"h":32,"z":5103}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Sales Dashboard | `s_fp_category_label` | deneb | `{"x":952,"y":220,"w":237,"h":22,"z":5104}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Sales Dashboard | `s_fp_category` | slicer | `{"x":956,"y":242,"w":229,"h":26,"z":5105}` | `[{"field": "Products.Category"}]` |
| Sales Dashboard | `s_fp_subcategory_label` | deneb | `{"x":952,"y":277,"w":237,"h":22,"z":5106}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Sales Dashboard | `s_fp_subcategory` | slicer | `{"x":956,"y":299,"w":229,"h":26,"z":5107}` | `[{"field": "Products.Sub-Category"}]` |
| Sales Dashboard | `s_fp_location` | deneb | `{"x":952,"y":394,"w":237,"h":32,"z":5108}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Sales Dashboard | `s_fp_region_label` | deneb | `{"x":952,"y":426,"w":237,"h":22,"z":5109}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Sales Dashboard | `s_fp_region` | slicer | `{"x":956,"y":448,"w":229,"h":26,"z":5110}` | `[{"field": "Location.Region"}]` |
| Sales Dashboard | `s_fp_state_label` | deneb | `{"x":952,"y":483,"w":237,"h":22,"z":5111}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Sales Dashboard | `s_fp_state` | slicer | `{"x":956,"y":505,"w":229,"h":26,"z":5112}` | `[{"field": "Location.State"}]` |
| Sales Dashboard | `s_fp_city_label` | deneb | `{"x":952,"y":540,"w":237,"h":22,"z":5113}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Sales Dashboard | `s_fp_city` | slicer | `{"x":956,"y":562,"w":229,"h":26,"z":5114}` | `[{"field": "Location.City"}]` |
| Sales Dashboard | `s_nav_sales` | image | `{"x":944,"y":10,"w":83,"h":62,"z":9000}` | `[]` |
| Sales Dashboard | `s_nav_customer` | image | `{"x":1035,"y":10,"w":83,"h":62,"z":9001}` | `[]` |
| Sales Dashboard | `s_filters_show` | image | `{"x":1136.5,"y":10,"w":62.7,"h":62,"z":9002}` | `[]` |
| Sales Dashboard | `s_filters_hide` | image | `{"x":1136.5,"y":10,"w":62.7,"h":62,"z":9003}` | `[]` |
| Customer Dashboard | `c_logo` | image | `{"x":4,"y":4,"w":65,"h":51,"z":100}` | `[]` |
| Customer Dashboard | `c_title` | deneb | `{"x":73.01,"y":0,"w":820.01,"h":59,"z":200}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Customer Dashboard | `c_kpi_legend` | deneb | `{"x":0,"y":59,"w":900,"h":29,"z":300}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Customer Dashboard | `c_kpi_customers` | deneb | `{"x":10,"y":88,"w":380,"h":274,"z":1000}` | `[{"field": "Orders.Order Date (Month)", "as": "Month"}, {"field": "Orders.CNTD CY Customers", "as": "CY"}, {"field": "Orders.CNTD PY Customers", "as": "PY"}, {"field": "Orders.KPI Total CY Customers", "as": "Total"}, {"field": "Orders.KPI Diff Customers", "as": "Diff"}]` |
| Customer Dashboard | `c_kpi_spc` | deneb | `{"x":410,"y":88,"w":380,"h":274,"z":1001}` | `[{"field": "Orders.Order Date (Month)", "as": "Month"}, {"field": "Orders.CY Sales per Customer", "as": "CY"}, {"field": "Orders.PY Sales per Customer", "as": "PY"}, {"field": "Orders.KPI Total CY Sales per Customer", "as": "Total"}, {"field": "Orders.KPI Diff Sales per Customers", "as": "Diff"}]` |
| Customer Dashboard | `c_kpi_orders` | deneb | `{"x":810,"y":88,"w":380,"h":274,"z":1002}` | `[{"field": "Orders.Order Date (Month)", "as": "Month"}, {"field": "Orders.CNTD CY Orders", "as": "CY"}, {"field": "Orders.CNTD PY Orders", "as": "PY"}, {"field": "Orders.KPI Total CY Orders", "as": "Total"}, {"field": "Orders.KPI Diff Orders", "as": "Diff"}]` |
| Customer Dashboard | `c_card_left` | shape | `{"x":10,"y":382,"w":580,"h":408,"z":1100}` | `[]` |
| Customer Dashboard | `c_card_right` | shape | `{"x":610,"y":382,"w":580,"h":408,"z":1101}` | `[]` |
| Customer Dashboard | `c_dist_title` | deneb | `{"x":16.99,"y":389,"w":566.02,"h":37,"z":1200}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Customer Dashboard | `c_distribution` | deneb | `{"x":16.99,"y":426,"w":566.02,"h":357,"z":1201}` | `[{"field": "Customer Orders by Year.Nr of Orders per Customers", "as": "X"}, {"field": "Orders.Customers by Nr of Orders", "as": "Y"}]` |
| Customer Dashboard | `c_top_title` | deneb | `{"x":616.99,"y":389,"w":566.02,"h":37,"z":1300}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Customer Dashboard | `c_top_headers` | deneb | `{"x":616.99,"y":426,"w":566.02,"h":40,"z":1301}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Customer Dashboard | `c_top_customers` | deneb | `{"x":616.99,"y":466,"w":566.02,"h":316.96,"z":1302}` | `[{"field": "Customers.Customer Name", "as": "Customer Name"}, {"field": "Orders.CY Last Order", "as": "Last"}, {"field": "Orders.CY Profit", "as": "Profit"}, {"field": "Orders.CY Sales", "as": "Sales"}, {"field": "Orders.CNTD CY Orders", "as": "Orders"}]` |
| Customer Dashboard | `c_fp_bg` | shape | `{"x":942,"y":0,"w":257,"h":799,"z":5000}` | `[]` |
| Customer Dashboard | `c_fp_heading` | deneb | `{"x":952,"y":96,"w":237,"h":37,"z":5100}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Customer Dashboard | `c_fp_year_label` | deneb | `{"x":952,"y":133,"w":237,"h":22,"z":5101}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Customer Dashboard | `c_fp_year` | slicer | `{"x":956,"y":155,"w":229,"h":26,"z":5102}` | `[{"field": "Select Year.Select Year"}]` |
| Customer Dashboard | `c_fp_product` | deneb | `{"x":952,"y":188,"w":237,"h":32,"z":5103}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Customer Dashboard | `c_fp_category_label` | deneb | `{"x":952,"y":220,"w":237,"h":22,"z":5104}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Customer Dashboard | `c_fp_category` | slicer | `{"x":956,"y":242,"w":229,"h":26,"z":5105}` | `[{"field": "Products.Category"}]` |
| Customer Dashboard | `c_fp_subcategory_label` | deneb | `{"x":952,"y":277,"w":237,"h":22,"z":5106}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Customer Dashboard | `c_fp_subcategory` | slicer | `{"x":956,"y":299,"w":229,"h":26,"z":5107}` | `[{"field": "Products.Sub-Category"}]` |
| Customer Dashboard | `c_fp_location` | deneb | `{"x":952,"y":394,"w":237,"h":32,"z":5108}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Customer Dashboard | `c_fp_region_label` | deneb | `{"x":952,"y":426,"w":237,"h":22,"z":5109}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Customer Dashboard | `c_fp_region` | slicer | `{"x":956,"y":448,"w":229,"h":26,"z":5110}` | `[{"field": "Location.Region"}]` |
| Customer Dashboard | `c_fp_state_label` | deneb | `{"x":952,"y":483,"w":237,"h":22,"z":5111}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Customer Dashboard | `c_fp_state` | slicer | `{"x":956,"y":505,"w":229,"h":26,"z":5112}` | `[{"field": "Location.State"}]` |
| Customer Dashboard | `c_fp_city_label` | deneb | `{"x":952,"y":540,"w":237,"h":22,"z":5113}` | `[{"field": "Orders.Current Year Value", "as": "Year"}, {"field": "Orders.Previous Year Value", "as": "PYear"}]` |
| Customer Dashboard | `c_fp_city` | slicer | `{"x":956,"y":562,"w":229,"h":26,"z":5114}` | `[{"field": "Location.City"}]` |
| Customer Dashboard | `c_nav_sales` | image | `{"x":944,"y":10,"w":83,"h":62,"z":9000}` | `[]` |
| Customer Dashboard | `c_nav_customer` | image | `{"x":1035,"y":10,"w":83,"h":62,"z":9001}` | `[]` |
| Customer Dashboard | `c_filters_show` | image | `{"x":1136.5,"y":10,"w":62.7,"h":62,"z":9002}` | `[]` |
| Customer Dashboard | `c_filters_hide` | image | `{"x":1136.5,"y":10,"w":62.7,"h":62,"z":9003}` | `[]` |

## Duplicate-key conflicts

- Location.Postal Code: 1 duplicate-key groups; City (1 duplicate-key groups).
- Products.Product ID: 32 duplicate-key groups; Product Name (32 duplicate-key groups).
