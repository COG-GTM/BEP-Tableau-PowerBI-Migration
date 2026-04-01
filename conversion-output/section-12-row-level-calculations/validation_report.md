# Validation Report — Section 12: Row Level Calculations (Functions)

## Summary
- **Total Calculated Fields**: 68
- **Converted**: 68
- **Conversion Rate**: 100%
- **Source**: Section 12 - Row Level Calculations (Functions).twb

## Categories
| Category | Count |
|----------|-------|
| String Functions | 26 |
| Date Functions | 8 |
| Conditional / Logical | 13 |
| Null Handling | 4 |
| Math Functions | 7 |
| Split / Parse | 9 |
| Bin Definition | 1 |

## Measure-by-Measure Validation

| # | Measure Name | Tableau Formula | DAX Equivalent | Status |
|---|-------------|-----------------|----------------|--------|
| 1 | Products (Lower) | `LOWER([Product1])` | `LOWER(ProductsLowQuality[Product1])` | Converted |
| 2 | Products (Upper) | `UPPER([Product1])` | `UPPER(ProductsLowQuality[Product1])` | Converted |
| 3 | Products (Len) | `LEN([Calculation...])` | `LEN(TRIM(ProductsLowQuality[Product2]))` | Converted |
| 4 | Products (Trim) | `TRIM([Product2])` | `TRIM(ProductsLowQuality[Product2])` | Converted |
| 5 | Products (CountD) | `COUNTD(TRIM([Product2]))` | `DISTINCTCOUNT(ProductsLowQuality[Product2])` | Converted |
| 6 | Product (Replace) | `REPLACE([Product_Name], "#", "Nr.")` | `SUBSTITUTE(Products[Product Name], "#", "Nr.")` | Converted |
| 7 | Products (Startswith Apple) | `STARTSWITH([Product_Name], "Apple")` | `LEFT(Products[Product Name], 5) = "Apple"` | Converted |
| 8 | Products (Contains Apple) | `CONTAINS([Product_Name], "Apple")` | `SEARCH("Apple", Products[Product Name], 1, 0) > 0` | Converted |
| 9 | Products (Endswith Apple) | `ENDSWITH([Product_Name], "Apple")` | `RIGHT(Products[Product Name], 5) = "Apple"` | Converted |
| 10 | Products (Contains Samsung) | `CONTAINS([Product_Name], "Samsung")` | `SEARCH("Samsung", ...) > 0` | Converted |
| 11 | Products (Black) | `CONTAINS(LOWER([Product_Name]), "black")` | `SEARCH("black", LOWER(...)) > 0` | Converted |
| 12 | Full Name | `[First_Name] + "-" + [Last_Name]` | `Customers[First Name] & "-" & Customers[Last Name]` | Converted |
| 13 | Full Product Name | `[Category] + ": " + [Product_Name]` | `Products[Category] & ": " & Products[Product Name]` | Converted |
| 14 | Phone (Country Code) | `SPLIT([Phone], "-", 1)` | `VAR/SEARCH DAX pattern` | Converted |
| 15 | Phone (Area Code) | `SPLIT([Phone], "-", 2)` | `VAR/SEARCH DAX pattern` | Converted |
| 16 | Phone (Number) | `SPLIT([Phone], "-", 3) + "-" + SPLIT(..., 4)` | `VAR/SEARCH DAX pattern` | Converted |
| 17 | Phone (Replace) | `REPLACE(REPLACE([Phone], "+", "00"), "-", "")` | `SUBSTITUTE(SUBSTITUTE(...))` | Converted |
| 18 | Address (Street) | `MID([Address], 9)` | `MID(Customers[Address], 9, LEN(...))` | Converted |
| 19 | URL (Domain) | `MID([Product_Image], 9)` | `MID(Products[Product Image], 9, LEN(...))` | Converted |
| 20 | URL (Protocoll) | `LEFT([Product_Image], 5)` | `LEFT(Products[Product Image], 5)` | Converted |
| 21 | Phone (Country Code Find) | `LEFT([Phone], FIND([Phone], "-")-1)` | `LEFT(Customers[Phone], SEARCH(...) - 1)` | Converted |
| 22 | Phone (Find -) | `FIND([Phone], "-")` | `SEARCH("-", Customers[Phone], 1, 0)` | Converted |
| 23 | Phone (FindNth2) | `FINDNTH([Phone], "-", 1)` | `SEARCH("-", Customers[Phone], 1, 0)` | Converted |
| 24 | Products L | `LOWER([Product_Name])` | `LOWER(Products[Product Name])` | Converted |
| 25 | Products U | `UPPER([Product_Name])` | `UPPER(Products[Product Name])` | Converted |
| 26 | URL (Extension) | `RIGHT([Product_Image], 3)` | `RIGHT(Products[Product Image], 3)` | Converted |
| 27 | Days to Ship | `DATEDIFF("day", [Order_Date], [Shipping_Date])` | `DATEDIFF(Orders[Order Date], Orders[Ship Date], DAY)` | Converted |
| 28 | Order Date (Month) | `LEFT(DATENAME("month", [Order_Date]), 3)` | `LEFT(FORMAT(Orders[Order Date], "MMMM"), 3)` | Converted |
| 29 | Order Date (Trunc) | `DATE(DATETRUNC("month", [Order_Date]))` | `STARTOFMONTH(Orders[Order Date])` | Converted |
| 30 | Shipping Date (+2 Years) | `DATEADD("year", 2, [Shipping_Date])` | `EDATE(Orders[Ship Date], 24)` | Converted |
| 31 | Today | `TODAY()` | `TODAY()` | Converted |
| 32 | Now | `NOW()` | `NOW()` | Converted |
| 33 | Order Date (Year) | `DATENAME("year", [Order_Date])` | `FORMAT(Orders[Order Date], "YYYY")` | Converted |
| 34 | Order Date (Quarter) | `DATENAME("quarter", [Order_Date])` | `FORMAT(Orders[Order Date], "Q")` | Converted |
| 35 | KPI (Colors) | `IF SUM([Sales]) > 200000 ...` | `SWITCH(TRUE(), SUM(Orders[Sales]) > 200000, ...)` | Converted |
| 36 | Sales (AND) | `IF [Country] = "Germany" AND [Score] > 50 ...` | `IF(Customers[Country] = ... && ...)` | Converted |
| 37 | Sales (Country) | `IF [Country] = "Germany" OR [Country] = "France" ...` | `IF(... || ...)` | Converted |
| 38 | Sales (Not Germany) | `IF NOT [Country] = "Germany" ...` | `IF(Customers[Country] <> "Germany", ...)` | Converted |
| 39 | Sales (OR) | `IF [Country] = "Germany" OR [Score] > 50 ...` | `IF(... || ...)` | Converted |
| 40 | Country (IF) | `IF [Country] = "Germany" THEN "DE" END` | `IF(Customers[Country] = "Germany", "DE", BLANK())` | Converted |
| 41 | Country (IF, ELSE) | `IF [Country] = "Germany" THEN "DE" ELSE "N/A" END` | `IF(Customers[Country] = "Germany", "DE", "N/A")` | Converted |
| 42 | Country (IIF) | `IIF([Country] = "Germany", "DE", "N/A")` | `IF(Customers[Country] = "Germany", "DE", "N/A")` | Converted |
| 43 | Country (IF, ELSE, ELSEIF) | `IF/ELSEIF multi-branch` | `SWITCH(TRUE(), ...)` | Converted |
| 44 | Country (Case When) | `CASE [Country] WHEN ...` | `SWITCH(Customers[Country], ...)` | Converted |
| 45 | Country (Abb U) | `IF [Country] = ... multi-branch` | `SWITCH(TRUE(), ...)` | Converted |
| 46 | Country (Abb L) | `LOWER([Calculation...])` | `LOWER([Country (Abb U)])` | Converted |
| 47 | Companies | `IF CONTAINS(LOWER(...), ...) multi-branch` | `SWITCH(TRUE(), SEARCH(...) > 0, ...)` | Converted |
| 48 | Profit (ZN) | `ZN([Profit])` | `IF(ISBLANK(Orders[Profit]), 0, Orders[Profit])` | Converted |
| 49 | Profit (IFNULL) | `IFNULL([Profit], 1)` | `IF(ISBLANK(Orders[Profit]), 1, Orders[Profit])` | Converted |
| 50 | Customer Email (IFNULL) | `IFNULL([Customer_Email], "unknown")` | `IF(ISBLANK(...), "unknown", ...)` | Converted |
| 51 | Profit (ISNULL) | `ISNULL([Profit])` | `ISBLANK(Orders[Profit])` | Converted |
| 52 | Revenue | `[Quantity] * [Unit_Price]` | `Orders[Quantity] * Orders[Unit Price]` | Converted |
| 53 | Running Total Revenue | `RUNNING_SUM(SUM([Revenue]))` | `VAR CurrentDate = MAX(...) RETURN CALCULATE(...)` | Converted |
| 54 | Total Revenue | `SUM([Revenue])` | `SUMX(Orders, Orders[Quantity] * Orders[Unit Price])` | Converted |
| 55 | Sales (Ceiling) | `CEILING([Sales])` | `CEILING(Orders[Sales], 1)` | Converted |
| 56 | Sales (Floor) | `FLOOR([Sales])` | `FLOOR(Orders[Sales], 1)` | Converted |
| 57 | Sales (Round) | `ROUND([Sales])` | `ROUND(Orders[Sales], 0)` | Converted |
| 58 | Sales (Round1) | `ROUND([Sales], 1)` | `ROUND(Orders[Sales], 1)` | Converted |
| 59 | Phone - Split 1 | `TRIM(SPLIT([Phone], "-", 1))` | `VAR/SEARCH DAX pattern` | Converted |
| 60 | Phone - Split 2 | `TRIM(SPLIT([Phone], "-", 2))` | `VAR/SEARCH DAX pattern` | Converted |
| 61 | Phone - Split 3 | `TRIM(SPLIT([Phone], "-", 3))` | `VAR/SEARCH DAX pattern` | Converted |
| 62 | Phone - Split 4 | `TRIM(SPLIT([Phone], "-", 4))` | `VAR/SEARCH DAX pattern` | Converted |
| 63 | Product Image (Domain) | `SPLIT(SPLIT([Product_Image], "://", 2), "/", 1)` | `VAR/SEARCH DAX pattern` | Converted |
| 64 | Product Image (Fragment) | `SPLIT([Product_Image], "#", 2)` | `VAR/SEARCH DAX pattern` | Converted |
| 65 | Product Image (Path) | `MID(SPLIT(SPLIT(...)))` | `VAR/SEARCH DAX pattern` | Converted |
| 66 | Product Image (Query) | `SPLIT(SPLIT([Product_Image], "#", 1), "?", 2)` | `VAR/SEARCH DAX pattern` | Converted |
| 67 | Product Image (Scheme) | `SPLIT([Product_Image], "://", 1)` | `VAR/SEARCH DAX pattern` | Converted |
| 68 | Days to Ship (bin) | `[Days to Ship] bin` | `FLOOR(DATEDIFF(...), 5)` | Converted |

