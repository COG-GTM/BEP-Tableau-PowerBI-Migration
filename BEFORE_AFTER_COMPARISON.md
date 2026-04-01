# Tableau to Power BI Migration: Before & After Comparison

## Repository Structure

```
BEP-Tableau-PowerBI-Migration/
  tableau-source/          <- Original Tableau workbooks and data (BEFORE)
    projects/              <- Project dashboards (HR, Sales)
    course/                <- Course workbooks (Sections 5-15)
      tableau-files/       <- .twb XML files + README documentation
      datasets/            <- Source CSV datasets
  conversion-output/       <- Converted Power BI artifacts (AFTER)
    sales-dashboard/       <- Sales & Customer Dashboard
    hr-dashboard/          <- HR Dashboard
    section-05-*/          <- Course section conversions
    ...                    <- (17 total workbook conversions)
  validation/             <- Validation scripts and test suite
```

## Migration Summary

| # | Workbook | Calculated Fields | Parameters | Status |
|---|----------|-------------------|------------|--------|
| 1 | HR Dashboard | 6 | 0 | Converted |
| 2 | Sales & Customer Dashboards | 8 | 1 | Converted |
| 3 | Section 05 - Data Sources | 1 | 0 | Converted |
| 4 | Section 06 - Metadata | 1 | 0 | Converted |
| 5 | Section 07 - Renaming | 3 | 0 | Converted |
| 6 | Section 08 - Organizing Data | 5 | 0 | Converted |
| 7 | Section 09 - Filtering Data | 5 | 0 | Converted |
| 8 | Section 10 - Parameters | 17 | 5 | Converted |
| 9 | Section 11 - Actions | 7 | 1 | Converted |
| 10 | Section 12 - Aggregate Calculations | 7 | 0 | Converted |
| 11 | Section 12 - LOD Expressions | 8 | 0 | Converted |
| 12 | Section 12 - Row Level Calculations | 68 | 0 | Converted |
| 13 | Section 12 - Table Calculations | 14 | 0 | Converted |
| 14 | Section 13 - Multi-Measures | 0 | 0 | Converted |
| 15 | Section 13 - Tableau 63 Charts | 15 | 3 | Converted |
| 16 | Section 14 - Tableau Dashboard | 3 | 0 | Converted |
| 17 | Section 15 - Sales & Customer Dashboards | 34 | 1 | Converted |
| | **TOTAL** | **202** | **11** | **17/17** |

---

## Per-Workbook Calculated Field Conversion Details

### HR Dashboard

- **Source**: `tableau-source/projects/hr-dashboard-project/HR Dashboard/`
- **Output**: `conversion-output/hr-dashboard/`
- **Artifacts**: `dax_measures.dax`, `model.tmdl`, `layout.json`, `theme.json`, `power_query.pq`, `validation_report.md`

| # | Tableau Calculated Field | Original Tableau Formula | DAX Pattern |
|---|------------------------|--------------------------|-------------|
| 1 | Active Employees | `IF [Status] = 'Active' THEN 1 ELSE 0 END` | `IF / SWITCH` |
| 2 | Terminated Employees | `IF [Status] = 'Terminated' THEN 1 ELSE 0 END` | `IF / SWITCH` |
| 3 | Hire Year | `YEAR([Hire Date])` | `YEAR` |
| 4 | Termination Year | `YEAR([Termination Date])` | `YEAR` |
| 5 | Years at Company | `DATEDIFF('year', [Hire Date], TODAY())` | `DATEDIFF` |
| 6 | Age Group | `IF [Age] < 25 THEN 'Under 25' ELSEIF [Age] < 35 THEN '25-34' ELSEIF [Age] < 4...` | `IF / SWITCH` |

### Sales & Customer Dashboards

- **Source**: `tableau-source/projects/sales-dashboard-project/Sales & Customer Dashboards/`
- **Output**: `conversion-output/sales-dashboard/`
- **Artifacts**: `dax_measures.dax`, `model.tmdl`, `layout.json`, `theme.json`, `power_query.pq`, `validation_report.md`

| # | Tableau Calculated Field | Original Tableau Formula | DAX Pattern |
|---|------------------------|--------------------------|-------------|
| 1 | CY Sales | `IF YEAR([Order Date]) = [Parameters].[Parameter 1] THEN [Sales] END` | `IF / SWITCH` |
| 2 | PY Sales | `IF YEAR([Order Date]) = [Parameters].[Parameter 1]-1 THEN [Sales] END` | `IF / SWITCH` |
| 3 | % Diff Sales | `(SUM([CY Sales]) - SUM([PY Sales])) / SUM([PY Sales])` | `SUM` |
| 4 | CY Profit | `IF YEAR([Order Date]) = [Parameters].[Parameter 1] THEN [Profit] END` | `IF / SWITCH` |
| 5 | Nr of Orders per Customer | `{ FIXED [Customer ID]: COUNTD([Order ID]) }` | `CALCULATE + ALLEXCEPT` |
| 6 | Max Sales Flag | `IF SUM([CY Sales]) = WINDOW_MAX(SUM([CY Sales])) THEN 'Max' ELSEIF SUM([CY Sa...` | `MAXX(ALLSELECTED)` |
| 7 | Running Total Sales | `RUNNING_SUM(SUM([Sales]))` | `CALCULATE + FILTER(ALL)` |
| 8 | Sales Rank | `RANK(SUM([Sales]))` | `RANKX(ALLSELECTED)` |

