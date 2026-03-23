# IT Project Management Dashboard — Tableau-to-Power BI Conversion Guide

> **Source Data**: JIRA REST API (`/rest/agile/1.0/board/{boardId}/sprint` and `/rest/api/3/search`)
> **Target**: Power BI Desktop / Power BI Service (GCC High)
> **Dataset**: `projects/it-project-mgmt-project/jira_issues.csv` (mock JIRA data)

---

## Data Model

### Star Schema Design

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│  dim_sprints     │     │    fact_issues         │     │  dim_assignees       │
│─────────────────│     │──────────────────────  │     │─────────────────────│
│ Sprint_Name (PK)│◄────│ Issue_Key (PK)         │────►│ Assignee (PK)        │
│ Sprint_Start    │     │ Issue_Type             │     │ Team                 │
│ Sprint_End      │     │ Summary                │     │ Role                 │
│ Sprint_Number   │     │ Status                 │     │ Capacity_Points      │
│ Sprint_Goal     │     │ Priority               │     └─────────────────────┘
└─────────────────┘     │ Sprint_Name (FK)       │
                        │ Story_Points           │     ┌─────────────────────┐
┌─────────────────┐     │ Assignee (FK)          │     │  dim_issue_types     │
│  dim_epics       │     │ Reporter               │     │─────────────────────│
│─────────────────│     │ Created_Date           │────►│ Issue_Type (PK)      │
│ Epic_Key (PK)   │◄────│ Updated_Date           │     │ Icon                 │
│ Epic_Summary    │     │ Resolved_Date          │     │ Color_Code           │
│ Epic_Status     │     │ Epic_Key (FK)          │     │ Sort_Order           │
│ Epic_Owner      │     │ Labels                 │     └─────────────────────┘
└─────────────────┘     │ Component              │
                        │ Issue_Type (FK)        │
                        └──────────────────────  ┘
```

### Relationships

| From Table | From Column | To Table | To Column | Cardinality | Cross-filter |
|-----------|-------------|----------|-----------|-------------|--------------|
| fact_issues | Sprint_Name | dim_sprints | Sprint_Name | Many-to-1 | Single |
| fact_issues | Assignee | dim_assignees | Assignee | Many-to-1 | Single |
| fact_issues | Epic_Key | dim_epics | Epic_Key | Many-to-1 | Single |
| fact_issues | Issue_Type | dim_issue_types | Issue_Type | Many-to-1 | Single |

---

## Tableau Calculated Fields → DAX Conversion

### 1. Sprint Velocity

**Tableau:**
```
SUM(
    IF [Status] = 'Done' THEN [Story_Points] END
)
```

**DAX Measure:**
```dax
Sprint Velocity =
CALCULATE(
    SUM(fact_issues[Story_Points]),
    fact_issues[Status] = "Done"
)
```

### 2. Burn-down Remaining (RUNNING_SUM in Reverse)

**Tableau (Table Calculation):**
```
RUNNING_SUM(SUM([Story_Points])) - RUNNING_SUM(
    SUM(IF [Status] = 'Done' THEN [Story_Points] END)
)
```

**DAX Measure:**
```dax
Burn-down Remaining =
VAR TotalPoints =
    CALCULATE(
        SUM(fact_issues[Story_Points]),
        ALLSELECTED(fact_issues)
    )
VAR CurrentDate = MAX('Calendar'[Date])
VAR CompletedToDate =
    CALCULATE(
        SUM(fact_issues[Story_Points]),
        fact_issues[Status] = "Done",
        fact_issues[Resolved_Date] <= CurrentDate,
        ALLSELECTED(fact_issues[Resolved_Date])
    )
RETURN
    TotalPoints - CompletedToDate
