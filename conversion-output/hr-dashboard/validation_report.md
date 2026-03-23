# HR Dashboard — Power BI Conversion Validation Report

**Source**: Tableau HR Dashboard (`projects/hr-dashboard-project/`)  
**Target**: Power BI Desktop (`.pbix` via TMDL/DAX/M artifacts)  
**Conversion Date**: 2026-03-23  
**Reference**: `windsurf-conversion-guide/CONVERSION_OUTLINE.md` Step 2.5 (Lines 172–185)

---

## 1. Data Source Validation

| Property | Tableau (Source) | Power BI (Target) | Status |
|---|---|---|---|
| File | `dataset.csv` | `dataset.csv` (via Power Query) | Converted |
| Delimiter | Semicolon (`;`) | Semicolon (`;`) — set in `Csv.Document()` | Converted |
| Date Format | DD/MM/YYYY | Parsed via custom `ParseEUDate` function in Power Query | Converted |
| Encoding | UTF-8 | UTF-8 (codepage 65001) | Converted |
| Null Handling (Termdate) | `ISNULL([Termdate])` | `ISBLANK(HR[Termdate])` + Power Query null coercion | Converted |

---

## 2. Column Mapping

| Source Column | Data Type (Tableau) | Data Type (Power BI) | Notes |
|---|---|---|---|
| Employee_ID | String | Text | Primary key |
| First Name | String | Text | — |
| Last Name | String | Text | — |
| Gender | String | Text | — |
| State | String | Text | — |
| City | String | Text | — |
| Education Level | String | Text | — |
| Birthdate | Date (DD/MM/YYYY) | Date | Parsed from EU format in Power Query |
| Hiredate | Date (DD/MM/YYYY) | Date | Parsed from EU format in Power Query |
| Termdate | Date (DD/MM/YYYY, nullable) | Date (nullable) | Blanks/nulls preserved for active employees |
| Department | String | Text | — |
| Job Title | String | Text | — |
| Salary | Number | Decimal (Currency) | Formatted as `$#,##0.00` |
| Performance Rating | String | Text | — |

---

## 3. Calculated Column Conversions

| Column Name | Tableau Formula | DAX Formula | Status |
|---|---|---|---|
| **Status** | `IF ISNULL([Termdate]) THEN 'Hired' ELSE 'Terminated' END` | `IF(ISBLANK(HR[Termdate]), "Hired", "Terminated")` | Converted |
| **Location** | `CASE [State] WHEN 'New York' THEN 'HQ' ELSE 'Branch' END` | `IF(HR[State] = "New York", "HQ", "Branch")` | Converted |
| **Age** | `DATEDIFF('year', [Birthdate], TODAY())` | `DATEDIFF(HR[Birthdate], TODAY(), YEAR)` | Converted |
| **Age Group** | `IF [Age] < 25 THEN '<25' ELSEIF [Age] < 35 THEN '25-34' ...` | `SWITCH(TRUE(), HR[Age] < 25, "<25", ...)` | Converted |
| **Length of Hire** | `IF ISNULL([Termdate]) THEN DATEDIFF('year', [Hiredate], TODAY()) ELSE DATEDIFF('year', [Hiredate], [Termdate]) END` | `IF(ISBLANK(HR[Termdate]), DATEDIFF(HR[Hiredate], TODAY(), YEAR), DATEDIFF(HR[Hiredate], HR[Termdate], YEAR))` | Converted |
| **Full Name** | `[First Name] + ' ' + [Last Name]` | `HR[First Name] & " " & HR[Last Name]` | Converted |

### Conversion Notes — Calculated Columns

- **ISNULL → ISBLANK**: Tableau's `ISNULL()` maps to DAX `ISBLANK()`. Both return TRUE for null/blank values.
- **CASE → IF/SWITCH**: Tableau's `CASE` with a single comparison maps cleanly to DAX `IF()`. Multi-branch `IF/ELSEIF` chains use `SWITCH(TRUE(), ...)`.
- **DATEDIFF parameter order**: Tableau uses `DATEDIFF('unit', start, end)` while DAX uses `DATEDIFF(start, end, unit)`. Argument order has been swapped accordingly.
- **String concatenation**: Tableau uses `+` for string concatenation; DAX uses `&`.