**Parameters**: Parameter 1

### Section 05 - Data Sources

- **Source**: `tableau-source/course/tableau-files/Section 05 - Data Sources/`
- **Output**: `conversion-output/section-05-data-sources/`
- **Artifacts**: `dax_measures.dax`, `model.tmdl`, `layout.json`, `theme.json`, `power_query.pq`, `validation_report.md`

| # | Tableau Calculated Field | Original Tableau Formula | DAX Pattern |
|---|------------------------|--------------------------|-------------|
| 1 | Logic 400 | `[Sales] < 400` | `See dax_measures.dax` |

### Section 06 - Metadata

- **Source**: `tableau-source/course/tableau-files/Section 06 - Metadata/`
- **Output**: `conversion-output/section-06-metadata/`
- **Artifacts**: `dax_measures.dax`, `model.tmdl`, `layout.json`, `theme.json`, `power_query.pq`, `validation_report.md`

| # | Tableau Calculated Field | Original Tableau Formula | DAX Pattern |
|---|------------------------|--------------------------|-------------|
| 1 | Logic 400 | `[Sales] < 400` | `See dax_measures.dax` |

### Section 07 - Renaming

- **Source**: `tableau-source/course/tableau-files/Section 07 - Renaming/`
- **Output**: `conversion-output/section-07-renaming/`
- **Artifacts**: `dax_measures.dax`, `model.tmdl`, `layout.json`, `theme.json`, `power_query.pq`, `validation_report.md`

| # | Tableau Calculated Field | Original Tableau Formula | DAX Pattern |
|---|------------------------|--------------------------|-------------|
| 1 | Category (Short) | `[Category]` | `See dax_measures.dax` |
| 2 | Logic 400 | `[Sales] < 400` | `See dax_measures.dax` |
| 3 | Country (Short) | `[Country]` | `See dax_measures.dax` |

### Section 08 - Organizing Data

- **Source**: `tableau-source/course/tableau-files/Section 08 - Organizing Data/`
- **Output**: `conversion-output/section-08-organizing-data/`
- **Artifacts**: `dax_measures.dax`, `model.tmdl`, `layout.json`, `theme.json`, `power_query.pq`, `validation_report.md`

| # | Tableau Calculated Field | Original Tableau Formula | DAX Pattern |
|---|------------------------|--------------------------|-------------|
| 1 | Category (Short) | `[Category]` | `See dax_measures.dax` |
| 2 | Sales (bin) | `[Sales]` | `See dax_measures.dax` |
| 3 | Score (bin) | `[Score]` | `See dax_measures.dax` |
| 4 | Logic 400 | `[Sales] < 400` | `See dax_measures.dax` |
| 5 | Country (Short) | `[Country]` | `See dax_measures.dax` |

### Section 09 - Filtering Data

- **Source**: `tableau-source/course/tableau-files/Section 09 - Filtering Data/`
- **Output**: `conversion-output/section-09-filtering-data/`
- **Artifacts**: `dax_measures.dax`, `model.tmdl`, `layout.json`, `theme.json`, `power_query.pq`, `validation_report.md`

| # | Tableau Calculated Field | Original Tableau Formula | DAX Pattern |
|---|------------------------|--------------------------|-------------|
| 1 | Logic 400 | `[Sales] < 400` | `See dax_measures.dax` |
| 2 | Country (Short) | `[Country]` | `See dax_measures.dax` |
| 3 | Category (Short) | `[Category]` | `See dax_measures.dax` |
| 4 | Sales (bin) | `[Sales]` | `See dax_measures.dax` |
| 5 | Score (bin) | `[Score]` | `See dax_measures.dax` |

### Section 10 - Parameters

- **Source**: `tableau-source/course/tableau-files/Section 10 - Parameters/`
- **Output**: `conversion-output/section-10-parameters/`
- **Artifacts**: `dax_measures.dax`, `model.tmdl`, `layout.json`, `theme.json`, `power_query.pq`, `validation_report.md`

