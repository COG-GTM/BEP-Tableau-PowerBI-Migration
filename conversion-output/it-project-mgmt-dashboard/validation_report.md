# IT Project Management Dashboard — Validation Report

> **Source**: Tableau Calculated Fields (IT PM Dashboard)
> **Target**: Power BI DAX Measures
> **Dataset**: `projects/it-project-mgmt-project/jira_issues.csv` (~300 rows, 17 columns)
> **Conversion Guide**: `windsurf-conversion-guide/IT_PROJECT_MGMT_CONVERSION.md`

---

## Summary

| Metric | Value |
|--------|-------|
| Total Measures Converted | 16 |
| Core Measure Groups | 10 |
| Data Model Tables | 6 (1 fact + 4 dimension + 1 calendar) |
| Relationships | 4 (all Many-to-1, single cross-filter) |
| Report Pages | 2 (Sprint Overview, Team Workload) |
| Conversion Status | Complete |

---

## Measure Conversion Details

### 1. Sprint Velocity

| Attribute | Detail |
|-----------|--------|
| **Tableau Pattern** | `SUM(IF [Status] = 'Done' THEN [Story_Points] END)` |
| **DAX Pattern** | `CALCULATE + SUM` with filter `Status = "Done"` |
| **Complexity** | Low |
| **Conversion Notes** | Direct translation — Tableau's `SUM(IF...)` maps cleanly to `CALCULATE(SUM(...), filter)` |
| **Validation** | Sum of Story_Points where Status = "Done", grouped by Sprint_Name |
| **Status** | Converted |

### 2. Burn-down Remaining

| Attribute | Detail |
|-----------|--------|
| **Tableau Pattern** | `RUNNING_SUM(SUM([Story_Points])) - RUNNING_SUM(SUM(IF [Status]='Done' THEN [Story_Points] END))` |
| **DAX Pattern** | `VAR TotalPoints + CompletedToDate` with `ALLSELECTED` and date filtering |
| **Complexity** | High (most complex conversion) |
| **Conversion Notes** | Tableau's `RUNNING_SUM` table calc requires explicit date logic in DAX. Uses `ALLSELECTED` to respect slicer context while removing date filters for the running total. Calendar table required as X-axis. |
| **Validation** | Verify remaining points decrease correctly across sprint dates; compare daily snapshots against manual calculation |
| **Status** | Converted |

### 3. Avg Cycle Time (Days)

| Attribute | Detail |
|-----------|--------|
| **Tableau Pattern** | `IF [Status]='Done' AND NOT ISNULL([Resolved_Date]) THEN DATEDIFF('day', [Created_Date], [Resolved_Date]) END` |
| **DAX Pattern** | `AVERAGEX + FILTER + DATEDIFF` |
| **Complexity** | Medium |
| **Conversion Notes** | Row-level IF with DATEDIFF becomes AVERAGEX iterating over filtered rows. Only includes Done issues with non-blank Resolved_Date. |
| **Validation** | Average of (Resolved_Date - Created_Date) in days for all Done issues with a resolved date |
| **Status** | Converted |

### 4. Avg Lead Time (Days)

| Attribute | Detail |
|-----------|--------|
| **Tableau Pattern** | `IF [Status]='Done' THEN DATEDIFF('day',[Created_Date],[Resolved_Date]) ELSE DATEDIFF('day',[Created_Date],TODAY()) END` |
| **DAX Pattern** | `AVERAGEX` with conditional `DATEDIFF` (Done → Resolved_Date, else → TODAY) |
| **Complexity** | Medium |
| **Conversion Notes** | Includes open issues measured to TODAY(), unlike cycle time. Conditional branching preserved in DAX IF(). |
| **Validation** | For Done items: days from Created to Resolved. For open items: days from Created to today. Average across all. |
| **Status** | Converted |

### 5a. Story Points Completed

