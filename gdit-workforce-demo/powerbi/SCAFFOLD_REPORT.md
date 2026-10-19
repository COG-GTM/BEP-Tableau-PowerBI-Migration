# Tableau scaffold report

## Dashboard zones

| Dashboard | Zone | Source | Emitted type |
|---|---|---|---|
| Attrition Watch | `2` | KPI Headcount | native:clusteredColumnChart |
| Attrition Watch | `3` | KPI Vol Exits Latest | textbox |
| Attrition Watch | `4` | KPI Vol Exits Prior | textbox |
| Attrition Watch | `5` | KPI Attrition Ratio | textbox |
| Attrition Watch | `6` | Monthly Exits Trend | native:clusteredColumnChart |
| Attrition Watch | `7` | Exits by Division | textbox |
| Attrition Watch | `8` | Top Titles | textbox |
| Attrition Watch | `9` | Clearance x Family Heatmap | native:tableEx |
| Attrition Watch | `10` | Exits by State | textbox |
| Attrition Watch | `11` | [View As] | textbox |
| Attrition Watch | `12` | [Window Months] | textbox |
| Attrition Watch | `13` | [Top N Titles] | textbox |
| Staffing Risk | `2` | Revenue at Risk by Account | textbox |
| Staffing Risk | `3` | Past Due HC by Family x Clearance | textbox |
| Staffing Risk | `4` | Open Requests Detail | textbox |
| Staffing Risk | `5` | [View As] | textbox |
| Training Compliance | `2` | Overdue Rate by BU | textbox |
| Training Compliance | `3` | Overdue by Course Category | textbox |
| Headcount vs Budget | `2` | Headcount vs Budget | textbox |
| Headcount vs Budget | `3` | [As Of Quarter End] | textbox |

## Unmapped entries

- **Attrition Watch / 3** (KPI Vol Exits Latest): Unmapped worksheet KPI Vol Exits Latest: Bar worksheet lacks a dimension/measure shelf pairing
- **Attrition Watch / 4** (KPI Vol Exits Prior): Unmapped worksheet KPI Vol Exits Prior: Bar worksheet lacks a dimension/measure shelf pairing
- **Attrition Watch / 5** (KPI Attrition Ratio): Unmapped worksheet KPI Attrition Ratio: Bar worksheet lacks a dimension/measure shelf pairing
- **Attrition Watch / 7** (Exits by Division): Unmapped worksheet Exits by Division: Bar worksheet lacks a dimension/measure shelf pairing
- **Attrition Watch / 8** (Top Titles): Unmapped worksheet Top Titles: Bar worksheet lacks a dimension/measure shelf pairing
- **Attrition Watch / 10** (Exits by State): Unmapped worksheet Exits by State: Unsupported mark class map
- **Attrition Watch / 11** ([View As]): Unmapped filter/control: [View As]
- **Attrition Watch / 12** ([Window Months]): Unmapped filter/control: [Window Months]
- **Attrition Watch / 13** ([Top N Titles]): Unmapped filter/control: [Top N Titles]
- **Staffing Risk / 2** (Revenue at Risk by Account): Unmapped worksheet Revenue at Risk by Account: Bar worksheet lacks a dimension/measure shelf pairing
- **Staffing Risk / 3** (Past Due HC by Family x Clearance): Unmapped worksheet Past Due HC by Family x Clearance: Pivot worksheet has no mapped measure values
- **Staffing Risk / 4** (Open Requests Detail): Unmapped worksheet Open Requests Detail: Pivot worksheet has no mapped measure values
- **Staffing Risk / 5** ([View As]): Unmapped filter/control: [View As]
- **Training Compliance / 2** (Overdue Rate by BU): Unmapped worksheet Overdue Rate by BU: Bar worksheet lacks a dimension/measure shelf pairing
- **Training Compliance / 3** (Overdue by Course Category): Unmapped worksheet Overdue by Course Category: Bar worksheet lacks a dimension/measure shelf pairing
- **Headcount vs Budget / 2** (Headcount vs Budget): Unmapped worksheet Headcount vs Budget: Bar worksheet lacks a dimension/measure shelf pairing
- **Headcount vs Budget / 3** ([As Of Quarter End]): Unmapped filter/control: [As Of Quarter End]

## Dropped fields / substitutions