| # | Tableau Calculated Field | Original Tableau Formula | DAX Pattern |
|---|------------------------|--------------------------|-------------|
| 1 | Logic 400 | `[Sales] < 400` | `See dax_measures.dax` |
| 2 | Country (Short) | `[Country]` | `See dax_measures.dax` |
| 3 | KPI Colors | `If SUM([Profit]) < [Parameters].[Parameter 4] THEN 'Red' ELSE 'Green' END` | `SUM` |
| 4 | Dynamic Dimension | `CASE [Parameters].[Parameter 1] WHEN 'Country' THEN [Country] WHEN 'Categor...` | `SWITCH(TRUE())` |
| 5 | Dynamic Measure | `CASE [Parameters].[Parameter 2] WHEN 'Sales' THEN [Sales] WHEN 'Profit' THE...` | `SWITCH(TRUE())` |
| 6 | Category (Short) | `[Category]` | `See dax_measures.dax` |
| 7 | Sales (bin) | `[Sales]` | `See dax_measures.dax` |
| 8 | Score (bin) | `[Score]` | `See dax_measures.dax` |
| 9 | Choose Dimension | `"Country"` | `See dax_measures.dax` |
| 10 | Choose Measure | `"Sales"` | `See dax_measures.dax` |
| 11 | Choose Size of Bins | `20.` | `See dax_measures.dax` |
| 12 | Choose Threshold | `10000` | `See dax_measures.dax` |
| 13 | Choose Dimension | `"Country"` | `See dax_measures.dax` |
| 14 | Choose Measure | `"Sales"` | `See dax_measures.dax` |
| 15 | Choose Size of Bins | `20.` | `See dax_measures.dax` |
| 16 | Choose Threshold | `10000` | `See dax_measures.dax` |
| 17 | Choose Top N Products | `15` | `See dax_measures.dax` |

**Parameters**: Choose Dimension, Choose Measure, Choose Size of Bins, Choose Threshold, Choose Top N Products

### Section 11 - Actions

- **Source**: `tableau-source/course/tableau-files/Section 11 - Actions/`
- **Output**: `conversion-output/section-11-actions/`
- **Artifacts**: `dax_measures.dax`, `model.tmdl`, `layout.json`, `theme.json`, `power_query.pq`, `validation_report.md`

| # | Tableau Calculated Field | Original Tableau Formula | DAX Pattern |
|---|------------------------|--------------------------|-------------|
| 1 | Total | `0.` | `See dax_measures.dax` |
| 2 | Calculation1 | `[Parameters].[Parameter 1]` | `See dax_measures.dax` |
| 3 | Total | `0.` | `See dax_measures.dax` |
| 4 | Total | `[Parameters].[Parameter 1]` | `See dax_measures.dax` |
| 5 | [Sales (bin)] | `[Sales]` | `See dax_measures.dax` |
| 6 | Score (bin) | `[Score]` | `See dax_measures.dax` |
| 7 | Total | `0.` | `See dax_measures.dax` |

**Parameters**: Total

### Section 12 - Aggregate Calculations

- **Source**: `tableau-source/course/tableau-files/Section 12 - Aggregate Calculations/`
- **Output**: `conversion-output/section-12-aggregate-calculations/`
- **Artifacts**: `dax_measures.dax`, `model.tmdl`, `layout.json`, `theme.json`, `power_query.pq`, `validation_report.md`

| # | Tableau Calculated Field | Original Tableau Formula | DAX Pattern |
|---|------------------------|--------------------------|-------------|
| 1 | Total Sales | `SUM([Sales])` | `SUM` |
| 2 |  Avg. Sales | `AVG([Sales])` | `AVERAGE` |
| 3 | Nr. of Orders | `COUNT([Order_ID])` | `See dax_measures.dax` |
| 4 | Nr. Of Products | `COUNTD([Product_ID])` | `DISTINCTCOUNT` |
| 5 | Highest Sales | `MAX([Sales])` | `See dax_measures.dax` |
| 6 | Lowest Sales | `MIN([Sales])` | `See dax_measures.dax` |
| 7 | Attr(Postal Code) | `ATTR([Postal_Code])` | `See dax_measures.dax` |

### Section 12 - LOD Expressions

- **Source**: `tableau-source/course/tableau-files/Section 12 - LOD Expressions/`
- **Output**: `conversion-output/section-12-lod-expressions/`
- **Artifacts**: `dax_measures.dax`, `model.tmdl`, `layout.json`, `theme.json`, `power_query.pq`, `validation_report.md`

