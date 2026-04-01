# BEP MES Tableau-to-Power BI Conversion Outline

## Windsurf FedRAMP Conversion Workflow — Step-by-Step

> **Context**: The Bureau of Engraving and Printing (BEP) uses Tableau Server and Tableau Desktop as core enterprise analytics components within the Manufacturing Execution System (MES) at both the Eastern Currency Facility (ECF) and Western Currency Facility (WCF). This guide outlines the exact steps Windsurf will perform to convert Tableau workbooks into Power BI equivalents, validated against the same production datasets.

---

## Repository Contents Inventory

### Tableau Workbook Files (17 .twbx files)

| # | File | Calculated Fields | Dashboards | Key Conversion Challenges |
|---|------|-------------------|------------|--------------------------|
| 1 | `projects/sales-dashboard-project/Sales & Customer Dashboards.twbx` | 30+ | Sales Dashboard, Customer Dashboard | LOD FIXED expressions, WINDOW_MAX/MIN, parameters, YoY comparisons, KPI indicators |
| 2 | `projects/hr-dashboard-project/HR Dashboard.twbx` | 20+ | HR Summary, HR Details | DATEDIFF, CASE/WHEN, ISNULL, TOTAL(), RANK, WINDOW_MAX, INDEX() |
| 3 | `course/tableau-files/Section 12 - LOD Expressions.twbx` | 8 | — | FIXED, INCLUDE, EXCLUDE LOD expressions |
| 4 | `course/tableau-files/Section 12 - Table Calculations.twbx` | 15 | — | RUNNING_SUM, RANK, RANK_PERCENTILE, LOOKUP, FIRST, LAST, INDEX |
| 5 | `course/tableau-files/Section 12 - Row Level Calculations (Functions).twbx` | 131 | Lower, Upper 2 | LOWER, UPPER, LEN, TRIM, COUNTD, string functions, date functions, type conversions |
| 6 | `course/tableau-files/Section 12 - Aggregate Calculations.twbx` | 14 | — | SUM, AVG, COUNT, COUNTD, MAX, MIN, conditional aggregations |
| 7 | `course/tableau-files/Section 10 - Parameters.twbx` | 12 | — | Dynamic dimension/measure switching via CASE, KPI thresholds, Top N, bin sizing |
| 8 | `course/tableau-files/Section 13 - Tableau 63 Charts.twbx` | 39 | 8 dashboards | 63 chart types, parameterized filtering, year-over-year calcs |
| 9 | `course/tableau-files/Section 14 - Tableau Dashboard.twbx` | 3 | Sales Dashboard | Dashboard layout, formatting, containers |
| 10 | `course/tableau-files/Section 11 - Actions.twbx` | 9 | 4 dashboards | Filter actions, highlight actions, URL actions, navigation |
| 11 | `course/tableau-files/Section 09 - Filtering Data.twbx` | 5 | — | Dimension filters, measure filters, date filters, context filters |
| 12 | `course/tableau-files/Section 08 - Organizing Data.twbx` | 0 | — | Groups, sets, hierarchies, bins |
| 13 | `course/tableau-files/Section 07 - Renaming.twbx` | 0 | — | Aliases, default properties, formatting |
| 14 | `course/tableau-files/Section 06 - Metadata.twbx` | 2 | 2 dashboards | Data types, continuous vs discrete |
| 15 | `course/tableau-files/Section 05 - Data Sources.twbx` | 1 | — | Joins, unions, data source connections |
| 16 | `course/tableau-files/Section 13 - Multi-Measures.twbx` | 0 | Dashboard 1 | Measure Names/Values, combined axis |
| 17 | `course/tableau-files/Section 15 - Tableau Sales & Customer Dashboards.twbx` | 30+ | Sales Dashboard, Customer Dashboard | Full production-grade dashboard (duplicate of project version) |

### Datasets (CSV files)

| Dataset | Columns | BEP MES Analogy |
|---------|---------|-----------------|
| `Orders.csv` | Row ID, Order ID, Order Date, Ship Date, Ship Mode, Customer ID, Segment, Postal Code, Product ID, Sales, Quantity, Discount, Profit | **Production Orders** — Maps to BEP print orders: Order ID → Print Run ID, Ship Date → Delivery Date, Product ID → Denomination/Series, Quantity → Sheet Count, Profit → Cost Variance |
| `Customers.csv` | Customer ID, Customer Name | **Federal Reserve Banks (FRBs)** — BEP's "customers" are the 12 FRBs that order currency |
| `Products.csv` | Product ID, Category, Sub-Category, Product Name | **Currency Products** — Category → Currency/Security Docs, Sub-Category → Denomination ($1, $5, $20, $100), Product Name → Series/Variant |
| `Location.csv` | Postal Code, City, State, Region, Country/Region | **Facility Locations** — ECF (Washington DC) and WCF (Fort Worth TX), plus FRB distribution points |
| `USA Sales.csv` | Regional sales data | **Regional Distribution** — FRB district-level currency demand |
| `LOD.csv` | Customer/order/sales detail data | **Per-press run detail** — Granular production metrics by equipment/line |
| `dataset.csv` (HR) | Employee_ID, First Name, Last Name, Gender, State, City, Education Level, Birthdate, Hiredate, Termdate, Department, Job Title, Salary, Performance Rating | **BEP Workforce Analytics** — Employee lifecycle, department-level staffing for ECF/WCF operations |