```

**Conversion Notes:**
- Tableau's `RUNNING_SUM` automatically accumulates across the table calc's addressing direction
- DAX requires explicit date logic using `FILTER` + `SUMX` to simulate the running window
- The burn-down chart in Power BI needs a Calendar table as the X-axis, with the measure calculating remaining points as of each date
- Use `ALLSELECTED` to respect slicer selections while removing date filters for the running total

### 3. Cycle Time

**Tableau:**
```
IF [Status] = 'Done' AND NOT ISNULL([Resolved_Date])
THEN DATEDIFF('day', [Created_Date], [Resolved_Date])
END
```

**DAX Measure:**
```dax
Avg Cycle Time (Days) =
AVERAGEX(
    FILTER(
        fact_issues,
        fact_issues[Status] = "Done"
            && NOT(ISBLANK(fact_issues[Resolved_Date]))
    ),
    DATEDIFF(
        fact_issues[Created_Date],
        fact_issues[Resolved_Date],
        DAY
    )
)
```

### 4. Lead Time

**Tableau:**
```
IF [Status] = 'Done'
THEN DATEDIFF('day', [Created_Date], [Resolved_Date])
ELSE DATEDIFF('day', [Created_Date], TODAY())
END
```

**DAX Measure:**
```dax
Avg Lead Time (Days) =
AVERAGEX(
    fact_issues,
    IF(
        fact_issues[Status] = "Done"
            && NOT(ISBLANK(fact_issues[Resolved_Date])),
        DATEDIFF(fact_issues[Created_Date], fact_issues[Resolved_Date], DAY),
        DATEDIFF(fact_issues[Created_Date], TODAY(), DAY)
    )
)
```

### 5. Story Points Completed vs Planned

**Tableau:**
```
// Completed
SUM(IF [Status] = 'Done' THEN [Story_Points] END)

// Planned (total committed to sprint)
SUM([Story_Points])
```

**DAX Measures:**
```dax
Story Points Completed =
CALCULATE(
    SUM(fact_issues[Story_Points]),
    fact_issues[Status] = "Done"
)

Story Points Planned =
SUM(fact_issues[Story_Points])

Completion Rate =
DIVIDE([Story Points Completed], [Story Points Planned], 0)
```

### 6. Bug Escape Rate

**Tableau:**
```
COUNTD(IF [Issue_Type] = 'Bug' THEN [Issue_Key] END)
/
COUNTD([Issue_Key])
```

**DAX Measure:**
```dax
Bug Escape Rate =
DIVIDE(
    CALCULATE(
        DISTINCTCOUNT(fact_issues[Issue_Key]),
        fact_issues[Issue_Type] = "Bug"
    ),
    DISTINCTCOUNT(fact_issues[Issue_Key]),
    0
)
```

### 7. Sprint Completion %

**Tableau:**
```
COUNTD(IF [Status] = 'Done' THEN [Issue_Key] END)
/
COUNTD([Issue_Key])
```

**DAX Measure:**
```dax
Sprint Completion % =
DIVIDE(
    CALCULATE(
        DISTINCTCOUNT(fact_issues[Issue_Key]),
        fact_issues[Status] = "Done"
    ),
    DISTINCTCOUNT(fact_issues[Issue_Key]),
    0
)
```

### 8. Stories by Status (COUNTD with IF)

**Tableau:**
```
COUNTD(IF [Status] = 'To Do' THEN [Issue_Key] END)
COUNTD(IF [Status] = 'In Progress' THEN [Issue_Key] END)
COUNTD(IF [Status] = 'In Review' THEN [Issue_Key] END)
COUNTD(IF [Status] = 'Done' THEN [Issue_Key] END)
```

**DAX Measures:**
```dax
Issues To Do =
CALCULATE(DISTINCTCOUNT(fact_issues[Issue_Key]), fact_issues[Status] = "To Do")

Issues In Progress =
CALCULATE(DISTINCTCOUNT(fact_issues[Issue_Key]), fact_issues[Status] = "In Progress")

Issues In Review =
CALCULATE(DISTINCTCOUNT(fact_issues[Issue_Key]), fact_issues[Status] = "In Review")

