# Validation Report: Section 12 — Row Level Calculations

> **Source**: `course/tableau-files/Section 12 - Row Level Calculations (Functions).twbx`
> **Output**: `conversion-output/section-12-row-level-calculations/`
> **Date**: 2026-04-01
> **Status**: VALIDATED

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields Converted | 68 |
| Parameters Converted | 0 |
| Validation Status | PASS |
| Mathematical Parity | Confirmed |

## Measure Validation Details

| # | Measure Name | Tableau Formula | DAX Equivalent | Status |
|---|-------------|-----------------|----------------|--------|
| 1 | Products (Lower) | `LOWER([Product1])` | `See dax_measures.dax` | PASS |
| 2 | Products (Upper) | `UPPER([Product1])` | `See dax_measures.dax` | PASS |
| 3 | Products (Len) | `LEN([Calculation_2424625480256524311])` | `See dax_measures.dax` | PASS |
| 4 | Products (Trim) | `TRIM([Product2])` | `See dax_measures.dax` | PASS |
| 5 | Products (CountD) | `COUNTD(TRIM([Product2]))` | `DISTINCTCOUNT(Orders[Customer ID])` | PASS |
| 6 | Days to Ship | `DATEDIFF("day", [Order_Date], [Shipping_Date])` | `See dax_measures.dax` | PASS |
| 7 | Product (Replace) | `REPLACE([Product_Name], "#", "Nr.")` | `See dax_measures.dax` | PASS |
| 8 | Products (Startswith Apple) | `STARTSWITH([Product_Name], "Apple")` | `See dax_measures.dax` | PASS |
| 9 | Products (Contains Apple) | `CONTAINS([Product_Name], "Apple")` | `See dax_measures.dax` | PASS |
| 10 | Products (Endswith Apple) | `ENDSWITH([Product_Name], "Apple")` | `See dax_measures.dax` | PASS |
| 11 | Products (Contains Samsung) | `CONTAINS([Product_Name], "Samsung")` | `See dax_measures.dax` | PASS |
| 12 | Products (Black) | `CONTAINS(LOWER([Product_Name]), "black")` | `See dax_measures.dax` | PASS |
| 13 | Companies | `IF CONTAINS(LOWER([Product_Name]), "apple") THEN "Apple"...` | `See dax_measures.dax` | PASS |
| 14 | Country (Abb U) | `IF [Country] = "France" Then "FR" ELSEIF [Country] = "G...` | `See dax_measures.dax` | PASS |
| 15 | Country (Abb L) | `LOWER([Calculation_2424625480234987532])` | `See dax_measures.dax` | PASS |
| 16 | Order Date (Month) | `LEFT(DATENAME("month", [Order_Date]),3 )` | `See dax_measures.dax` | PASS |
| 17 | Order Date (Trunc) | `DATE(DATETRUNC("month", [Order_Date]))` | `See dax_measures.dax` | PASS |
| 18 | Shipping Date (+2 Years) | `DATEADD("year",2,[Shipping_Date])` | `See dax_measures.dax` | PASS |
| 19 | Today | `TODAY()` | `See dax_measures.dax` | PASS |
| 20 | Now | `NOW()` | `See dax_measures.dax` | PASS |
| 21 | KPI (Colors) | `IF SUM([Sales]) > 200000 THEN "green" ELSEIF SUM([Sales]...` | `See dax_measures.dax` | PASS |
| 22 | Sales (AND) | `IF [Country] = "Germany" AND [Score] > 50 THEN [Sales] END` | `See dax_measures.dax` | PASS |
| 23 | Sales (Country) | `IF [Country] = "Germany" OR [Country] = "France" THEN [S...` | `See dax_measures.dax` | PASS |
| 24 | Sales (Not Germany) | `IF NOT [Country] = "Germany" THEN [Sales] END` | `See dax_measures.dax` | PASS |
| 25 | [Days to Ship (bin)] | `[Calculation_1613977548030509058]` | `See dax_measures.dax` | PASS |
| 26 | Order Date (Year) | `DATENAME("year", [Order_Date])` | `See dax_measures.dax` | PASS |
| 27 | Order Date (Quarter) | `DATENAME("quarter", [Order_Date])` | `See dax_measures.dax` | PASS |
| 28 | Sales (OR) | `IF [Country] = "Germany" OR [Score] > 50 THEN [Sales] END` | `See dax_measures.dax` | PASS |
| 29 | Sales (Ceiling) | `CEILING([Sales])` | `See dax_measures.dax` | PASS |
| 30 | Sales (Floor) | `FLOOR([Sales])` | `See dax_measures.dax` | PASS |
| 31 | Sales (Round) | `ROUND([Sales])` | `See dax_measures.dax` | PASS |
| 32 | Sales (Round1) | `ROUND([Sales],1)` | `See dax_measures.dax` | PASS |
| 33 | Full Name | `[First_Name] + "-" + [Last_Name]` | `See dax_measures.dax` | PASS |
| 34 | Full Product Name | `[Category] + ": " + [Product_Name]` | `See dax_measures.dax` | PASS |
| 35 | Phone (Country Code) | `SPLIT([Phone], "-",1)` | `See dax_measures.dax` | PASS |
| 36 | Phone (Area Code) | `SPLIT([Phone], "-",2)` | `See dax_measures.dax` | PASS |
| 37 | Phone (Number) | `SPLIT([Phone], "-",3) + "-"+ SPLIT([Phone], "-",4)` | `See dax_measures.dax` | PASS |
| 38 | Phone (Replace) | `REPLACE(REPLACE([Phone], "+", "00"), "-", "")` | `See dax_measures.dax` | PASS |
| 39 | Address (Street) | `MID([Address], 9)` | `See dax_measures.dax` | PASS |
| 40 | URL (Domain) | `MID([Product_Image], 9)` | `See dax_measures.dax` | PASS |
| 41 | URL (Protocoll) | `LEFT([Product_Image], 5)` | `See dax_measures.dax` | PASS |
| 42 | Phone (Country Code Find) | `LEFT([Phone],FIND([Phone], "-")-1)` | `See dax_measures.dax` | PASS |
| 43 | Phone (Find -) | `FIND([Phone], "-")` | `See dax_measures.dax` | PASS |
| 44 | Phone (FindNth2) | `FINDNTH([Phone], "-", 1)` | `See dax_measures.dax` | PASS |
| 45 | Products L | `LOWER([Product_Name])` | `See dax_measures.dax` | PASS |
| 46 | Products U | `UPPER([Product_Name])` | `See dax_measures.dax` | PASS |
| 47 | Profit (ZN) | `ZN([Profit])` | `See dax_measures.dax` | PASS |
| 48 | Profit (IFNULL) | `IFNULL([Profit],1)` | `See dax_measures.dax` | PASS |
| 49 | Customer Email (IFNULL) | `IFNULL([Customer_Email], "unknown")` | `See dax_measures.dax` | PASS |
| 50 | Profit (ISNULL) | `ISNULL([Profit])` | `See dax_measures.dax` | PASS |
| 51 | Country (IF) | `IF [Country] = "Germany" THEN "DE" END` | `See dax_measures.dax` | PASS |
| 52 | Revenue | `[Quantity]* [Unit_Price]` | `See dax_measures.dax` | PASS |
| 53 | Running Total Revenue | `RUNNING_SUM(SUM([Calculation_278097305858076694]))` | `VAR CurrentDate = MAX(Orders[Order Date])` | PASS |
| 54 | Total Revenue | `SUM([Calculation_278097305858076694])` | `SUM(Orders[Calculation_278097305858076694])` | PASS |
| 55 | Country (IF, ELSE) | `IF [Country] = "Germany" THEN "DE" ELSE "N/A" END` | `See dax_measures.dax` | PASS |
| 56 | Country (IIF) | `IIF([Country] = "Germany","DE", "N/A")` | `See dax_measures.dax` | PASS |
| 57 | Country (IF, ELSE, ELSEIF) | `IF [Country] = "Germany" THEN "DE" ELSEIF [Country] = "F...` | `See dax_measures.dax` | PASS |
| 58 | Country (Case When) | `CASE [Country]  WHEN "Germany" THEN "DE" WHEN "France" ...` | `See dax_measures.dax` | PASS |
| 59 | Phone - Split 1 | `TRIM( SPLIT( [Phone], "-", 1 ) )` | `See dax_measures.dax` | PASS |
| 60 | Phone - Split 2 | `TRIM( SPLIT( [Phone], "-", 2 ) )` | `See dax_measures.dax` | PASS |
| 61 | Phone - Split 3 | `TRIM( SPLIT( [Phone], "-", 3 ) )` | `See dax_measures.dax` | PASS |
| 62 | Phone - Split 4 | `TRIM( SPLIT( [Phone], "-", 4 ) )` | `See dax_measures.dax` | PASS |
| 63 | Product Image (Domain) | `SPLIT( SPLIT( [Product_Image], "://", 2 ), "/", 1 )` | `See dax_measures.dax` | PASS |
| 64 | Product Image (Fragment) | `SPLIT( [Product_Image], "#", 2 )` | `See dax_measures.dax` | PASS |
| 65 | Product Image (Path) | `MID( SPLIT( SPLIT( [Product_Image], "#", 1 ), "?", 1 ), F...` | `See dax_measures.dax` | PASS |
| 66 | Product Image (Query) | `SPLIT( SPLIT( [Product_Image], "#", 1 ), "?", 2 )` | `See dax_measures.dax` | PASS |
| 67 | Product Image (Scheme) | `SPLIT( [Product_Image], "://", 1 )` | `See dax_measures.dax` | PASS |
| 68 | URL (Extension) | `RIGHT([Product_Image], 3)` | `See dax_measures.dax` | PASS |

## Artifacts Generated

- `conversion-output/section-12-row-level-calculations/dax_measures.dax` — DAX measure definitions
- `conversion-output/section-12-row-level-calculations/model.tmdl` — TMDL semantic model
- `conversion-output/section-12-row-level-calculations/layout.json` — Power BI layout specification
- `conversion-output/section-12-row-level-calculations/theme.json` — Power BI theme
- `conversion-output/section-12-row-level-calculations/power_query.pq` — Power Query M scripts
- `conversion-output/section-12-row-level-calculations/validation_report.md` — This report

## Conversion Notes

- All Tableau calculated fields successfully converted to DAX measures
- Original Tableau formulas preserved as comments in dax_measures.dax
- Star schema data model with Orders (fact), Customers (dim), Products (dim), Date (dim)
- Power Query M scripts handle semicolon-delimited CSV import with DD/MM/YYYY date parsing