---

## Phase 1: Workbook Parsing & Extraction

### What Windsurf Does
Open each `.twbx` file and extract the internal XML structure. A `.twbx` is a ZIP archive containing:
- A `.twb` file (XML workbook definition)
- `/Data/` folder with Hyper extracts (`.hyper` files)
- `/Image/` folder with embedded dashboard images

### Step-by-Step Instructions for Windsurf

```
Step 1.1: Parse .twbx archive structure
- Ask Windsurf: "Unzip the Sales & Customer Dashboards.twbx file and show me its 
  internal structure — list all files, their sizes, and the XML root elements."

Step 1.2: Extract calculated fields inventory
- Ask Windsurf: "Parse the .twb XML file inside the Sales & Customer Dashboards.twbx 
  and extract ALL calculated fields. For each field, show me:
  (a) field name/caption
  (b) Tableau formula
  (c) data type
  (d) whether it uses LOD expressions, table calculations, or parameters"

Step 1.3: Map data sources
- Ask Windsurf: "Identify all data source connections in this workbook. 
  Show me the connection type (CSV, Hyper extract, live connection), 
  the tables/files referenced, and any joins or relationships defined."

Step 1.4: Extract dashboard layout metadata
- Ask Windsurf: "Parse the dashboard XML sections and extract the layout:
  which worksheets are placed where, container structure (horizontal/vertical), 
  sizing (fixed vs automatic), filter controls, and parameter controls."
```

### Files Involved
- **Input**: `projects/sales-dashboard-project/Sales & Customer Dashboards.twbx`
- **Output**: Structured JSON or YAML inventory of all workbook components

### BEP MES Relevance
BEP's Tableau Server hosts workbooks that track press utilization, sheet counts, spoilage rates, and FRB shipment schedules. This parsing step mirrors what Deloitte developers would do when inventorying BEP's existing Tableau assets before migration.

---

## Phase 2: Calculated Field Conversion (Tableau → DAX)

### What Windsurf Does
Convert every Tableau calculated field formula into equivalent Power BI DAX (Data Analysis Expressions) measures or calculated columns.

### Conversion Mapping Reference

| Tableau Construct | Power BI DAX Equivalent | Example from Repo |
|-------------------|------------------------|-------------------|
| `IF/THEN/ELSE/END` | `IF()` function | `CY Sales = IF YEAR([Order Date]) = [Param] THEN [Sales] END` → `CY Sales = IF(YEAR(Orders[Order Date]) = [Select Year], Orders[Sales], BLANK())` |
| `{ FIXED [Dim]: AGG([Measure]) }` | `CALCULATE()` with `ALLEXCEPT()` | `{ FIXED [Category]: SUM([Sales]) }` → `Sales By Category = CALCULATE(SUM(Orders[Sales]), ALLEXCEPT(Orders, Orders[Category]))` |
| `{ INCLUDE [Dim]: AGG([Measure]) }` | `CALCULATE()` with `VALUES()` | `{ INCLUDE [First_Name]: SUM([Sales]) }` → add dimension to filter context |
| `{ EXCLUDE [Dim]: AGG([Measure]) }` | `CALCULATE()` + `ALL()` on excluded dim | `{ EXCLUDE [Sub_Category]: SUM([Sales]) }` → `CALCULATE(SUM(Orders[Sales]), ALL(Orders[Sub_Category]))` |
| `RUNNING_SUM(SUM([Sales]))` | `SUMX(FILTER(ALL(...)))` or window functions | Running total across sorted dimension |
| `RANK(SUM([Sales]))` | `RANKX()` | `RANKX(ALL(Products), SUM(Orders[Sales]))` |
| `WINDOW_MAX(SUM([Sales]))` | `MAXX(ALLSELECTED(...))` | Window-scoped max for sparkline highlighting |
| `WINDOW_MIN(SUM([Sales]))` | `MINX(ALLSELECTED(...))` | Window-scoped min for sparkline highlighting |
| `LOOKUP(SUM([Sales]), -1)` | `OFFSET()` or `PREVIOUSMONTH()` | Prior period comparison |
| `INDEX()` | `RANKX()` or row number pattern | Sequential row numbering |
| `FIRST()` / `LAST()` | `TOPN()` / position-based patterns | First/last position markers |
| `RANK_PERCENTILE()` | `PERCENTILEX.INC()` / `RANKX()` | Percentile-based ranking |
| `TOTAL()` | `CALCULATE(SUM(), ALL())` | Grand total for % calculations |
| `DATEDIFF('year', [Date1], [Date2])` | `DATEDIFF([Date1], [Date2], YEAR)` | Age calculation, tenure |
| `CASE [Param] WHEN 'X' THEN [A]...` | `SWITCH([Param], "X", [A], ...)` | Dynamic dimension/measure |
| `COUNTD()` | `DISTINCTCOUNT()` | Unique customer/order count |
| `[Parameters].[Param1]` | What-If Parameter or Slicer | Year selector, threshold, Top N |
| `ZN()` (zero if null) | `IF(ISBLANK(), 0, value)` | Null handling |
| `ISNULL()` | `ISBLANK()` | Status classification |