| # | Tableau Calculated Field | Original Tableau Formula | DAX Pattern |
|---|------------------------|--------------------------|-------------|
| 1 | Sales By Category | `{ FIXED [Category] : SUM([Sales]) }` | `CALCULATE + ALLEXCEPT` |
| 2 | Sales Exclude Category | `{ EXCLUDE [Category] : SUM([Sales]) }` | `CALCULATE + ALL(dim)` |
| 3 | Calculation1 | `{ INCLUDE [First_Name] : SUM([Sales]) }` | `SUMMARIZE + ADDCOLUMNS` |
| 4 | Avg Sales of Customers | `{ INCLUDE [First_Name] : SUM([Sales]) }` | `SUMMARIZE + ADDCOLUMNS` |
| 5 | Nr. of Orders per Customer | `{ FIXED [Customer_ID]: COUNT([Order_ID]) }` | `CALCULATE + ALLEXCEPT` |
| 6 | Sales of Tables | `IF [Sub_Category] = "Tables" THEN [Sales] END` | `IF / SWITCH` |
| 7 | Exclude Sub Category | `{ EXCLUDE [Sub_Category]: SUM([Calculation_1596526105595723802]) }` | `CALCULATE + ALL(dim)` |
| 8 | Difference | `SUM([Sales]) - SUM([Calculation_1596526105598066726])` | `SUM` |

### Section 12 - Row Level Calculations

- **Source**: `tableau-source/course/tableau-files/Section 12 - Row Level Calculations/`
- **Output**: `conversion-output/section-12-row-level-calculations/`
- **Artifacts**: `dax_measures.dax`, `model.tmdl`, `layout.json`, `theme.json`, `power_query.pq`, `validation_report.md`

