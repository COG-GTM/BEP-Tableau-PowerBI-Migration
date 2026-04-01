# Section 12 - Row Level Calculations (Functions)

> **Source**: `Section 12 - Row Level Calculations (Functions).twbx`
> **Extracted TWB**: `Section 12 - Row Level Calculations (Functions).twb`

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields | 68 |
| Parameters | 0 |
| Data Sources | 31 |
| Dashboards | 1 |
| Worksheets | 28 |

## Key Tableau Features Used

- Running calculations
- DATEDIFF date calculation
- CASE/WHEN switching
- Null handling (ISNULL/ZN)
- COUNTD (distinct count)

## Calculated Fields

| # | Name | Formula | Data Type | Role |
|---|------|---------|-----------|------|
| 1 | Products (Lower) | `LOWER([Product1])` | string | dimension |
| 2 | Products (Upper) | `UPPER([Product1])` | string | dimension |
| 3 | Products (Len) | `LEN([Calculation_2424625480256524311])` | integer | dimension |
| 4 | Products (Trim) | `TRIM([Product2])` | string | dimension |
| 5 | Products (CountD) | `COUNTD(TRIM([Product2]))` | integer | measure |
| 6 | Days to Ship | `DATEDIFF("day", [Order_Date], [Shipping_Date])` | integer | measure |
| 7 | Product (Replace) | `REPLACE([Product_Name], "#", "Nr.")` | string | dimension |
| 8 | Products (Startswith Apple) | `STARTSWITH([Product_Name], "Apple")` | boolean | dimension |
| 9 | Products (Contains Apple) | `CONTAINS([Product_Name], "Apple")` | boolean | dimension |
| 10 | Products (Endswith Apple) | `ENDSWITH([Product_Name], "Apple")` | boolean | dimension |
| 11 | Products (Contains Samsung) | `CONTAINS([Product_Name], "Samsung")` | boolean | dimension |
| 12 | Products (Black) | `CONTAINS(LOWER([Product_Name]), "black")` | boolean | dimension |
| 13 | Companies | `IF CONTAINS(LOWER([Product_Name]), "apple") THEN "Apple" ELSEIF CONTAINS(LOWER([Product_Name]), "samsung") THEN "Sam...` | string | dimension |
| 14 | Country (Abb U) | `IF [Country] = "France" Then "FR" ELSEIF [Country] = "Germany" THEN "DE" ELSEIF [Country] = "Italy" THEN "IT" E...` | string | dimension |
| 15 | Country (Abb L) | `LOWER([Calculation_2424625480234987532])` | string | dimension |
| 16 | Order Date (Month) | `LEFT(DATENAME("month", [Order_Date]),3 )` | string | dimension |
| 17 | Order Date (Trunc) | `DATE(DATETRUNC("month", [Order_Date]))` | date | dimension |
| 18 | Shipping Date (+2 Years) | `DATEADD("year",2,[Shipping_Date])` | datetime | dimension |
| 19 | Today | `TODAY()` | date | dimension |
| 20 | Now | `NOW()` | datetime | dimension |
| 21 | KPI (Colors) | `IF SUM([Sales]) > 200000 THEN "green" ELSEIF SUM([Sales]) > 100000 THEN "organge" ELSEIF SUM([Sales]) <= 100000 THE...` | string | measure |
| 22 | Sales (AND) | `IF [Country] = "Germany" AND [Score] > 50 THEN [Sales] END` | real | measure |
| 23 | Sales (Country) | `IF [Country] = "Germany" OR [Country] = "France" THEN [Sales] END` | real | measure |
| 24 | Sales (Not Germany) | `IF NOT [Country] = "Germany" THEN [Sales] END` | real | measure |
| 25 | [Days to Ship (bin)] | `[Calculation_1613977548030509058]` | integer | dimension |
| 26 | Order Date (Year) | `DATENAME("year", [Order_Date])` | string | dimension |
| 27 | Order Date (Quarter) | `DATENAME("quarter", [Order_Date])` | string | dimension |
| 28 | Sales (OR) | `IF [Country] = "Germany" OR [Score] > 50 THEN [Sales] END` | real | measure |
| 29 | Sales (Ceiling) | `CEILING([Sales])` | integer | measure |
| 30 | Sales (Floor) | `FLOOR([Sales])` | integer | measure |
| 31 | Sales (Round) | `ROUND([Sales])` | real | measure |
| 32 | Sales (Round1) | `ROUND([Sales],1)` | real | measure |
| 33 | Full Name | `[First_Name] + "-" + [Last_Name]` | string | dimension |
| 34 | Full Product Name | `[Category] + ": " + [Product_Name]` | string | dimension |
| 35 | Phone (Country Code) | `SPLIT([Phone], "-",1)` | string | dimension |
| 36 | Phone (Area Code) | `SPLIT([Phone], "-",2)` | string | dimension |
| 37 | Phone (Number) | `SPLIT([Phone], "-",3) + "-"+ SPLIT([Phone], "-",4)` | string | dimension |
| 38 | Phone (Replace) | `REPLACE(REPLACE([Phone], "+", "00"), "-", "")` | string | dimension |
| 39 | Address (Street) | `MID([Address], 9)` | string | dimension |
| 40 | URL (Domain) | `MID([Product_Image], 9)` | string | dimension |
| 41 | URL (Protocoll) | `LEFT([Product_Image], 5)` | string | dimension |
| 42 | Phone (Country Code Find) | `LEFT([Phone],FIND([Phone], "-")-1)` | string | dimension |
| 43 | Phone (Find -) | `FIND([Phone], "-")` | integer | measure |
| 44 | Phone (FindNth2) | `FINDNTH([Phone], "-", 1)` | integer | measure |
| 45 | Products L | `LOWER([Product_Name])` | string | dimension |
| 46 | Products U | `UPPER([Product_Name])` | string | dimension |
| 47 | Profit (ZN) | `ZN([Profit])` | real | measure |
| 48 | Profit (IFNULL) | `IFNULL([Profit],1)` | real | measure |
| 49 | Customer Email (IFNULL) | `IFNULL([Customer_Email], "unknown")` | string | dimension |
| 50 | Profit (ISNULL) | `ISNULL([Profit])` | boolean | dimension |
| 51 | Country (IF) | `IF [Country] = "Germany" THEN "DE" END` | string | dimension |
| 52 | Revenue | `[Quantity]* [Unit_Price]` | real | measure |
| 53 | Running Total Revenue | `RUNNING_SUM(SUM([Calculation_278097305858076694]))` | real | measure |
| 54 | Total Revenue | `SUM([Calculation_278097305858076694])` | real | measure |
| 55 | Country (IF, ELSE) | `IF [Country] = "Germany" THEN "DE" ELSE "N/A" END` | string | dimension |
| 56 | Country (IIF) | `IIF([Country] = "Germany","DE", "N/A")` | string | dimension |
| 57 | Country (IF, ELSE, ELSEIF) | `IF [Country] = "Germany" THEN "DE" ELSEIF [Country] = "France" THEN "FR" ELSEIF [Country] = "USA" THEN "US" ELSE "...` | string | dimension |
| 58 | Country (Case When) | `CASE [Country]  WHEN "Germany" THEN "DE" WHEN "France" THEN "FR" WHEN "USA" THEN "US" ELSE "N/A" END` | string | dimension |
| 59 | Phone - Split 1 | `TRIM( SPLIT( [Phone], "-", 1 ) )` | string | dimension |
| 60 | Phone - Split 2 | `TRIM( SPLIT( [Phone], "-", 2 ) )` | string | dimension |
| 61 | Phone - Split 3 | `TRIM( SPLIT( [Phone], "-", 3 ) )` | string | dimension |
| 62 | Phone - Split 4 | `TRIM( SPLIT( [Phone], "-", 4 ) )` | string | dimension |
| 63 | Product Image (Domain) | `SPLIT( SPLIT( [Product_Image], "://", 2 ), "/", 1 )` | string | dimension |
| 64 | Product Image (Fragment) | `SPLIT( [Product_Image], "#", 2 )` | string | dimension |
| 65 | Product Image (Path) | `MID( SPLIT( SPLIT( [Product_Image], "#", 1 ), "?", 1 ), FIND( [Product_Image], "/", FIND( [Product_Image], "://") + 3...` | string | dimension |
| 66 | Product Image (Query) | `SPLIT( SPLIT( [Product_Image], "#", 1 ), "?", 2 )` | string | dimension |
| 67 | Product Image (Scheme) | `SPLIT( [Product_Image], "://", 1 )` | string | dimension |
| 68 | URL (Extension) | `RIGHT([Product_Image], 3)` | string | dimension |