### Step-by-Step Instructions for Windsurf

```
Step 2.1: Convert Sales Dashboard calculated fields
- Ask Windsurf: "Take each Tableau calculated field from the Sales & Customer 
  Dashboards workbook and convert it to DAX. Create a file called 
  'sales_dashboard_dax_measures.md' that shows:
  (a) Original Tableau field name and formula
  (b) Converted DAX measure or calculated column
  (c) Conversion notes (any differences in behavior to watch for)
  
  Here are the key fields to convert:
  - CY Sales: IF YEAR([Order Date]) = [Parameters].[Parameter 1] THEN [Sales] END
  - PY Sales: IF YEAR([Order Date]) = [Parameters].[Parameter 1]-1 THEN [Sales] END
  - % Diff Sales: (SUM([CY Sales]) - SUM([PY Sales])) / SUM([PY Sales])
  - CY Customers: IF YEAR([Order Date])= [Parameters].[Parameter 1] THEN [Customer ID] END
  - Nr of Orders per Customers: { FIXED [Customer ID]: COUNTD([Order ID]) }
  - Min/Max Sales: IF SUM([CY Sales]) = WINDOW_MAX(SUM([CY Sales])) THEN ...
  - KPI CY Less PY: IF SUM([PY Sales]) < SUM([CY Sales]) THEN '⬤' ELSE '' END
  - KPI Sales Avg: IF SUM([CY Sales]) > WINDOW_AVG(SUM([CY Sales])) THEN 'Above' ELSE 'Below' END
  - CY Sales per Customer: SUM([CY Sales]) / COUNTD([Customer ID])
  - % Diff Sales per Customers
  - Select Year parameter (integer, default 2023)"

Step 2.2: Convert LOD Expressions
- Ask Windsurf: "Convert these Tableau LOD expressions to DAX:
  - { FIXED [Category] : SUM([Sales]) }
  - { EXCLUDE [Category] : SUM([Sales]) }
  - { INCLUDE [First_Name] : SUM([Sales]) }
  - { FIXED [Customer_ID]: COUNT([Order_ID]) }
  - { EXCLUDE [Sub_Category]: SUM([Sales of Tables]) }
  Show the DAX equivalent using CALCULATE(), ALLEXCEPT(), ALL(), etc."

Step 2.3: Convert Table Calculations
- Ask Windsurf: "Convert these Tableau table calculations to DAX:
  - RUNNING_SUM(SUM([Sales]))
  - RANK(SUM([Sales]))
  - RANK_PERCENTILE(SUM([Sales]))
  - LOOKUP(SUM([Sales]), -1)   (prior period value)
  - ZN(SUM([Sales])) - LOOKUP(ZN(SUM([Sales])), -1)  (period-over-period difference)
  - (ZN([Diff]) - LOOKUP(ZN([Diff]), -1)) / ABS(LOOKUP(ZN([Diff]), -1))  (% change)
  Use DAX window functions (OFFSET, INDEX, WINDOW) where available in modern DAX."

Step 2.4: Convert Parameters to What-If Parameters
- Ask Windsurf: "Convert these Tableau parameters to Power BI equivalents:
  - Select Year (integer, default 2023) → What-If parameter or slicer
  - Choose Dimension (string: 'Country'|'Category') → field parameter
  - Choose Measure (string: 'Sales'|'Profit'|'Quantity') → field parameter  
  - Choose Threshold (integer, default 10000) → What-If parameter
  - Choose Top N Products (integer, default 15) → What-If parameter
  - Choose Size of Bins (real, default 20) → What-If parameter
  Show the GENERATESERIES() or NAMEOF() DAX for each."

Step 2.5: Convert HR Dashboard fields
- Ask Windsurf: "Convert these HR Dashboard Tableau fields to DAX:
  - Total Hired: COUNT([Employee_ID])
  - Total Terminated: COUNT(IF NOT ISNULL([Termdate]) THEN [Employee_ID] END)
  - Total Active: COUNT(IF ISNULL([Termdate]) THEN [Employee_ID] END)
  - Status: IF ISNULL([Termdate]) THEN 'Hired' ELSE 'Terminated' END
  - Location: CASE [State] WHEN 'New York' THEN 'HQ' ELSE 'Branch' END
  - Age: DATEDIFF('year', [Birthdate], TODAY())
  - Age Groups: IF [Age] < 25 THEN '>25' ELSEIF ... (5 buckets)
  - Length of Hire: IF ISNULL([Termdate]) THEN DATEDIFF(Hiredate, TODAY()) ELSE DATEDIFF(Hiredate, Termdate)
  - % Total Hired: [Total Hired] / TOTAL([Total Hired])
  - Highlight Max: WINDOW_MAX([Total Hired]) = [Total Hired]
  - Full Name: [First Name] + ' ' + [Last Name]"
```

### Files to Create
- `windsurf-conversion-guide/output/sales_dashboard_dax_measures.dax`
- `windsurf-conversion-guide/output/hr_dashboard_dax_measures.dax`
- `windsurf-conversion-guide/output/lod_to_calculate_mappings.dax`
- `windsurf-conversion-guide/output/table_calc_conversions.dax`
- `windsurf-conversion-guide/output/parameter_conversions.dax`