| # | Tableau Calculated Field | Original Tableau Formula | DAX Pattern |
|---|------------------------|--------------------------|-------------|
| 1 | Products (Lower) | `LOWER([Product1])` | `LOWER` |
| 2 | Products (Upper) | `UPPER([Product1])` | `UPPER` |
| 3 | Products (Len) | `LEN([Calculation_2424625480256524311])` | `LEN` |
| 4 | Products (Trim) | `TRIM([Product2])` | `See dax_measures.dax` |
| 5 | Products (CountD) | `COUNTD(TRIM([Product2]))` | `DISTINCTCOUNT` |
| 6 | Days to Ship | `DATEDIFF("day", [Order_Date], [Shipping_Date])` | `DATEDIFF` |
| 7 | Product (Replace) | `REPLACE([Product_Name], "#", "Nr.")` | `See dax_measures.dax` |
| 8 | Products (Startswith Apple) | `STARTSWITH([Product_Name], "Apple")` | `See dax_measures.dax` |
| 9 | Products (Contains Apple) | `CONTAINS([Product_Name], "Apple")` | `CONTAINSSTRING` |
| 10 | Products (Endswith Apple) | `ENDSWITH([Product_Name], "Apple")` | `See dax_measures.dax` |
| 11 | Products (Contains Samsung) | `CONTAINS([Product_Name], "Samsung")` | `CONTAINSSTRING` |
| 12 | Products (Black) | `CONTAINS(LOWER([Product_Name]), "black")` | `LOWER` |
| 13 | Companies | `IF CONTAINS(LOWER([Product_Name]), "apple") THEN "Apple" ELSEIF CONTAINS(LOW...` | `IF / SWITCH` |
| 14 | Country (Abb U) | `IF [Country] = "France" Then "FR" ELSEIF [Country] = "Germany" THEN "DE" ...` | `IF / SWITCH` |
| 15 | Country (Abb L) | `LOWER([Calculation_2424625480234987532])` | `LOWER` |
| 16 | Order Date (Month) | `LEFT(DATENAME("month", [Order_Date]),3 )` | `LEFT` |
| 17 | Order Date (Trunc) | `DATE(DATETRUNC("month", [Order_Date]))` | `See dax_measures.dax` |
| 18 | Shipping Date (+2 Years) | `DATEADD("year",2,[Shipping_Date])` | `See dax_measures.dax` |
| 19 | Today | `TODAY()` | `TODAY` |
| 20 | Now | `NOW()` | `See dax_measures.dax` |
| 21 | KPI (Colors) | `IF SUM([Sales]) > 200000 THEN "green" ELSEIF SUM([Sales]) > 100000 THEN "org...` | `SUM` |
| 22 | Sales (AND) | `IF [Country] = "Germany" AND [Score] > 50 THEN [Sales] END` | `IF / SWITCH` |
| 23 | Sales (Country) | `IF [Country] = "Germany" OR [Country] = "France" THEN [Sales] END` | `IF / SWITCH` |
| 24 | Sales (Not Germany) | `IF NOT [Country] = "Germany" THEN [Sales] END` | `IF / SWITCH` |
| 25 | [Days to Ship (bin)] | `[Calculation_1613977548030509058]` | `See dax_measures.dax` |
| 26 | Order Date (Year) | `DATENAME("year", [Order_Date])` | `See dax_measures.dax` |
| 27 | Order Date (Quarter) | `DATENAME("quarter", [Order_Date])` | `See dax_measures.dax` |
| 28 | Sales (OR) | `IF [Country] = "Germany" OR [Score] > 50 THEN [Sales] END` | `IF / SWITCH` |
| 29 | Sales (Ceiling) | `CEILING([Sales])` | `See dax_measures.dax` |
| 30 | Sales (Floor) | `FLOOR([Sales])` | `See dax_measures.dax` |
| 31 | Sales (Round) | `ROUND([Sales])` | `ROUND` |
| 32 | Sales (Round1) | `ROUND([Sales],1)` | `ROUND` |
| 33 | Full Name | `[First_Name] + "-" + [Last_Name]` | `See dax_measures.dax` |
| 34 | Full Product Name | `[Category] + ": " + [Product_Name]` | `See dax_measures.dax` |
| 35 | Phone (Country Code) | `SPLIT([Phone], "-",1)` | `See dax_measures.dax` |
| 36 | Phone (Area Code) | `SPLIT([Phone], "-",2)` | `See dax_measures.dax` |
| 37 | Phone (Number) | `SPLIT([Phone], "-",3) + "-"+ SPLIT([Phone], "-",4)` | `See dax_measures.dax` |
| 38 | Phone (Replace) | `REPLACE(REPLACE([Phone], "+", "00"), "-", "")` | `See dax_measures.dax` |
| 39 | Address (Street) | `MID([Address], 9)` | `MID` |
| 40 | URL (Domain) | `MID([Product_Image], 9)` | `MID` |
| 41 | URL (Protocoll) | `LEFT([Product_Image], 5)` | `LEFT` |
| 42 | Phone (Country Code Find) | `LEFT([Phone],FIND([Phone], "-")-1)` | `LEFT` |
| 43 | Phone (Find -) | `FIND([Phone], "-")` | `See dax_measures.dax` |
| 44 | Phone (FindNth2) | `FINDNTH([Phone], "-", 1)` | `See dax_measures.dax` |
| 45 | Products L | `LOWER([Product_Name])` | `LOWER` |
| 46 | Products U | `UPPER([Product_Name])` | `UPPER` |
| 47 | Profit (ZN) | `ZN([Profit])` | `IF(ISBLANK, 0)` |
| 48 | Profit (IFNULL) | `IFNULL([Profit],1)` | `See dax_measures.dax` |
| 49 | Customer Email (IFNULL) | `IFNULL([Customer_Email], "unknown")` | `See dax_measures.dax` |
| 50 | Profit (ISNULL) | `ISNULL([Profit])` | `ISBLANK` |
| 51 | Country (IF) | `IF [Country] = "Germany" THEN "DE" END` | `IF / SWITCH` |
| 52 | Revenue | `[Quantity]* [Unit_Price]` | `See dax_measures.dax` |
| 53 | Running Total Revenue | `RUNNING_SUM(SUM([Calculation_278097305858076694]))` | `CALCULATE + FILTER(ALL)` |
| 54 | Total Revenue | `SUM([Calculation_278097305858076694])` | `SUM` |
| 55 | Country (IF, ELSE) | `IF [Country] = "Germany" THEN "DE" ELSE "N/A" END` | `IF / SWITCH` |
| 56 | Country (IIF) | `IIF([Country] = "Germany","DE", "N/A")` | `IF` |
| 57 | Country (IF, ELSE, ELSEIF) | `IF [Country] = "Germany" THEN "DE" ELSEIF [Country] = "France" THEN "FR" EL...` | `IF / SWITCH` |
| 58 | Country (Case When) | `CASE [Country]  WHEN "Germany" THEN "DE" WHEN "France" THEN "FR" WHEN "USA...` | `SWITCH(TRUE())` |
| 59 | Phone - Split 1 | `TRIM( SPLIT( [Phone], "-", 1 ) )` | `See dax_measures.dax` |
| 60 | Phone - Split 2 | `TRIM( SPLIT( [Phone], "-", 2 ) )` | `See dax_measures.dax` |
| 61 | Phone - Split 3 | `TRIM( SPLIT( [Phone], "-", 3 ) )` | `See dax_measures.dax` |
| 62 | Phone - Split 4 | `TRIM( SPLIT( [Phone], "-", 4 ) )` | `See dax_measures.dax` |
| 63 | Product Image (Domain) | `SPLIT( SPLIT( [Product_Image], "://", 2 ), "/", 1 )` | `See dax_measures.dax` |
| 64 | Product Image (Fragment) | `SPLIT( [Product_Image], "#", 2 )` | `See dax_measures.dax` |
| 65 | Product Image (Path) | `MID( SPLIT( SPLIT( [Product_Image], "#", 1 ), "?", 1 ), FIND( [Product_Image]...` | `MID` |
| 66 | Product Image (Query) | `SPLIT( SPLIT( [Product_Image], "#", 1 ), "?", 2 )` | `See dax_measures.dax` |
| 67 | Product Image (Scheme) | `SPLIT( [Product_Image], "://", 1 )` | `See dax_measures.dax` |
| 68 | URL (Extension) | `RIGHT([Product_Image], 3)` | `RIGHT` |

