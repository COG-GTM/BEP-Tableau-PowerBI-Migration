# HR Dashboard (Project)

> **Source**: `HR Dashboard.twbx`
> **Extracted TWB**: `HR Dashboard.twb`

---

## Summary

| Metric | Value |
|--------|-------|
| Calculated Fields | 15 |
| Parameters | 0 |
| Data Sources | 25 |
| Dashboards | 2 |
| Worksheets | 21 |

## Key Tableau Features Used

- Rank calculations
- Window calculations
- TOTAL() aggregation
- DATEDIFF date calculation
- CASE/WHEN switching
- Null handling (ISNULL/ZN)

## Calculated Fields

| # | Name | Formula | Data Type | Role |
|---|------|---------|-----------|------|
| 1 | % Total Terminated | `[Calculation_3363625995832086533] / TOTAL([Calculation_3363625995832086533])` | real | measure |
| 2 | % Total Hired | `[Calculation_3363625995831468034] / TOTAL([Calculation_3363625995831468034])` | real | measure |
| 3 | Rank Top 2 | `RANK([Calculation1]) <= 2` | boolean | measure |
| 4 | Status | `IF ISNULL([Termdate]) THEN 'Hired' ELSE 'Terminated' END` | string | dimension |
| 5 | Highlight Max | `WINDOW_MAX([Calculation_3363625995831468034]) = [Calculation_3363625995831468034]` | boolean | measure |
| 6 | Total Hired | `COUNT([Employee_ID])` | integer | measure |
| 7 | Total Terminated | `COUNT(IF NOT ISNULL([Termdate]) THEN [Employee_ID] END)` | integer | measure |
| 8 | Total Active | `COUNT(IF ISNULL([Termdate]) THEN [Employee_ID] END)` | integer | measure |
| 9 | Location | `CASE [State]     WHEN 'New York' THEN 'HQ'     ELSE 'Branch' END` | string | dimension |
| 10 | Age | `DATEDIFF('year', [Birthdate], TODAY())` | integer | measure |
| 11 | Age Groups | `IF [Calculation_3363625995860541454] < 25 THEN '>25' ELSEIF [Calculation_3363625995860541454] >=25 AND [Calculation_...` | string | dimension |
| 12 | Full Name | `[First Name] + ' ' + [Last Name]` | string | dimension |
| 13 | Length of Hire | `IF ISNULL ([Termdate])  THEN DATEDIFF('year', [Hiredate], TODAY()) ELSE DATEDIFF('year', [Hiredate], [Termdate]) END` | integer | measure |
| 14 | % Highlight Max | `WINDOW_MAX([Calculation1]) = [Calculation1]` | boolean | measure |
| 15 | Rank Top 1 | `RANK([Calculation1]) <= 1` | boolean | measure |

## Data Sources

| # | Name | Connection Type | Tables/Files |
|---|------|----------------|--------------|
| 1 | HumanResources | federated | HumanResources.csv, Extract |
| 2 | HumanResources | unknown | - |
| 3 | HumanResources | unknown | - |
| 4 | HumanResources | unknown | - |
| 5 | HumanResources | unknown | - |
| 6 | HumanResources | unknown | - |
| 7 | HumanResources | unknown | - |
| 8 | HumanResources | unknown | - |
| 9 | HumanResources | unknown | - |
| 10 | HumanResources | unknown | - |
| 11 | HumanResources | unknown | - |
| 12 | HumanResources | unknown | - |
| 13 | HumanResources | unknown | - |
| 14 | HumanResources | unknown | - |
| 15 | HumanResources | unknown | - |
| 16 | HumanResources | unknown | - |
| 17 | HumanResources | unknown | - |
| 18 | HumanResources | unknown | - |
| 19 | HumanResources | unknown | - |
| 20 | HumanResources | unknown | - |
| 21 | HumanResources | unknown | - |
| 22 | HumanResources | unknown | - |
| 23 | HumanResources | unknown | - |
| 24 | HumanResources | unknown | - |
| 25 | HumanResources | unknown | - |

## Dashboards

- **HR | Details** (1400 x 800)
- **HR | Summary** (1400 x 800)

## Worksheets

- Age
- Age Groups
- Age vs Education
- Age vs Salary
- BAN Active
- BAN Hired
- BAN Terminated
- Cities
- Departments
- Detailed
- Education Levels
- Education vs Performance
- Gender
- Gender vs Education Level
- Hired By Year
- Job Titles
- Location
- Map States
- States
- Terminated By Year
- test

## Extracted Files

- `Data/TableauTemp/#TableauTemp_1bg4gin0vyl3cj1d7s2jl00jlily.hyper`
- `HR Dashboard.twb`
- `Image/Logo.png`
- `Image/background dashbaord details.png`
- `Image/background dashbaord summary.png`
- `Image/contact-channel.png`
- `Image/contact-linkedin.png`
- `Image/contact-public.png`
- `Image/dashboard-records-active1.png`
- `Image/dashboard-records-inactive.png`
- `Image/dashboard-summary-active.png`
- `Image/dashboard-summary-inactive.png`
- `Image/download image.png`
- `Image/download pdf.png`
- `Image/filter-active.png`
- `Image/filter-group-hidden.png`
- `Image/filter-group-shown.png`
- `Image/filter-inactive.png`
- `Image/info-hidden.png`
- `Image/info-shown.png`