### Dropped fields
- Attrition Watch / KPI Vol Exits Latest: Vol Exits Latest (rows shelf; unresolved)
- Attrition Watch / KPI Vol Exits Latest: Vol Exits Latest (text encoding; unresolved)
- Attrition Watch / KPI Vol Exits Prior: Vol Exits Prior (rows shelf; unresolved)
- Attrition Watch / KPI Vol Exits Prior: Vol Exits Prior (text encoding; unresolved)
- Attrition Watch / KPI Attrition Ratio: Attrition Ratio (rows shelf; unresolved)
- Attrition Watch / KPI Attrition Ratio: Attrition Ratio (text encoding; unresolved)
- Attrition Watch / Monthly Exits Trend: Trailing 3M Vol Exits (rows shelf; unresolved)
- Attrition Watch / Monthly Exits Trend: Trailing 3M Vol Exits (text encoding; unresolved)
- Attrition Watch / Exits by Division: Vol Exits Latest (rows shelf; unresolved)
- Attrition Watch / Exits by Division: Vol Exits Latest (text encoding; unresolved)
- Attrition Watch / Top Titles: Vol Exits Latest (rows shelf; unresolved)
- Attrition Watch / Top Titles: Title Rank (rows shelf; unresolved)
- Attrition Watch / Top Titles: Vol Exits Latest (text encoding; unresolved)
- Attrition Watch / Clearance x Family Heatmap: Vol Exits Latest (rows shelf; unresolved)
- Attrition Watch / Clearance x Family Heatmap: Vol Exits Latest (text encoding; unresolved)
- Attrition Watch / Exits by State: Vol Exits Latest (rows shelf; unresolved)
- Attrition Watch / Exits by State: Vol Exits Latest (text encoding; unresolved)
- Staffing Risk / Revenue at Risk by Account: Revenue at Risk (Won contracts) (rows shelf; unresolved)
- Staffing Risk / Revenue at Risk by Account: Revenue at Risk (Won contracts) (text encoding; unresolved)
- Training Compliance / Overdue Rate by BU: Overdue Rate (rows shelf; unresolved)
- Training Compliance / Overdue Rate by BU: Division Overdue Rate (rows shelf; unresolved)
- Training Compliance / Overdue Rate by BU: Overdue Rate (text encoding; unresolved)
- Training Compliance / Overdue by Course Category: Overdue Rate (rows shelf; unresolved)
- Training Compliance / Overdue by Course Category: Overdue Rate (text encoding; unresolved)
- Headcount vs Budget / Headcount vs Budget: Headcount at As Of (rows shelf; unresolved)
- Headcount vs Budget / Headcount vs Budget: Budget Variance % (rows shelf; unresolved)
- Headcount vs Budget / Headcount vs Budget: Budget Variance % (color encoding; unresolved)
- Headcount vs Budget / Headcount vs Budget: Headcount at As Of (text encoding; unresolved)

### Substitutions
- None.

## Calculation translation status