### Section 12 - Table Calculations

- **Source**: `tableau-source/course/tableau-files/Section 12 - Table Calculations/`
- **Output**: `conversion-output/section-12-table-calculations/`
- **Artifacts**: `dax_measures.dax`, `model.tmdl`, `layout.json`, `theme.json`, `power_query.pq`, `validation_report.md`

| # | Tableau Calculated Field | Original Tableau Formula | DAX Pattern |
|---|------------------------|--------------------------|-------------|
| 1 | [Calculation1] | `ZN(SUM([Sales])) - LOOKUP(ZN(SUM([Sales])), -1)` | `CALCULATE + DATEADD` |
| 2 | [Calculation2] | `RUNNING_SUM(SUM([Sales]))` | `CALCULATE + FILTER(ALL)` |
| 3 | [Calculation3] | `RANK_PERCENTILE(SUM([Sales]))` | `SUM` |
| 4 | [Calculation4] | `ZN(SUM([Sales])) - LOOKUP(ZN(SUM([Sales])), -1)` | `CALCULATE + DATEADD` |
| 5 | [Calculation1 1] | `(ZN([Calculation1]) - LOOKUP(ZN([Calculation1]), -1)) / ABS(LOOKUP(ZN([Calcul...` | `CALCULATE + DATEADD` |
| 6 | [Calculation1] | `RUNNING_SUM(SUM([Sales]))` | `CALCULATE + FILTER(ALL)` |
| 7 | Calculation2 | `LAST()` | `See dax_measures.dax` |
| 8 | Lookup | `LOOKUP(SUM([Sales]),2)` | `CALCULATE + DATEADD` |
| 9 | First (Sales) | `IF FIRST() = 0 THEN SUM([Sales]) END` | `SUM` |
| 10 | Rank (Sales) | `RANK(SUM([Sales]))` | `RANKX(ALLSELECTED)` |
| 11 | Last | `LAST()` | `See dax_measures.dax` |
| 12 | First | `FIRST()` | `See dax_measures.dax` |
| 13 | Index | `INDEX()` | `RANKX` |
| 14 | Running (Sales) | `RUNNING_SUM(SUM(Sales))` | `CALCULATE + FILTER(ALL)` |

### Section 13 - Multi-Measures

- **Source**: `tableau-source/course/tableau-files/Section 13 - Multi-Measures/`
- **Output**: `conversion-output/section-13-multi-measures/`
- **Artifacts**: `dax_measures.dax`, `model.tmdl`, `layout.json`, `theme.json`, `power_query.pq`, `validation_report.md`

*No calculated fields -- conversion focuses on data model and layout.*

### Section 13 - Tableau 63 Charts

- **Source**: `tableau-source/course/tableau-files/Section 13 - Tableau 63 Charts/`
- **Output**: `conversion-output/section-13-tableau-63-charts/`
- **Artifacts**: `dax_measures.dax`, `model.tmdl`, `layout.json`, `theme.json`, `power_query.pq`, `validation_report.md`

| # | Tableau Calculated Field | Original Tableau Formula | DAX Pattern |
|---|------------------------|--------------------------|-------------|
| 1 | Select Country | `"USA"` | `See dax_measures.dax` |
| 2 | Select Discount | `0.18` | `See dax_measures.dax` |
| 3 | Select Profit Ratio | `0.1` | `See dax_measures.dax` |
| 4 | Highlighted Country | `[Country] = [Parameters].[Parameter 1]` | `See dax_measures.dax` |
| 5 | Sales 2021 | `IF YEAR([Order_Date]) = 2021 THEN [Sales] END` | `IF / SWITCH` |
| 6 | Sales 2022 | `IF YEAR([Order_Date]) = 2022 THEN [Sales] END` | `IF / SWITCH` |
| 7 | Nr of Orders per Customer | `{ FIXED [Customer_ID] : COUNT([Order_ID])}` | `CALCULATE + ALLEXCEPT` |
| 8 | Profit Ratio | `SUM([Profit])/ SUM([Sales])` | `SUM` |
| 9 | Quadrant Color | `IF [Calculation_2330612859080679425] >= [Parameters].[Parameter 3] AND AVG([D...` | `AVERAGE` |
| 10 | KPI Colors | `IF SUM([Sales]) > 50000 THEN "Green" ELSEIF  SUM([Sales]) <= 50000 AND SUM([...` | `SUM` |
| 11 | KPI Colors of Two Years | `IF SUM([Calculation_1361775988060233740]) >= SUM([Calculation_136177598805979...` | `SUM` |
| 12 | Quantity (bin) | `[Quantity]` | `See dax_measures.dax` |
| 13 | Select Country | `"USA"` | `See dax_measures.dax` |
| 14 | Select Discount | `0.18` | `See dax_measures.dax` |
| 15 | Select Profit Ratio | `0.1` | `See dax_measures.dax` |