Issues Done =
CALCULATE(DISTINCTCOUNT(fact_issues[Issue_Key]), fact_issues[Status] = "Done")
```

### 9. Velocity Trend (WINDOW_AVG)

**Tableau (Table Calculation):**
```
WINDOW_AVG(SUM(IF [Status] = 'Done' THEN [Story_Points] END), -2, 0)
```

**DAX Measure:**
```dax
Velocity 3-Sprint Moving Avg =
VAR CurrentSprint = MAX(dim_sprints[Sprint_Number])
RETURN
AVERAGEX(
    FILTER(
        ALL(dim_sprints),
        dim_sprints[Sprint_Number] >= CurrentSprint - 2
            && dim_sprints[Sprint_Number] <= CurrentSprint
    ),
    CALCULATE(
        SUM(fact_issues[Story_Points]),
        fact_issues[Status] = "Done"
    )
)
```

**Conversion Notes:**
- Tableau's `WINDOW_AVG(expr, -2, 0)` computes a 3-period moving average (current + 2 prior)
- DAX uses `AVERAGEX` + `FILTER(ALL(...))` to create the sliding window
- The `ALL(dim_sprints)` removes the current filter context on sprints so the FILTER can look back
- Requires a `Sprint_Number` column for ordering (1-based integer)

### 10. Scope Creep (Stories Added Mid-Sprint)

**Tableau:**
```
COUNTD(
    IF [Created_Date] > [Sprint_Start]
       AND [Created_Date] <= [Sprint_End]
    THEN [Issue_Key]
    END
)
```

**DAX Measure:**
```dax
Scope Creep (Issues Added Mid-Sprint) =
CALCULATE(
    DISTINCTCOUNT(fact_issues[Issue_Key]),
    FILTER(
        fact_issues,
        fact_issues[Created_Date] > RELATED(dim_sprints[Sprint_Start])
            && fact_issues[Created_Date] <= RELATED(dim_sprints[Sprint_End])
    )
)
```

---

## Power Query M Script — JIRA REST API Connection

```m
// JIRA Cloud REST API — Power Query M Template
// Endpoints:
//   - Sprints: /rest/agile/1.0/board/{boardId}/sprint
//   - Issues: /rest/api/3/search
// Auth: Basic Auth (email:API_token) or OAuth 2.0
// Note: For FedRAMP, use JIRA Data Center behind VPN

let
    // --- Configuration ---
    // IMPORTANT: Store credentials in Power BI Parameters
    JiraBaseUrl = "https://your-instance.atlassian.net",
    BoardId = "926",  // Target board ID
    Email = Text.From(Excel.CurrentWorkbook(){[Name="JiraEmail"]}[Content]{0}[Column1]),
    ApiToken = Text.From(Excel.CurrentWorkbook(){[Name="JiraApiToken"]}[Content]{0}[Column1]),
    AuthHeader = "Basic " & Binary.ToText(
        Text.ToBinary(Email & ":" & ApiToken, TextEncoding.Utf8),
        BinaryEncoding.Base64
    ),

    // --- Step 1: Get All Sprints ---
    SprintsResponse = Json.Document(
        Web.Contents(
            JiraBaseUrl & "/rest/agile/1.0/board/" & BoardId & "/sprint",
            [
                Headers = [
                    #"Authorization" = AuthHeader,
                    #"Accept" = "application/json"
                ],
                Query = [state = "active,closed,future", maxResults = "50"]
            ]
        )
    ),
    SprintsList = SprintsResponse[values],

    // --- Step 2: Get Issues via JQL Search ---
    // Paginated — handle startAt and maxResults
    GetIssuesPage = (startAt as number) =>
        Json.Document(
            Web.Contents(
                JiraBaseUrl & "/rest/api/3/search",
                [
                    Headers = [
                        #"Authorization" = AuthHeader,
                        #"Content-Type" = "application/json",
                        #"Accept" = "application/json"
                    ],
                    Content = Json.FromValue([
                        jql = "project = UF ORDER BY created DESC",
                        startAt = startAt,
                        maxResults = 100,
                        fields = {
                            "issuetype", "summary", "status", "priority",
                            "customfield_10020", // Sprint
                            "story_points", "customfield_10028", // Story points
                            "assignee", "reporter", "created", "updated",
                            "resolutiondate", "customfield_10014", // Epic Link
                            "labels", "components"
                        }
                    ])
                ]
            )
        ),

    // --- Step 3: Paginate Through All Issues ---
    FirstPage = GetIssuesPage(0),
    TotalIssues = FirstPage[total],
    PageCount = Number.RoundUp(TotalIssues / 100),
    AllPages = List.Generate(
        () => [page = 0, data = FirstPage],
        each [page] < PageCount,
        each [
            page = [page] + 1,
            data = GetIssuesPage(([page] + 1) * 100)
        ],
        each [data][issues]
    ),
    AllIssues = List.Combine(AllPages),

    // --- Step 4: Convert to Table ---
    IssuesTable = Table.FromList(AllIssues, Splitter.SplitByNothing(), {"Record"}),
    ExpandedIssues = Table.ExpandRecordColumn(IssuesTable, "Record", {
        "key", "fields"
    }, {"Issue_Key", "fields"}),

    // --- Step 5: Expand Fields ---
    ExpandedFields = Table.ExpandRecordColumn(ExpandedIssues, "fields", {
        "issuetype", "summary", "status", "priority",
        "customfield_10020", "customfield_10028",
        "assignee", "reporter", "created", "updated",
        "resolutiondate", "customfield_10014", "labels", "components"
    }),

    // Flatten nested records (issuetype, status, priority, assignee, reporter)
    FlatType = Table.TransformColumns(ExpandedFields, {
        {"issuetype", each try _[name] otherwise null},
        {"status", each try _[name] otherwise null},
        {"priority", each try _[name] otherwise null},
        {"assignee", each try _[displayName] otherwise "Unassigned"},
        {"reporter", each try _[displayName] otherwise "Unknown"}
    }),

    // --- Step 6: Clean and Rename ---
    RenamedCols = Table.RenameColumns(FlatType, {
        {"issuetype", "Issue_Type"},
        {"summary", "Summary"},
        {"status", "Status"},
        {"priority", "Priority"},
        {"customfield_10028", "Story_Points"},
        {"assignee", "Assignee"},
        {"reporter", "Reporter"},
        {"created", "Created_Date"},
        {"updated", "Updated_Date"},
        {"resolutiondate", "Resolved_Date"},
        {"customfield_10014", "Epic_Key"},
        {"labels", "Labels"},
        {"components", "Component"}
    }),

    // --- Step 7: Data Types ---
    TypedTable = Table.TransformColumnTypes(RenamedCols, {
        {"Story_Points", Int64.Type},
        {"Created_Date", type datetime},
        {"Updated_Date", type datetime},
        {"Resolved_Date", type datetime}
    })