---

## 4. Measure Conversions

| Measure Name | Tableau Formula | DAX Formula | Status |
|---|---|---|---|
| **Total Hired** | `COUNT([Employee_ID])` | `COUNTROWS(HR)` | Converted |
| **Total Terminated** | `COUNT(IF NOT ISNULL([Termdate]) THEN [Employee_ID] END)` | `CALCULATE(COUNTROWS(HR), NOT(ISBLANK(HR[Termdate])))` | Converted |
| **Total Active** | `COUNT(IF ISNULL([Termdate]) THEN [Employee_ID] END)` | `CALCULATE(COUNTROWS(HR), ISBLANK(HR[Termdate]))` | Converted |
| **% Total Hired** | `[Total Hired] / TOTAL([Total Hired])` | `DIVIDE([Total Hired], CALCULATE([Total Hired], ALL(HR)), 0)` | Converted |
| **Highlight Max** | `WINDOW_MAX([Total Hired]) = [Total Hired]` | `IF([Total Hired] = MAXX(ALLSELECTED(HR[Department]), [Total Hired]), TRUE(), FALSE())` | Converted |
| **Avg Salary** | `AVG([Salary])` | `AVERAGE(HR[Salary])` | Converted |
| **Hires by Year** | Active employee count per year | `CALCULATE(COUNTROWS(HR), ISBLANK(HR[Termdate]))` | Converted |
| **Terminations by Year** | Terminated count per year | `CALCULATE(COUNTROWS(HR), NOT(ISBLANK(HR[Termdate])))` | Converted |

### Conversion Notes — Measures

- **COUNT → COUNTROWS**: Tableau's `COUNT([field])` counting non-null values maps to DAX `COUNTROWS(table)` for counting all rows. Since Employee_ID is never null, these are equivalent.
- **COUNT-IF pattern → CALCULATE**: Tableau's inline `COUNT(IF ... THEN ... END)` becomes DAX `CALCULATE(COUNTROWS(...), filter)`.
- **TOTAL() → ALL()**: Tableau's `TOTAL()` function computes the grand total across all partitions. The DAX equivalent uses `CALCULATE` with `ALL(table)` to remove all filters.
- **WINDOW_MAX → MAXX + ALLSELECTED**: Tableau's `WINDOW_MAX()` computes the maximum across partitions. DAX uses `MAXX(ALLSELECTED(dimension), measure)` to iterate over all visible values and find the maximum.
- **Division safety**: `DIVIDE()` is used instead of `/` to handle division-by-zero cases (returns 0 as the alternate result).

---

## 5. Data Model Validation

| Component | Description | Status |
|---|---|---|
| **HR Table** | Primary fact table with 14 source columns + 6 calculated columns | Defined in `model.tmdl` |
| **DateTable** | Calendar dimension (2000–2030) with Year, Month, Quarter, DayOfWeek | Defined in `model.tmdl` |
| **Relationship: Hiredate** | `HR[Hiredate]` → `DateTable[Date]` (active, single direction) | Configured |
| **Relationship: Termdate** | `HR[Termdate]` → `DateTable[Date]` (inactive, single direction) | Configured |
| **Measures** | 8 measures attached to HR table | Defined in `model.tmdl` and `dax_measures.dax` |

### Date Table Notes

- The inactive relationship on Termdate allows use of `USERELATIONSHIP()` in DAX measures when analyzing termination timelines.
- DateTable covers 2000–2030 to encompass all possible birth dates, hire dates, and term dates in the dataset.

---

## 6. Power Query Validation

| Step | Description | Status |
|---|---|---|
| Import | `Csv.Document()` with semicolon delimiter, UTF-8 encoding | Implemented |
| Header Promotion | First row promoted to column headers | Implemented |
| Whitespace Trimming | All text columns trimmed | Implemented |
| Date Parsing | Custom `ParseEUDate` function converts DD/MM/YYYY → Date | Implemented |
| Null Handling | Termdate blanks/empty strings → `null` | Implemented |
| Type Assignment | All 14 columns assigned correct Power BI data types | Implemented |
| Salary Cleaning | Salary nulls default to 0, parsed as number | Implemented |