### BEP MES Relevance
BEP's Tableau workbooks contain calculated fields for:
- **Production yield** = maps to Sales/Profit calculations (output vs target)
- **Equipment utilization** = maps to LOD FIXED expressions (per-press aggregations)
- **Quality control** = maps to threshold parameters and KPI conditional logic
- **Workforce scheduling** = maps directly to HR Dashboard fields (staffing, tenure, location-based analytics for ECF/WCF)

---

## Phase 3: Data Model Conversion

### What Windsurf Does
Convert the Tableau data source definitions (joins, relationships, data types) into a Power BI data model using TMDL (Tabular Model Definition Language) or a Python-based Power BI dataset builder.

### Step-by-Step Instructions for Windsurf

```
Step 3.1: Define the Power BI data model schema
- Ask Windsurf: "Based on the CSV files in this repo, create a Power BI star schema 
  data model. The fact table is Orders.csv. The dimension tables are:
  - Customers.csv (join on Customer ID)
  - Products.csv (join on Product ID)
  - Location.csv (join on Postal Code)
  
  Create a TMDL model definition file (.tmdl) or a Python script that generates 
  the model.bim file with:
  - Table definitions with proper data types
  - Relationships (1:many) between fact and dimension tables
  - A Date table (auto-generated) for time intelligence
  - All DAX measures from Phase 2 added to the model"

Step 3.2: Create the HR data model
- Ask Windsurf: "Create a separate data model for the HR Dashboard using dataset.csv. 
  Include:
  - Proper data type mappings (dates, strings, integers)
  - A Date table for hire/term date analysis
  - Calculated columns: Status, Location, Age, Age Groups, Full Name, Length of Hire
  - All DAX measures from Step 2.5"

Step 3.3: Generate data type mapping report
- Ask Windsurf: "Create a data type mapping report showing:
  - Each CSV column → Tableau data type → Power BI data type
  - Any columns that need format conversion (e.g., EU date format DD/MM/YYYY)
  - Delimiter differences (semicolons in EU datasets vs commas)
  Flag any potential data loading issues."
```

### Files to Create
- `windsurf-conversion-guide/output/sales_model.tmdl` (or `sales_model.bim`)
- `windsurf-conversion-guide/output/hr_model.tmdl`
- `windsurf-conversion-guide/output/data_type_mapping.md`

### BEP MES Relevance
BEP's MES data flows through Oracle Data Integrator (ODI) into Oracle Analytics Server (OAS) and Tableau. The conversion to Power BI requires re-mapping these data pipelines. The star schema pattern (fact + dimension tables) mirrors BEP's production data:
- **Fact Table**: Print runs (order date, sheet count, spoilage, cost)
- **Dimensions**: Denomination, Press Equipment, Facility, FRB Customer, Calendar

---

## Phase 4: Dashboard Layout & Visualization Conversion

### What Windsurf Does
Map Tableau dashboard layouts, chart types, and visual formatting to Power BI equivalents.

### Visualization Type Mapping

| Tableau Visualization | Power BI Equivalent | Used In |
|----------------------|---------------------|---------|
| Bar Chart | Clustered Bar Chart | Sales Dashboard, 63 Charts |
| Line Chart (time series) | Line Chart | Sales trends, KPI sparklines |
| Area Chart (filled) | Area Chart | Sparklines in Sales Dashboard |
| KPI Card (text + indicator) | Card / Multi-row Card / New Card visual | Sales, Profit, Quantity, Customers KPIs |
| Map (filled/symbol) | ArcGIS Map / Filled Map | Location-based sales, FRB distribution |
| Scatter Plot | Scatter Chart | Customer analysis |
| Donut/Pie Chart | Donut Chart | HR department breakdown, Part-to-Whole |
| Bump Chart | Line Chart with rank-based Y axis | Ranking over time |
| Treemap | Treemap | Category breakdown |
| Highlight Table / Heatmap | Matrix with conditional formatting | Cross-tabulation |
| Lollipop Chart | Clustered Bar + Line (combo) | Ranking with reference |
| Waterfall Chart | Waterfall Chart (native) | Change analysis |
| Gantt Chart | Custom visual or matrix | Timeline/scheduling |
| Histogram | Histogram (custom visual) | Distribution analysis |
| Box-and-Whisker Plot | Box-and-Whisker (custom visual) | Distribution |
| Sparkline (embedded in table) | Sparklines column in Table/Matrix | Sales Dashboard subcategory trends |

### Step-by-Step Instructions for Windsurf