in
    TypedTable
```

---

## Dashboard Layout Specification

### Page 1: Sprint Overview

```
┌──────────────────────────────────────────────────────────────┐
│  IT PROJECT MANAGEMENT — SPRINT DASHBOARD                    │
│  [Sprint Slicer]  [Assignee Slicer]  [Epic Slicer]          │
├──────────┬──────────┬──────────┬──────────┬──────────────────┤
│ VELOCITY │  COMPL%  │  AVG     │  BUG     │  SCOPE           │
│   45 pts │   72%    │ CYCLE    │ ESCAPE   │  CREEP           │
│          │          │ 4.2 days │  18%     │  12 issues       │
├──────────┴──────────┴──────────┼──────────┴──────────────────┤
│                                │                              │
│   Sprint Velocity              │   Burn-down Chart            │
│   [Clustered Bar Chart]        │   [Line Chart]               │
│                                │                              │
│   S1 ████ 30                   │   ──────\                    │
│   S2 ██████ 38                 │          \────\              │
│   S3 ████████ 42               │               \──── (ideal) │
│   S4 █████████ 45              │          actual ──\          │
│   S5 ███████ 40                │                              │
│   S6 ██████ 35                 │   X: Sprint Day              │
│                                │   Y: Remaining Points        │
│   --- 3-Sprint Avg ---         │                              │
├────────────────────────────────┼──────────────────────────────┤
│                                │                              │
│   Story Status Distribution    │   Sprint Comparison Matrix   │
│   [Donut Chart]                │   [Matrix Visual]            │
│                                │                              │
│   ● Done        55%            │          S1  S2  S3  S4  S5 │
│   ● In Progress 20%            │   Vel    30  38  42  45  40 │
│   ● In Review   10%            │   Comp%  85% 72% 68% 65% 70│
│   ● To Do       15%            │   Bugs   3   5   8   6   4  │
│                                │   Scope+ 2   4   6   5   3  │
├────────────────────────────────┴──────────────────────────────┤
│                                                                │
│   Cycle Time Distribution                                      │
│   [Histogram]                                                  │
│                                                                │
│   ██                                                           │
│   ██ ██                                                        │
│   ██ ██ ██                                                     │
│   ██ ██ ██ ██                                                  │
│   1d 2d 3d 5d 8d 13d                                          │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### Page 2: Team Workload Heatmap