---

## 7. Layout Validation

### Page 1: HR Summary

| Visual | Type | Data Binding | Status |
|---|---|---|---|
| Total Hired KPI | Card | `[Total Hired]` | Configured |
| Total Terminated KPI | Card | `[Total Terminated]` | Configured |
| Total Active KPI | Card | `[Total Active]` | Configured |
| Average Salary KPI | Card | `[Avg Salary]` | Configured |
| Department Donut | Donut Chart | Department × Total Hired | Configured |
| HQ vs Branch | Clustered Bar | Location × Total Hired (by Gender) | Configured |
| Age Distribution | Clustered Column | Age Group × Total Hired | Configured |
| Gender Breakdown | Donut Chart | Gender × Total Hired | Configured |
| Department Slicer | Dropdown Slicer | Department | Configured |
| Status Slicer | Tile Slicer | Status | Configured |

### Page 2: HR Details

| Visual | Type | Data Binding | Status |
|---|---|---|---|
| Department Filter | Dropdown Slicer | Department | Configured |
| Location Filter | Tile Slicer | Location | Configured |
| Status Filter | Tile Slicer | Status | Configured |
| Education Filter | Dropdown Slicer | Education Level | Configured |
| Performance Filter | Dropdown Slicer | Performance Rating | Configured |
| Employee Table | Table | 12 columns with conditional formatting | Configured |
| Performance Distribution | Clustered Bar | Performance Rating × Total Hired | Configured |
| Tenure Distribution | Clustered Column | Length of Hire × Total Hired | Configured |

### Conditional Formatting

| Column | Rule Type | Details |
|---|---|---|
| Status | Discrete | Hired = green background, Terminated = red background |
| Performance Rating | Discrete | Exceeds = green, Good = blue, Satisfactory = yellow, Needs Improvement = red |
| Salary | Color Scale | Low (red) → Mid (yellow) → High (green) |

---

## 8. Theme Validation

| Property | Value | Purpose |
|---|---|---|
| Primary Color | `#2E86C1` (Blue) | Active/hired employees, headers |
| Good/Hired | `#28B463` (Green) | Positive indicators, active status |
| Bad/Terminated | `#E74C3C` (Red) | Negative indicators, terminated status |
| Warning | `#F39C12` (Amber) | Neutral/warning indicators |
| Background | `#F4F6F7` (Light Gray) | Page background |
| Foreground | `#2C3E50` (Dark Navy) | Text and labels |
| Font | Segoe UI family | Consistent with Power BI default |

---

## 9. Artifacts Inventory

| File | Description | Format |
|---|---|---|
| `dax_measures.dax` | All DAX calculated columns and measures with Tableau source comments | DAX |
| `model.tmdl` | Tabular Model Definition with tables, columns, measures, relationships | TMDL |
| `layout.json` | Two-page Power BI layout with visual configurations | JSON |
| `power_query.pq` | Power Query M script for data import and transformation | M (Power Query) |
| `theme.json` | Power BI theme with HR-appropriate color palette | JSON |
| `validation_report.md` | This validation report | Markdown |

---

## 10. Known Limitations & Recommendations

1. **TMDL Import**: The `model.tmdl` file defines the semantic model structure. To use in Power BI Desktop, import via Tabular Editor or the Power BI TMDL preview feature.
2. **Date Table Relationship**: The Termdate relationship is set to inactive by default. Use `USERELATIONSHIP(HR[Termdate], DateTable[Date])` in measures that need to analyze by termination date.
3. **File Path**: The Power Query script references `dataset.csv` by relative path. Update the `File.Contents()` path to match the actual deployment location.
4. **Highlight Max**: The `Highlight Max` measure uses `ALLSELECTED` which respects slicer context. If the visual should always compare against the global maximum regardless of slicers, replace `ALLSELECTED` with `ALL`.
5. **EU Date Parsing**: The Power Query `ParseEUDate` function expects exactly DD/MM/YYYY format. If the source data format varies, add additional parsing logic.