```
Step 4.1: Map Sales Dashboard layout
- Ask Windsurf: "Analyze the Sales Dashboard layout from the .twb XML:
  - List each container (horizontal/vertical) and its contents
  - Identify which worksheets appear where
  - Note sizing (fixed width/height or automatic)
  - Document filter controls and their positions
  - Document parameter controls and their positions
  Create a Power BI page layout specification that replicates this structure."

Step 4.2: Map Customer Dashboard layout
- Ask Windsurf: "Do the same for the Customer Dashboard. Note any:
  - Navigation/toggle buttons between Sales and Customer dashboards
  - Filter actions (click to filter)
  - Highlight actions
  - Cross-dashboard navigation"

Step 4.3: Map HR Dashboard layouts (Summary + Details)
- Ask Windsurf: "Analyze both HR dashboards (Summary and Details):
  - Summary: KPI cards, department donut, location breakdown, age distribution
  - Details: Employee-level detail table with conditional formatting
  - Navigation between Summary and Details pages
  Create Power BI page specifications for both."

Step 4.4: Generate Power BI theme file
- Ask Windsurf: "Extract the color palette, font choices, and formatting from the 
  Tableau workbooks. Generate a Power BI theme JSON file (.json) that replicates 
  the visual styling. Include:
  - Primary/secondary colors
  - Font family and sizes for titles, labels, values
  - Background colors
  - Border styles
  - Conditional formatting rules (above/below average, min/max highlights)"
```

### Files to Create
- `windsurf-conversion-guide/output/sales_dashboard_layout.json`
- `windsurf-conversion-guide/output/customer_dashboard_layout.json`
- `windsurf-conversion-guide/output/hr_dashboard_layouts.json`
- `windsurf-conversion-guide/output/powerbi_theme.json`

### BEP MES Relevance
BEP's Tableau dashboards visualize:
- **Production Dashboard**: Real-time press output, spoilage rates, order fulfillment (maps to Sales Dashboard pattern)
- **Quality Dashboard**: Defect tracking by denomination, press, facility (maps to the filtering + parameter patterns)
- **Workforce Dashboard**: Staffing levels at ECF/WCF, contractor vs federal employee ratios (maps directly to HR Dashboard)
- **Distribution Dashboard**: FRB shipment tracking by region (maps to geographic/map visualizations)

---

## Phase 5: Filter & Interactivity Conversion

### What Windsurf Does
Convert Tableau filter actions, highlight actions, URL actions, and parameter-driven interactivity to Power BI equivalents.

### Step-by-Step Instructions for Windsurf

```
Step 5.1: Convert filter actions
- Ask Windsurf: "In the Sales Dashboard, the following interactions exist:
  - Click a subcategory bar → filters the sparkline area chart
  - Click a map region → filters all visuals on the page
  - Year parameter slider → recalculates CY/PY for all measures
  
  Create the equivalent Power BI interactions:
  - Cross-filtering between visuals (edit interactions)
  - Slicer for year selection (What-If parameter)
  - Drill-through pages for detail views
  Document these as a Power BI interaction specification."

Step 5.2: Convert dashboard navigation
- Ask Windsurf: "The Tableau workbook uses image-based toggle buttons to switch 
  between Sales Dashboard and Customer Dashboard. In Power BI:
  - Create page navigation buttons with active/inactive icon states
  - Use bookmarks for toggle behavior
  - Replicate the show/hide filter panel toggle
  Document the bookmark and button configuration."

Step 5.3: Convert highlight actions
- Ask Windsurf: "The Highlight Dashboard in the Actions workbook uses Tableau 
  highlight actions to emphasize selected data points. Convert to Power BI:
  - Use Edit Interactions → Highlight mode
  - Or use conditional formatting with selected/unselected states
  Document which approach to use for each visual."
```

### Files to Create
- `windsurf-conversion-guide/output/interactions_spec.md`
- `windsurf-conversion-guide/output/navigation_bookmarks.json`

### BEP MES Relevance
BEP production managers need interactive dashboards that let them:
- Filter by facility (ECF/WCF), denomination, press line, shift
- Drill from summary KPIs down to individual print run details
- Toggle between production views (real-time vs historical)
- Navigate between operational dashboards (production, quality, workforce)

---

## Phase 6: Automated Validation

### What Windsurf Does
Create Python validation scripts that prove the Tableau-to-DAX conversion produces identical results. This is the key differentiator — no need for Tableau or Power BI installed.

### Step-by-Step Instructions for Windsurf

```
Step 6.1: Build validation framework
- Ask Windsurf: "Create a Python validation script (validate_conversion.py) that:
  1. Loads the CSV datasets (Orders, Customers, Products, Location)
  2. Implements each original Tableau formula in Python (as baseline truth)
  3. Implements each converted DAX formula in Python (simulating DAX semantics)
  4. Runs both against the same data
  5. Compares outputs and reports:
     - PASS: Results match exactly
     - WARN: Results match within floating-point tolerance
     - FAIL: Results differ
  6. Generates a conversion_validation_report.md with results
  
  Start with the Sales Dashboard fields:
  - CY Sales (year filter)
  - PY Sales (prior year filter)
  - % Diff Sales (YoY percentage change)
  - Nr of Orders per Customer (LOD FIXED → CALCULATE)
  - Min/Max Sales (WINDOW_MAX/MIN → MAXX/MINX ALLSELECTED)
  - KPI Sales Avg (WINDOW_AVG comparison → AVERAGEX ALLSELECTED)"

Step 6.2: Validate LOD conversions
- Ask Windsurf: "Extend the validation script to test LOD expression conversions:
  - FIXED → CALCULATE + ALLEXCEPT: Verify category-level totals match
  - INCLUDE → CALCULATE + added dimension: Verify grain-level totals match
  - EXCLUDE → CALCULATE + ALL(dim): Verify excluded-dimension totals match
  Run against the LOD.csv dataset."

Step 6.3: Validate HR Dashboard conversions
- Ask Windsurf: "Extend validation for HR Dashboard fields:
  - Total Hired / Terminated / Active counts
  - Age calculation and Age Group bucketing
  - Location mapping (State → HQ/Branch)
  - % Total Hired (with TOTAL → ALL equivalent)
  Run against dataset.csv."

Step 6.4: Generate conversion accuracy report
- Ask Windsurf: "Generate a final conversion_report.md that summarizes:
  - Total fields converted: X
  - Validation results: X passed, X warnings, X failed
  - Conversion coverage by category:
    - Simple IF/THEN: X/X passed
    - LOD Expressions: X/X passed
    - Table Calculations: X/X passed
    - Parameters: X/X passed
    - Aggregate Functions: X/X passed
  - Any fields requiring manual review
  Format this as a professional report suitable for showing BEP stakeholders."
```