| Attribute | Detail |
|-----------|--------|
| **Tableau Pattern** | `SUM(IF [Status]='Done' THEN [Story_Points] END)` |
| **DAX Pattern** | `CALCULATE(SUM(...), Status = "Done")` |
| **Complexity** | Low |
| **Conversion Notes** | Same pattern as Sprint Velocity — dedicated measure for card/KPI use |
| **Validation** | Sum of Story_Points where Status = "Done" |
| **Status** | Converted |

### 5b. Story Points Planned

| Attribute | Detail |
|-----------|--------|
| **Tableau Pattern** | `SUM([Story_Points])` |
| **DAX Pattern** | `SUM(fact_issues[Story_Points])` |
| **Complexity** | Low |
| **Conversion Notes** | Direct 1:1 mapping — total points committed to sprint |
| **Validation** | Sum of all Story_Points in current filter context |
| **Status** | Converted |

### 5c. Completion Rate

| Attribute | Detail |
|-----------|--------|
| **Tableau Pattern** | `SUM(IF [Status]='Done' THEN [Story_Points] END) / SUM([Story_Points])` |
| **DAX Pattern** | `DIVIDE([Story Points Completed], [Story Points Planned], 0)` |
| **Complexity** | Low |
| **Conversion Notes** | Uses DIVIDE for safe division (avoids divide-by-zero). References the two sub-measures. |
| **Validation** | Completed / Planned ratio, should be between 0 and 1 |
| **Status** | Converted |

### 6. Bug Escape Rate

| Attribute | Detail |
|-----------|--------|
| **Tableau Pattern** | `COUNTD(IF [Issue_Type]='Bug' THEN [Issue_Key] END) / COUNTD([Issue_Key])` |
| **DAX Pattern** | `DIVIDE(CALCULATE(DISTINCTCOUNT(...), Issue_Type="Bug"), DISTINCTCOUNT(...), 0)` |
| **Complexity** | Medium |
| **Conversion Notes** | COUNTD with IF → CALCULATE + DISTINCTCOUNT. Measures proportion of bugs to total issues per sprint. |
| **Validation** | Count of distinct Bug issue keys / Count of all distinct issue keys |
| **Status** | Converted |

### 7. Sprint Completion %

| Attribute | Detail |
|-----------|--------|
| **Tableau Pattern** | `COUNTD(IF [Status]='Done' THEN [Issue_Key] END) / COUNTD([Issue_Key])` |
| **DAX Pattern** | `DIVIDE(CALCULATE(DISTINCTCOUNT(...), Status="Done"), DISTINCTCOUNT(...), 0)` |
| **Complexity** | Medium |
| **Conversion Notes** | Issue-count-based completion (vs. story-point-based Completion Rate). Both metrics are valuable for different views. |
| **Validation** | Count of distinct Done issue keys / Count of all distinct issue keys |
| **Status** | Converted |

### 8. Issues by Status (4 measures)

| Attribute | Detail |
|-----------|--------|
| **Tableau Pattern** | `COUNTD(IF [Status]='X' THEN [Issue_Key] END)` for each status |
| **DAX Pattern** | `CALCULATE(DISTINCTCOUNT(...), Status = "X")` for each status |
| **Complexity** | Low |
| **Conversion Notes** | Four separate measures: To Do, In Progress, In Review, Done. Each is a CALCULATE with a single filter. |
| **Sub-measures** | `Issues To Do`, `Issues In Progress`, `Issues In Review`, `Issues Done` |
| **Validation** | Sum of all four status counts should equal total DISTINCTCOUNT of Issue_Key |
| **Status** | Converted |

### 9. Velocity 3-Sprint Moving Average

| Attribute | Detail |
|-----------|--------|
| **Tableau Pattern** | `WINDOW_AVG(SUM(IF [Status]='Done' THEN [Story_Points] END), -2, 0)` |
| **DAX Pattern** | `AVERAGEX + FILTER(ALL(dim_sprints))` sliding window over Sprint_Number |
| **Complexity** | High |
| **Conversion Notes** | Tableau's WINDOW_AVG(-2,0) computes 3-period moving average (current + 2 prior). DAX uses ALL() to remove current filter context, then FILTER to look back 2 sprints. Requires Sprint_Number column for ordering. |
| **Validation** | For each sprint N: average of velocity for sprints N-2, N-1, N |
| **Status** | Converted |