## Notes
- Tableau `REPLACE` maps to DAX `SUBSTITUTE` (character-level replacement).
- Tableau `SPLIT` has no direct DAX equivalent; implemented using `SEARCH`/`MID`/`LEFT`/`RIGHT` with VAR patterns.
- Tableau `CONTAINS`/`STARTSWITH`/`ENDSWITH` mapped to `SEARCH`/`LEFT`/`RIGHT` comparisons.
- Tableau `ZN` maps to `IF(ISBLANK(...), 0, ...)`.
- Tableau `RUNNING_SUM` (table calc) mapped to DAX `CALCULATE` with `FILTER(ALL(...))` pattern.
- Tableau `DATETRUNC` mapped to `STARTOFMONTH` for month truncation.
- Tableau `DATEADD` mapped to `EDATE` for year addition (24 months = 2 years).
- Bin definition uses `FLOOR(value, bin_size)` pattern.

## Data Sources
- **ProductsLowQuality**: `course/datasets/non-eu-dataset/small-dataset/ProductsLowQuality.csv`
- **Orders**: `course/datasets/non-eu-dataset/small-dataset/Orders.csv`
- **Customers**: `course/datasets/non-eu-dataset/small-dataset/Customers.csv`
- **Products**: `course/datasets/non-eu-dataset/small-dataset/Products.csv`
- **Customers_Details**: `course/datasets/non-eu-dataset/small-dataset/Customers_Details.csv`