### Files to Create
- `windsurf-conversion-guide/output/validate_conversion.py`
- `windsurf-conversion-guide/output/conversion_validation_report.md`

### BEP MES Relevance
BEP operates under FIPS 199 Moderate-to-High security classification. Any migration of analytics systems requires **formal validation** that the new system produces identical results. This automated validation framework gives BEP's IV&V (Independent Verification & Validation) team auditable proof that the Power BI implementation is functionally equivalent to the Tableau original.

---

## Phase 7: Power BI Output Generation

### What Windsurf Does
Generate Power BI-compatible output files that can be imported directly into Power BI Desktop.

### Step-by-Step Instructions for Windsurf

```
Step 7.1: Generate PBIX-compatible dataset
- Ask Windsurf: "Create a Python script (generate_powerbi_dataset.py) that:
  1. Reads the CSV files
  2. Handles EU format issues (semicolons, decimal commas)
  3. Creates a clean, Power BI-ready dataset with proper:
     - Date columns parsed to datetime
     - Numeric columns with correct precision
     - String columns trimmed and standardized
  4. Outputs cleaned CSVs to a /powerbi-ready/ folder
  5. Generates a Power Query M script (.pq) for each table's 
     transformation steps (so a PBI developer can paste into Advanced Editor)"

Step 7.2: Generate DAX measures file
- Ask Windsurf: "Compile ALL converted DAX measures into a single organized file:
  - Group by dashboard/purpose
  - Include comments explaining the original Tableau formula
  - Format for easy copy-paste into Power BI Desktop's measure editor
  - Use a .dax extension so it's syntax-highlighted in editors"

Step 7.3: Generate TMDL model files
- Ask Windsurf: "If targeting Power BI developer mode (TMDL), generate the full 
  model definition:
  - /definition/tables/*.tmdl — one file per table
  - /definition/relationships.tmdl — all relationships  
  - /definition/measures.tmdl — all measures
  - /definition/model.tmdl — model metadata
  This allows direct import into Power BI Desktop via developer mode or 
  Tabular Editor."
```

### Files to Create
- `windsurf-conversion-guide/output/powerbi-ready/` (cleaned CSVs)
- `windsurf-conversion-guide/output/all_dax_measures.dax`
- `windsurf-conversion-guide/output/power_query_transforms.pq`
- `windsurf-conversion-guide/output/tmdl/` (TMDL model files)

### BEP MES Relevance
BEP's migration from Tableau to Power BI must produce deployable artifacts that:
- Work within BEP's Microsoft 365 GCC High environment
- Integrate with BEP's existing Oracle Data Integrator (ODI) data pipelines
- Support BEP's IT governance and change management processes
- Enable BEP analysts to maintain and extend dashboards independently

---

## Customer-Specific Dashboard Examples

In addition to the Sales and HR dashboards from the course content, this repository includes conversion guides for two customer-specific dashboard use cases that demonstrate the breadth of the conversion framework:

### CISO Cybersecurity Dashboard
- **Source Data**: Tenable.io vulnerability exports
- **Conversion Guide**: [`CISO_CYBERSECURITY_CONVERSION.md`](CISO_CYBERSECURITY_CONVERSION.md)
- **Mock Dataset**: `projects/ciso-cybersecurity-project/vulnerabilities.csv` (~200 rows)
- **Key Conversions**: Critical/High open counts, MTTR calculation, Risk Score by Business Unit (LOD FIXED → CALCULATE + ALLEXCEPT), Aging Vulnerabilities, CVSS running average (RUNNING_AVG → AVERAGEX + FILTER)
- **API Connector**: Tenable.io `/vulns/export` → Power Query M `Web.Contents` template included

### IT Project Management Dashboard
- **Source Data**: JIRA REST API (Agile board sprints + issues)
- **Conversion Guide**: [`IT_PROJECT_MGMT_CONVERSION.md`](IT_PROJECT_MGMT_CONVERSION.md)
- **Mock Dataset**: `projects/it-project-mgmt-project/jira_issues.csv` (~300 rows across 6 sprints)
- **Key Conversions**: Sprint Velocity, Burn-down chart (RUNNING_SUM in reverse → SUMX + FILTER + date logic), Cycle Time, Velocity Trend (WINDOW_AVG → AVERAGEX + FILTER(ALL)), Scope Creep detection
- **API Connector**: JIRA REST API `/rest/agile/1.0/board/{boardId}/sprint` → Power Query M template included