| Calculation | Status | Class | Source formula | Reason | DAX |
|---|---|---|---|---|---|
| user_email (v_entitlement_expanded) | supported | row | [user_email] |  | 'v_entitlement_expanded'[user_email] |
| Entitlement OK | unsupported | row | [user_email (v_entitlement_expanded)] = [View As] | Unknown field 'View As' |  |
| Is Active | supported | row | ISNULL([term_date]) |  | ISBLANK('workers'[term_date]) |
| Months Ago Term | unsupported | row | DATEDIFF('month', [term_date], DATETRUNC('month', TODAY())) | Unsupported function DATETRUNC |  |
| Latest Window | unsupported | row | [Months Ago Term] >= 1 AND [Months Ago Term] <= [Window Months] | depends on Months Ago Term |  |
| Prior Window | unsupported | row | [Months Ago Term] > [Window Months] AND [Months Ago Term] <= 2*[Window Months] | depends on Months Ago Term |  |
| Voluntary Exit ID | supported | row | IF [term_type]='Voluntary' THEN [worker_id] END |  | IF(('workers'[term_type] = "Voluntary"), 'workers'[worker_id]) |
| Vol Exits Latest | unsupported | aggregate | COUNTD(IF [Latest Window] THEN [Voluntary Exit ID] END) | depends on Latest Window |  |
| Vol Exits Prior | unsupported | aggregate | COUNTD(IF [Prior Window] THEN [Voluntary Exit ID] END) | depends on Prior Window |  |
| Attrition Ratio | unsupported | aggregate | [Vol Exits Latest] / [Vol Exits Prior] | depends on Vol Exits Latest |  |
| Headcount | supported | aggregate | COUNTD(IF [Is Active] THEN [worker_id] END) |  | COUNTROWS(FILTER(DISTINCT(SELECTCOLUMNS('workers', "__v", IF('workers'[Is Active], 'workers'[worker_id]))), NOT ISBLANK([__v]))) |
| Headcount at As Of | unsupported | aggregate | COUNTD(IF [hire_date] <= [As Of Quarter End] AND (ISNULL([term_date]) OR [term_date] > [As Of Quarter End]) THEN [worker_id] END) | Unknown field 'As Of Quarter End' |  |
| Tenure at Exit (yrs) | needs_override | lod | {FIXED [worker_id]: MIN(DATEDIFF('day', [hire_date], [term_date]))} / 365.25 |  |  |
| Division Avg Salary | needs_override | lod | {FIXED [division]: AVG([base_salary])} |  |  |
| Salary vs Division Avg | unsupported | aggregate | AVG([base_salary]) / AVG([Division Avg Salary]) - 1 | depends on Division Avg Salary |  |
| Title Exits (INCLUDE) | unsupported | lod | {INCLUDE [job_title]: [Vol Exits Latest]} | depends on Vol Exits Latest |  |
| Division Headcount | needs_override | lod | {FIXED [division]: COUNTD(IF [Is Active] THEN [worker_id] END)} |  |  |
| Vol Exits Monthly | supported | aggregate | COUNTD([Voluntary Exit ID]) |  | DISTINCTCOUNT('workers'[Voluntary Exit ID]) |
| Monthly Vol Exits YoY % | table_calc | table_calc | (SUM([Vol Exits Monthly]) - LOOKUP(SUM([Vol Exits Monthly]), -12)) / ABS(LOOKUP(SUM([Vol Exits Monthly]), -12)) |  |  |
| Trailing 3M Vol Exits | table_calc | table_calc | WINDOW_SUM(COUNTD([Voluntary Exit ID]), -2, 0) |  |  |
| Running Vol Exits YTD | table_calc | table_calc | RUNNING_SUM(COUNTD([Voluntary Exit ID])) |  |  |
| Title Rank | unsupported | table_calc | RANK(COUNTD(IF [Latest Window] THEN [Voluntary Exit ID] END)) | depends on Latest Window |  |
| Overdue Rate | unsupported | unsupported | SUM(IF [status] = 'Overdue' THEN 1 ELSE 0 END) / SUM(IF [status] IN ('Completed', 'Overdue') THEN 1 ELSE 0 END) | Expected THEN at position 65, found 'IN' |  |
| Division Overdue Rate | unsupported | unsupported | {FIXED [division], [category]: SUM(IF [status]='Overdue' THEN 1 ELSE 0 END) / SUM(IF [status] IN ('Completed','Overdue') THEN 1 ELSE 0 END)} | Expected THEN at position 94, found 'IN' |  |
| Fiscal Year | unsupported | row | "FY" + RIGHT(STR(YEAR([As Of Quarter End])),2) | Unknown field 'As Of Quarter End' |  |
| Fiscal Quarter | unsupported | row | "Q" + STR(DATEPART('quarter',[As Of Quarter End])) | Unknown field 'As Of Quarter End' |  |
| Budget Variance % | unsupported | aggregate | [Headcount at As Of] / SUM([FY Budget (extract)].[headcount_budget]) - 1 | depends on Headcount at As Of |  |
| user_email (v_entitlement_expanded) | supported | row | [user_email] |  | 'v_entitlement_expanded'[user_email] |
| Entitlement OK | unsupported | row | [user_email (v_entitlement_expanded)] = [View As] | Unknown field 'View As' |  |
| Past Due Open HC | supported | row | IF [stage]='Won' AND [status]='Open' AND [needed_by] < TODAY() THEN [headcount] ELSE 0 END |  | IF(((('opportunities'[stage] = "Won") && ('training_completions'[status] = "Open")) && ('staffing_requests'[needed_by] < TODAY())), 'staffing_requests'[headcount], 0) |
| Opp Amount | needs_override | lod | {FIXED [opp_id]: MIN([amount])} |  |  |
| Opp Requested HC | needs_override | lod | {FIXED [opp_id]: SUM([headcount])} |  |  |
| Opp Past Due HC | needs_override | lod | {FIXED [opp_id]: SUM([Past Due Open HC])} |  |  |
| Revenue at Risk (Won contracts) | unsupported | aggregate | SUM(IF [stage]='Won' THEN [amount] * [Past Due Open HC] / [Opp Requested HC] ELSE 0 END) | depends on Opp Requested HC |  |