### 10. Scope Creep (Issues Added Mid-Sprint)

| Attribute | Detail |
|-----------|--------|
| **Tableau Pattern** | `COUNTD(IF [Created_Date] > [Sprint_Start] AND [Created_Date] <= [Sprint_End] THEN [Issue_Key] END)` |
| **DAX Pattern** | `CALCULATE + FILTER with RELATED(dim_sprints[Sprint_Start/Sprint_End])` |
| **Complexity** | Medium |
| **Conversion Notes** | Uses RELATED() to access dimension columns through the relationship. Counts issues whose Created_Date falls within the sprint window (after start, before/on end). |
| **Validation** | Count of issues where Created_Date > Sprint_Start AND Created_Date <= Sprint_End for each sprint |
| **Status** | Converted |

---

## Data Model Validation

### Tables

| Table | Type | Row Source | Key Column | Expected Rows |
|-------|------|-----------|------------|---------------|
| fact_issues | Fact | jira_issues.csv | Issue_Key | ~300 |
| dim_sprints | Dimension | Extracted from fact_issues | Sprint_Name | ~6-10 |
| dim_assignees | Dimension | Extracted from fact_issues | Assignee | ~8-12 |
| dim_epics | Dimension | Filtered from fact_issues (Issue_Type = "Epic") | Epic_Key | ~5-8 |
| dim_issue_types | Dimension | Static reference table | Issue_Type | 7 |
| Calendar | Date | DAX CALENDAR(2025-09-01, 2026-03-31) | Date | 213 |

### Relationships

| # | From | To | Cardinality | Cross-filter | Status |
|---|------|----|-------------|--------------|--------|
| 1 | fact_issues[Sprint_Name] | dim_sprints[Sprint_Name] | Many-to-1 | Single | Defined |
| 2 | fact_issues[Assignee] | dim_assignees[Assignee] | Many-to-1 | Single | Defined |
| 3 | fact_issues[Epic_Key] | dim_epics[Epic_Key] | Many-to-1 | Single | Defined |
| 4 | fact_issues[Issue_Type] | dim_issue_types[Issue_Type] | Many-to-1 | Single | Defined |

---

## Dashboard Pages Validation

### Page 1: Sprint Overview

| Visual | Type | Primary Measure(s) | Status |
|--------|------|-------------------|--------|
| Sprint Slicer | Slicer (dropdown) | dim_sprints[Sprint_Name] | Defined |
| Assignee Slicer | Slicer (dropdown) | dim_assignees[Assignee] | Defined |
| Epic Slicer | Slicer (dropdown) | dim_epics[Epic_Key] | Defined |
| Velocity KPI Card | Card | Sprint Velocity | Defined |
| Completion % KPI Card | Card | Sprint Completion % | Defined |
| Avg Cycle Time KPI Card | Card | Avg Cycle Time (Days) | Defined |
| Bug Escape Rate KPI Card | Card | Bug Escape Rate | Defined |
| Scope Creep KPI Card | Card | Scope Creep (Issues Added Mid-Sprint) | Defined |
| Velocity Bar Chart | Clustered Bar + Line | Sprint Velocity + 3-Sprint Moving Avg | Defined |
| Burn-down Chart | Line Chart | Burn-down Remaining | Defined |
| Status Distribution | Donut Chart | Issue counts by Status | Defined |
| Sprint Comparison Matrix | Matrix | Velocity, Completion%, Bugs, Scope Creep | Defined |
| Cycle Time Histogram | Clustered Column | Cycle Time distribution (binned) | Defined |

### Page 2: Team Workload

| Visual | Type | Primary Measure(s) | Status |
|--------|------|-------------------|--------|
| Assignee Workload Matrix | Matrix (heatmap) | Story Points by Assignee x Sprint | Defined |
| Story Points by Member | Clustered Bar | Completed vs Planned by Assignee | Defined |
| Individual Velocity Trends | Line Chart | Velocity per Assignee over Sprints | Defined |