```
┌──────────────────────────────────────────────────────────────┐
│  TEAM WORKLOAD — ASSIGNEE × SPRINT                           │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│   [Matrix with Conditional Formatting]                         │
│                                                                │
│                  S1    S2    S3    S4    S5    S6    Total     │
│   ──────────────────────────────────────────────────────────  │
│   Alex T.       ██5   ██8   ██8   ██10  ██7   ██5    43     │
│   Jordan R.     ██3   ██5   ██6   ██8   ██8   ██6    36     │
│   Morgan C.     ██4   ██6   ██7   ██7   ██5   ██4    33     │
│   Casey W.      ██5   ██7   ██5   ██6   ██6   ██5    34     │
│   Taylor K.     ██3   ██4   ██5   ██5   ██4   ██3    24     │
│   ...                                                          │
│                                                                │
│   Color: Green (under capacity) → Red (over capacity)         │
│   Values: Story Points assigned                                │
│                                                                │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│   Epic Progress                                                │
│   [Stacked Bar Chart — % Complete by Epic]                    │
│                                                                │
│   Auth & SSO     ████████████████░░░░ 80%                     │
│   Analytics      ██████████░░░░░░░░░░ 50%                     │
│   Data Pipeline  ████████████░░░░░░░░ 60%                     │
│   Reporting      ██████░░░░░░░░░░░░░░ 30%                     │
│   FedRAMP        ████████████████░░░░ 80%                     │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

---

## Validation Approach

### Automated Validation Steps

1. **Row Count**: Verify all ~300 issues imported into Power BI
2. **Velocity Check**: Sum story points where Status = "Done" per sprint — compare DAX vs Python
3. **Burn-down Accuracy**: Verify remaining points decrease correctly over sprint dates
4. **Cycle Time**: Compute average days (Created → Resolved) for Done issues — compare DAX vs pandas
5. **Bug Escape Rate**: Verify Bug count / Total count per sprint
6. **Scope Creep**: Verify count of issues created after sprint start date

### Python Validation Script Pattern

```python
import pandas as pd

df = pd.read_csv("jira_issues.csv")

# Sprint velocity
velocity = df[df["Status"] == "Done"].groupby("Sprint_Name")["Story_Points"].sum()
print(f"Sprint Velocity:\n{velocity}")

# Cycle time
done = df[(df["Status"] == "Done") & df["Resolved_Date"].notna()].copy()
done["Created_Date"] = pd.to_datetime(done["Created_Date"])
done["Resolved_Date"] = pd.to_datetime(done["Resolved_Date"])
done["Cycle_Time"] = (done["Resolved_Date"] - done["Created_Date"]).dt.days
print(f"\nAvg Cycle Time: {done['Cycle_Time'].mean():.1f} days")

# Bug escape rate
bug_rate = len(df[df["Issue_Type"] == "Bug"]) / len(df)
print(f"\nBug Escape Rate: {bug_rate:.1%}")

# Scope creep
df["Created_Date"] = pd.to_datetime(df["Created_Date"])
df["Sprint_Start"] = pd.to_datetime(df["Sprint_Start"])
scope_creep = len(df[df["Created_Date"] > df["Sprint_Start"]])
print(f"\nScope Creep (issues added mid-sprint): {scope_creep}")

# Completion rate per sprint
completion = df.groupby("Sprint_Name").apply(
    lambda x: len(x[x["Status"] == "Done"]) / len(x)
)
print(f"\nSprint Completion Rate:\n{completion}")
```

### IV&V Compliance Artifacts

| Artifact | Description | NIST Control |
|----------|-------------|--------------|
| `sprint_velocity_baseline.json` | Expected velocity values per sprint for regression | SA-11 |
| `cycle_time_distribution.csv` | Full distribution of cycle times for statistical validation | SA-11(1) |
| `burn_down_daily_snapshots.csv` | Daily point values for burn-down chart verification | SI-12 |
| `scope_change_audit.csv` | Issues added/removed per sprint with timestamps | AU-2, CM-3 |