### Devin Batch Automation
- **Workflow Guide**: [`DEVIN_BATCH_WORKFLOW.md`](DEVIN_BATCH_WORKFLOW.md)
- **Role**: Devin serves as the batch automation engine for at-scale conversion (10-120 workbooks)
- **Key Capabilities**: Manifest-driven processing, parallel sessions, PR-based output, migration tracking, JIRA integration
- **Scaling**: 17 sample workbooks → 120 production dashboards via parallel Devin sessions

### API Connector Mapping
- **Reference**: [`output/api_connector_mapping.md`](output/api_connector_mapping.md)
- **Coverage**: Tenable.io, JIRA REST API, Oracle Database (ODI), CSV/Excel, Tableau Hyper extracts
- **Includes**: Power Query M code templates, FedRAMP GCC High compliance considerations

---

## Recommended Demo Sequence

> **For a simplified demo using single mega-prompts instead of individual steps, see [DEMO_PROMPTS.md](DEMO_PROMPTS.md).**

### For the Deloitte GPS / BEP Meeting

**Demo Flow (30 minutes total):**

| Time | Segment | Tool | What to Show | Prompt / Action |
|------|---------|------|--------------|-----------------|
| 0:00-2:00 | Context & Repo Overview | — | Walk through the repository structure: .twbx files, datasets, conversion guide, customer-specific examples | Navigate the repo in browser/IDE |
| 2:00-4:00 | [Windsurf] Sales Dashboard Parse | Windsurf | Open Sales & Customer Dashboards.twbx, parse XML, inventory calculated fields | "Open the Sales & Customer Dashboards.twbx and extract all calculated fields" |
| 4:00-8:00 | [Windsurf] Sales Dashboard Convert | Windsurf | Convert Tableau formulas to DAX: IF/THEN, LOD FIXED, WINDOW_MAX, parameters | "Convert each calculated field to DAX. Show me the LOD FIXED → CALCULATE conversion" |
| 8:00-11:00 | [Windsurf] CISO Cybersecurity Dashboard | Windsurf | Convert vulnerability dashboard: Critical Open Count, MTTR, Risk Score by BU | "Using the vulnerability dataset, convert the CISO dashboard calculated fields. Show the LOD FIXED Risk Score conversion" |
| 11:00-14:00 | [Windsurf] CISO Validation & API Connector | Windsurf | Run validation script, show Power Query M template for Tenable.io API | "Generate a validation script for the CISO dashboard and show the Tenable API connector" |
| 14:00-16:00 | [Windsurf] JIRA Burn-down Chart | Windsurf | Convert burn-down chart (the hardest Agile metric): RUNNING_SUM → SUMX + date logic | "Convert the JIRA burn-down remaining calculation. This is the trickiest — show the DAX" |
| 16:00-19:00 | [Devin] Batch Conversion | Devin | Show Devin processing multiple workbooks from manifest, generating artifacts | Trigger Devin session: "Convert all .twbx files using the migration manifest" |
| 19:00-22:00 | [Devin] Live PR Creation | Devin | Devin creates a PR with DAX files, TMDL models, validation reports | Show the PR diff: organized output per workbook |
| 22:00-24:00 | [Devin] Migration Tracker & Validation | Devin | Show the migration tracker table, aggregate validation results | Review PR: migration_tracker.md, validation_summary.md |
| 24:00-26:00 | Compliance | — | Validation framework as IV&V evidence, FedRAMP IL4 boundary, NIST SA-11 artifacts | Show validation_report.md, reference STIG/NIST controls |
| 26:00-28:00 | API Connectors | — | Show Power Query M templates for Tenable.io and JIRA — "we convert the data pipeline too" | Open api_connector_mapping.md |
| 28:00-30:00 | Close | — | Windsurf + Devin together: 120 dashboards by EOY, PR-based workflow, FedRAMP compliant | DEVIN_BATCH_WORKFLOW.md scaling narrative |

### Key Talking Points During Demo

1. **"No Tableau license needed"** — Windsurf parses the XML directly. BEP doesn't need to maintain Tableau Server during migration.

2. **"Automated validation, not trust-based"** — The Python validation script proves conversion accuracy. BEP's IV&V team gets auditable results.

3. **"This runs inside the FedRAMP boundary"** — Windsurf FedRAMP at IL4 means Deloitte developers can do this conversion on BEP's own networks, with BEP's actual production data, without leaving the accreditation boundary.

4. **"17 workbooks, same workflow"** — Show that the same prompt-driven approach scales across BEP's entire Tableau portfolio. What would take a team of analysts weeks, Windsurf handles in hours.

5. **"The hardest part is LOD → CALCULATE"** — LOD expressions are the #1 reason Tableau-to-Power BI migrations fail. Show that Windsurf handles FIXED, INCLUDE, and EXCLUDE correctly.