**Parameters**: Select Country, Select Discount, Select Profit Ratio

### Section 14 - Tableau Dashboard

- **Source**: `tableau-source/course/tableau-files/Section 14 - Tableau Dashboard/`
- **Output**: `conversion-output/section-14-tableau-dashboard/`
- **Artifacts**: `dax_measures.dax`, `model.tmdl`, `layout.json`, `theme.json`, `power_query.pq`, `validation_report.md`

| # | Tableau Calculated Field | Original Tableau Formula | DAX Pattern |
|---|------------------------|--------------------------|-------------|
| 1 | Category (Short) | `[Category]` | `See dax_measures.dax` |
| 2 | Logic 400 | `[Sales] < 400` | `See dax_measures.dax` |
| 3 | Country (Short) | `[Country]` | `See dax_measures.dax` |

### Section 15 - Sales & Customer Dashboards

- **Source**: `tableau-source/course/tableau-files/Section 15 - Sales & Customer Dashboards/`
- **Output**: `conversion-output/section-15-sales-customer-dashboards/`
- **Artifacts**: `dax_measures.dax`, `model.tmdl`, `layout.json`, `theme.json`, `power_query.pq`, `validation_report.md`

| # | Tableau Calculated Field | Original Tableau Formula | DAX Pattern |
|---|------------------------|--------------------------|-------------|
| 1 | Select Year | `2023` | `See dax_measures.dax` |
| 2 | % Diff Orders | `(COUNTD([CY Sales (copy)_3221481164594982929]) - COUNTD([PY Sales (copy)_3221...` | `DISTINCTCOUNT` |
| 3 | % Diff Customers | `(COUNTD([CY Sales (copy)_3221481164532666369]) - COUNTD([CY Customers (copy)_...` | `DISTINCTCOUNT` |
| 4 | % Diff Quantity | `(SUM([CY Sales (copy) (copy)_237846410424193025]) - SUM([PY Sales (copy) (cop...` | `SUM` |
| 5 | % Diff Profit | `(SUM([CY Sales (copy)_237846410424180736]) - SUM([PY Sales (copy)_23784641042...` | `SUM` |
| 6 | % Diff Sales per Customers | `([CY Profit (copy)_3221481164532895746] - [CY Sales per Customer (copy)_32214...` | `See dax_measures.dax` |
| 7 | PY Customers | `IF YEAR([Order Date])= [Parameters].[Parameter 1]-1 THEN [Customer ID]  END` | `IF / SWITCH` |
| 8 | CY Sales per Customer | `SUM([Calculation_721701895334993921]) / COUNTD([CY Sales (copy)_3221481164532...` | `DISTINCTCOUNT` |
| 9 | CY Quantity | `IF YEAR([Order Date]) = [Parameters].[Parameter 1] THEN [Quantity] END` | `IF / SWITCH` |
| 10 | CY Profit | `IF YEAR([Order Date]) = [Parameters].[Parameter 1] THEN [Profit] END` | `IF / SWITCH` |
| 11 | CY Customers | `IF YEAR([Order Date])= [Parameters].[Parameter 1] THEN [Customer ID]  END` | `IF / SWITCH` |
| 12 | CY Orders | `IF YEAR([Order Date]) = [Parameters].[Parameter 1] THEN [Order ID] END` | `IF / SWITCH` |
| 13 | PY Sales | `IF YEAR([Order Date]) = [Parameters].[Parameter 1]-1 THEN [Sales] END` | `IF / SWITCH` |
| 14 | PY Sales per Customer | `SUM([CY Sales (copy)_721701895335804930]) / COUNTD([CY Customers (copy)_32214...` | `DISTINCTCOUNT` |
| 15 | Current Year | `[Parameters].[Parameter 1]` | `See dax_measures.dax` |
| 16 | Previous Year | `[Parameters].[Parameter 1]-1` | `See dax_measures.dax` |
| 17 | KPI CY Less PY | `IF SUM([Calculation_721701895334993921]) < SUM([CY Sales (copy)_7217018953358...` | `SUM` |
| 18 | KPI Sales Avg | `IF SUM([Calculation_721701895334993921]) > WINDOW_AVG(SUM([Calculation_721701...` | `AVERAGEX(ALLSELECTED)` |
| 19 | CY Sales | `IF YEAR([Order Date]) = [Parameters].[Parameter 1] THEN [Sales] END` | `IF / SWITCH` |
| 20 | Order Date (Year) | `YEAR([Order Date])` | `YEAR` |
| 21 | % Diff Sales | `(SUM([Calculation_721701895334993921]) - SUM([CY Sales (copy)_721701895335804...` | `SUM` |
| 22 | Min/Max Sales | `IF SUM([Calculation_721701895334993921]) = WINDOW_MAX(SUM([Calculation_721701...` | `MAXX(ALLSELECTED)` |
| 23 | {SUM([CY Sales])} | `{SUM([Calculation_721701895334993921])}` | `SUM` |
| 24 | Nr of Orders per Customers | `{ FIXED [CY Sales (copy)_3221481164532666369]: COUNTD([CY Sales (copy)_322148...` | `CALCULATE + ALLEXCEPT` |
| 25 | KPI Profit Avg | `IF SUM([CY Sales (copy)_237846410424180736]) > WINDOW_AVG(SUM([CY Sales (copy...` | `AVERAGEX(ALLSELECTED)` |
| 26 | Min/Max Sales Per Customers | `IF [CY Profit (copy)_3221481164532895746] = WINDOW_MAX([CY Profit (copy)_3221...` | `MAXX(ALLSELECTED)` |
| 27 | Min/Max Customers | `IF COUNTD([CY Sales (copy)_3221481164532666369]) = WINDOW_MAX(COUNTD([CY Sale...` | `MAXX(ALLSELECTED)` |
| 28 | Min/Max Quantity | `IF SUM([CY Sales (copy) (copy)_237846410424193025]) = WINDOW_MAX(SUM([CY Sale...` | `MAXX(ALLSELECTED)` |
| 29 | Min/Max Profit | `IF SUM([CY Sales (copy)_237846410424180736]) = WINDOW_MAX(SUM([CY Sales (copy...` | `MAXX(ALLSELECTED)` |
| 30 | Min/Max Orders | `IF COUNTD([CY Sales (copy)_3221481164594982929]) = WINDOW_MAX(COUNTD([CY Sale...` | `MAXX(ALLSELECTED)` |
| 31 | PY Quantity | `IF YEAR([Order Date]) = [Parameters].[Parameter 1]-1 THEN [Quantity] END` | `IF / SWITCH` |
| 32 | PY Profit | `IF YEAR([Order Date]) = [Parameters].[Parameter 1]-1 THEN [Profit] END` | `IF / SWITCH` |
| 33 | PY Orders | `IF YEAR([Order Date]) = [Parameters].[Parameter 1]-1 THEN [Order ID] END` | `IF / SWITCH` |
| 34 | Select Year | `2023` | `See dax_measures.dax` |