---

## Artifacts Produced

| File | Description | Lines |
|------|-------------|-------|
| `dax_measures.dax` | All 16 DAX measures with Tableau formulas as comments | ~230 |
| `model.tmdl` | Complete TMDL with 6 tables, 4 relationships, all measures | ~380 |
| `layout.json` | 2-page report layout with all visuals and formatting | ~550 |
| `power_query.pq` | Power Query M: CSV import + JIRA REST API template + dimension extraction | ~290 |
| `theme.json` | Professional blue/gray Power BI theme | ~280 |
| `validation_report.md` | This document | — |

---

## Conversion Pattern Reference

| Tableau Pattern | DAX Equivalent | Used In |
|----------------|----------------|---------|
| `SUM(IF ... END)` | `CALCULATE(SUM(...), filter)` | Measures 1, 5a |
| `RUNNING_SUM` | `VAR + ALLSELECTED + date filter` | Measure 2 |
| `IF + DATEDIFF` | `AVERAGEX + FILTER + DATEDIFF` | Measures 3, 4 |
| `SUM / SUM` | `DIVIDE([m1], [m2], 0)` | Measures 5c, 7 |
| `COUNTD(IF ... END) / COUNTD` | `DIVIDE(CALCULATE(DISTINCTCOUNT), DISTINCTCOUNT)` | Measures 6, 7 |
| `COUNTD(IF [Status]='X')` | `CALCULATE(DISTINCTCOUNT, Status="X")` | Measure 8 |
| `WINDOW_AVG(-2, 0)` | `AVERAGEX(FILTER(ALL(dim), range))` | Measure 9 |
| `COUNTD(IF date > date)` | `CALCULATE(DISTINCTCOUNT, FILTER(RELATED))` | Measure 10 |

---

## Python Validation Script

The following validation script can be used to verify DAX measure outputs against pandas calculations:

```python
import pandas as pd

df = pd.read_csv("projects/it-project-mgmt-project/jira_issues.csv")

# 1. Sprint Velocity
velocity = df[df["Status"] == "Done"].groupby("Sprint_Name")["Story_Points"].sum()
print(f"Sprint Velocity:\n{velocity}\n")

# 3. Avg Cycle Time
done = df[(df["Status"] == "Done") & df["Resolved_Date"].notna()].copy()
done["Created_Date"] = pd.to_datetime(done["Created_Date"])
done["Resolved_Date"] = pd.to_datetime(done["Resolved_Date"])
done["Cycle_Time"] = (done["Resolved_Date"] - done["Created_Date"]).dt.days
print(f"Avg Cycle Time: {done['Cycle_Time'].mean():.1f} days\n")

# 6. Bug Escape Rate
bug_rate = len(df[df["Issue_Type"] == "Bug"]) / len(df)
print(f"Bug Escape Rate: {bug_rate:.1%}\n")

# 10. Scope Creep
df["Created_Date"] = pd.to_datetime(df["Created_Date"])
df["Sprint_Start"] = pd.to_datetime(df["Sprint_Start"])
scope_creep = len(df[df["Created_Date"] > df["Sprint_Start"]])
print(f"Scope Creep (issues added mid-sprint): {scope_creep}\n")

# 7. Sprint Completion Rate
completion = df.groupby("Sprint_Name").apply(
    lambda x: len(x[x["Status"] == "Done"]) / len(x)
)
print(f"Sprint Completion Rate:\n{completion}")
```

---

## IV&V Compliance Artifacts

| Artifact | Description | NIST Control |
|----------|-------------|--------------|
| `sprint_velocity_baseline.json` | Expected velocity values per sprint for regression | SA-11 |
| `cycle_time_distribution.csv` | Full distribution of cycle times for statistical validation | SA-11(1) |
| `burn_down_daily_snapshots.csv` | Daily point values for burn-down chart verification | SI-12 |
| `scope_change_audit.csv` | Issues added/removed per sprint with timestamps | AU-2, CM-3 |