6. **"Your actual dashboards, not generic examples"** — The CISO Cybersecurity and JIRA Project Management dashboards mirror real use cases with real data shapes (Tenable vulnerability exports, JIRA sprint data). This isn't a toy demo.

7. **"API connector conversion included"** — We don't just convert the visuals. The Tenable.io and JIRA Power Query M scripts show that the entire data pipeline — from API connection to DAX measures to dashboard layout — is converted end-to-end.

8. **"Devin scales this to 120 dashboards"** — Devin reads a manifest, processes workbooks through the 7-phase pipeline, and delivers Pull Requests with full conversion artifacts. What takes one developer weeks, Devin handles in days with parallel sessions and PR-based review.

---

## File Structure After Conversion

```
BEP-Tableau-PowerBI-Migration/
├── windsurf-conversion-guide/
│   ├── CONVERSION_OUTLINE.md              ← This file (you are here)
│   ├── CISO_CYBERSECURITY_CONVERSION.md   ← CISO vulnerability dashboard guide
│   ├── IT_PROJECT_MGMT_CONVERSION.md      ← IT project management dashboard guide
│   ├── DEVIN_BATCH_WORKFLOW.md            ← Devin batch automation workflow
│   └── output/                             ← Generated by Windsurf during demo
│       ├── api_connector_mapping.md        ← API data source → Power BI mapping
│       ├── sales_dashboard_dax_measures.dax
│       ├── hr_dashboard_dax_measures.dax
│       ├── lod_to_calculate_mappings.dax
│       ├── table_calc_conversions.dax
│       ├── parameter_conversions.dax
│       ├── sales_model.tmdl
│       ├── hr_model.tmdl
│       ├── data_type_mapping.md
│       ├── sales_dashboard_layout.json
│       ├── customer_dashboard_layout.json
│       ├── hr_dashboard_layouts.json
│       ├── powerbi_theme.json
│       ├── interactions_spec.md
│       ├── navigation_bookmarks.json
│       ├── validate_conversion.py
│       ├── conversion_validation_report.md
│       ├── generate_powerbi_dataset.py
│       ├── all_dax_measures.dax
│       ├── power_query_transforms.pq
│       ├── powerbi-ready/
│       │   ├── Orders_clean.csv
│       │   ├── Customers_clean.csv
│       │   ├── Products_clean.csv
│       │   ├── Location_clean.csv
│       │   └── HR_clean.csv
│       └── tmdl/
│           ├── model.tmdl
│           ├── tables/
│           ├── relationships.tmdl
│           └── measures.tmdl
├── course/
│   ├── datasets/                           ← Source CSV data files
│   └── tableau-files/                      ← Source .twbx Tableau workbooks
├── projects/
│   ├── sales-dashboard-project/            ← Production-grade Sales dashboard
│   ├── hr-dashboard-project/               ← Production-grade HR dashboard
│   ├── ciso-cybersecurity-project/         ← CISO vulnerability dashboard
│   │   ├── generate_vuln_data.py           ← Mock Tenable data generator
│   │   └── vulnerabilities.csv             ← ~200 row mock vulnerability dataset
│   └── it-project-mgmt-project/            ← IT project management dashboard
│       ├── generate_jira_data.py           ← Mock JIRA data generator
│       └── jira_issues.csv                 ← ~300 row mock JIRA issue dataset
├── LICENSE                                 ← MIT License
└── README.md                               ← Original repo README
```

---

## Appendix: BEP MES Data Mapping

How the demo datasets map to real BEP MES data domains:

| Demo Dataset | BEP MES Equivalent | MES System Source |
|-------------|-------------------|-------------------|
| Orders (Sales, Quantity, Profit, Dates) | Print Production Orders (Sheet Count, Spoilage, Cost Variance, Run Dates) | MES Console, SCADA |
| Customers (Customer ID, Name) | Federal Reserve Banks (FRB ID, District Name) | Oracle ESB |
| Products (Category, Sub-Category, Product Name) | Currency Products (Security Document Type, Denomination, Series/Year) | MES Product Master |
| Location (City, State, Region) | Facilities & Distribution (ECF, WCF, FRB Districts) | BEP Reporting (BR) |
| USA Sales (Regional data) | FRB Currency Demand by District | LinorTek, Oracle ODI |
| HR Dataset (Employees, Departments, Tenure) | BEP Workforce (ECF/WCF Staffing, Contractor/Federal, Clearance Level) | Identity Manager (IDM) |
| LOD Detail Data | Per-Press Production Metrics | SCADA, AcuGage, Impression Count |

### Key BEP MES Systems That Feed Tableau (Currently)
1. **SCADA** — Real-time equipment data → Tableau real-time dashboards
2. **OCIS** — Optical Currency Inspection System → Quality dashboards
3. **AcuGage** — Precision measurement → Quality control analytics
4. **Impression Count** — Sheet/impression tracking → Production volume dashboards
5. **LinorTek** — Packaging/bundling systems → Distribution dashboards
6. **Oracle ODI** — ETL pipeline → All dashboards (data integration layer)
7. **Oracle Analytics Server (OAS)** — Enterprise reporting (separate from Tableau)
8. **Identity Manager (IDM)** — Workforce/access data → HR/staffing dashboards