**Parameters**: Select Year

---

## Conversion Methodology

### Tableau to DAX Translation Rules

| Tableau Pattern | DAX Equivalent | Notes |
|----------------|----------------|-------|
| `{ FIXED [dim]: AGG([col]) }` | `CALCULATE(AGG(t[col]), ALLEXCEPT(t, t[dim]))` | LOD Fixed |
| `{ EXCLUDE [dim]: AGG([col]) }` | `CALCULATE(AGG(t[col]), ALL(t[dim]))` | LOD Exclude |
| `{ INCLUDE [dim]: AGG([col]) }` | `SUMMARIZE + ADDCOLUMNS` | LOD Include |
| `RUNNING_SUM(SUM([col]))` | `CALCULATE(SUM(t[col]), FILTER(ALL(t[date]), t[date] <= CurrentDate))` | Table calc |
| `RANK(SUM([col]))` | `RANKX(ALLSELECTED(t[dim]), [measure], , DESC, Dense)` | Ranking |
| `WINDOW_MAX/MIN/AVG` | `MAXX/MINX/AVERAGEX(ALLSELECTED(...))` | Window func |
| `LOOKUP(expr, -1)` | `CALCULATE([measure], DATEADD(Date[Date], -1, YEAR))` | Period offset |
| `COUNTD([col])` | `DISTINCTCOUNT(t[col])` | Distinct count |
| `ZN(expr)` | `IF(ISBLANK(expr), 0, expr)` | Null handling |
| `TOTAL(SUM([col]))` | `CALCULATE(SUM(t[col]), ALL(t))` | Grand total |
| `Parameters` | `GENERATESERIES + SELECTEDVALUE` | What-If param |

### Data Model Architecture

All conversions follow the **star schema** pattern:
- **Fact table**: Orders (sales transactions)
- **Dimension tables**: Customers, Products, Date
- **Relationships**: One-to-many from dimensions to fact table
- **Date table**: DAX-generated calendar (2020-2023) with Year, Month, Quarter columns

### Artifact Set (per workbook)

| File | Purpose |
|------|---------|
| `dax_measures.dax` | All Tableau calculated fields converted to DAX (with original formula comments) |
| `model.tmdl` | Tabular Model Definition Language semantic model |
| `layout.json` | Power BI layout specification with page/visual positions |
| `theme.json` | Power BI theme (colors, fonts, styling) |
| `power_query.pq` | Power Query M scripts for CSV data import and transformation |
| `validation_report.md` | Conversion validation results with PASS/FAIL status |