## Data Sources

| # | Name | Connection Type | Tables/Files |
|---|------|----------------|--------------|
| 1 | ProductsLowQuality | federated | ProductsLowQuality.csv, Extract |
| 2 | Big Data Source | federated | Orders.csv, Customers.csv, Products.csv, Orders.csv_5AF5F66F4EC84139B3533FCBFC0437BE, Customers.csv_90819B9BAE6E4CCA87ED07457EF68A05 |
| 3 | Small Data Source | federated | Customers.csv, Customers_Details.csv, Orders.csv+, Orders.csv, Orders_Archive.csv |
| 4 | Small Data Source | unknown | - |
| 5 | Small Data Source | unknown | - |
| 6 | Small Data Source | unknown | - |
| 7 | Small Data Source | unknown | - |
| 8 | Big Data Source | unknown | - |
| 9 | Big Data Source | unknown | - |
| 10 | Small Data Source | unknown | - |
| 11 | Big Data Source | unknown | - |
| 12 | Small Data Source | unknown | - |
| 13 | Small Data Source | unknown | - |
| 14 | Big Data Source | unknown | - |
| 15 | Small Data Source | unknown | - |
| 16 | Big Data Source | unknown | - |
| 17 | Big Data Source | unknown | - |
| 18 | Small Data Source | unknown | - |
| 19 | ProductsLowQuality | unknown | - |
| 20 | ProductsLowQuality | unknown | - |
| 21 | Small Data Source | unknown | - |
| 22 | Small Data Source | unknown | - |
| 23 | Big Data Source | unknown | - |
| 24 | Small Data Source | unknown | - |
| 25 | Small Data Source | unknown | - |
| 26 | Small Data Source | unknown | - |
| 27 | Big Data Source | unknown | - |
| 28 | Big Data Source | unknown | - |
| 29 | Big Data Source | unknown | - |
| 30 | Big Data Source | unknown | - |
| 31 | Small Data Source | unknown | - |

## Dashboards

- **Lower, Upper 2** (1024 x 768)

## Worksheets

- Calculation Types
- Ceiling, Floor, Round
- Concat Full name
- Concat Product
- Datediff
- Extract Dates
- Find, FindNth
- Format Date
- Left, Right, Mid
- Left, Right, Mid (Task)
- Logical (KPI)
- Logical Conditions
- Logical Operators
- Lower Abb
- Lower Products
- Lower, Upper
- Ltrim, Rtrim,Trim
- Null Functions
- Replace (Phone)
- Replace (Product)
- Split (Automatic)
- Split (Calc.)
- Split (Manual)
- Starts, Ends, Contains
- Today
- Truncate Date
- Upper Abb
- Upper Products

## Extracted Files

- `Data/TableauTemp/#TableauTemp_1q7htp21xm5zb610livg919zt3im.hyper`
- `Data/TableauTemp/TEMP_0huhu5b0z3w9lu13w3c8m104l3bh.hyper`
- `Data/TableauTemp/TEMP_0ycaug41sov6ia19pq4iq06ejah4.hyper`
- `Section 12 - Row Level Calculations (Functions).twb`
