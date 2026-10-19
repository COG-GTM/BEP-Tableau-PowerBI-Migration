# Tableau migration report: GDIT Workforce & Pipeline

## Tables and extracted rows

| Table | Hyper table | Rows | Columns |
|---|---|---:|---:|
| workers | `workers` | 0 | 23 |
| worker_events | `worker_events` | 0 | 6 |
| training_completions | `training_completions` | 0 | 8 |
| courses | `courses` | 0 | 5 |
| v_entitlement_expanded | `v_entitlement_expanded` | 0 | 2 |
| opportunities | `opportunities` | 0 | 11 |
| staffing_requests | `staffing_requests` | 0 | 11 |
| FY Headcount Budget | `FY Headcount Budget` | 0 | 6 |

## Relationships

- `workers.worker_id` → `worker_events.worker_id`
- `workers.worker_id` → `training_completions.worker_id`
- `training_completions.course_code` → `courses.course_code`
- `workers.division` → `v_entitlement_expanded.division`
- `opportunities.opp_id` → `staffing_requests.opp_id`
- `opportunities.division` → `v_entitlement_expanded.division`

## Calculations

| Caption | Class | Status | DAX / reason |
|---|---|---|---|
| user_email (v_entitlement_expanded) | row | supported | `'v_entitlement_expanded'[user_email]` |
| Entitlement OK | row | unsupported | `Unknown field 'View As'` |
| Is Active | row | supported | `ISBLANK('workers'[term_date])` |
| Months Ago Term | row | supported | `DATEDIFF('workers'[term_date], DATE(YEAR(TODAY()), MONTH(TODAY()), 1), MONTH)` |
| Latest Window | row | unsupported | `Unknown field 'Window Months'` |
| Prior Window | row | unsupported | `Unknown field 'Window Months'` |
| Voluntary Exit ID | row | supported | `IF(('workers'[term_type] = "Voluntary"), 'workers'[worker_id])` |
| Vol Exits Latest | aggregate | unsupported | `depends on Latest Window` |
| Vol Exits Prior | aggregate | unsupported | `depends on Prior Window` |
| Attrition Ratio | aggregate | unsupported | `depends on Vol Exits Latest` |
| Headcount | aggregate | supported | `COUNTROWS(FILTER(DISTINCT(SELECTCOLUMNS('workers', "__v", IF('workers'[Is Active], 'workers'[worker_id]))), NOT ISBLANK([__v])))` |
| Headcount at As Of | aggregate | unsupported | `Unknown field 'As Of Quarter End'` |
| Tenure at Exit (yrs) | lod | needs_override | `` |
| Division Avg Salary | lod | needs_override | `` |
| Salary vs Division Avg | aggregate | unsupported | `depends on Division Avg Salary` |
| Title Exits (INCLUDE) | lod | unsupported | `depends on Vol Exits Latest` |
| Division Headcount | lod | needs_override | `` |
| Vol Exits Monthly | aggregate | supported | `DISTINCTCOUNT('workers'[Voluntary Exit ID])` |
| Monthly Vol Exits YoY % | table_calc | table_calc | `` |
| Trailing 3M Vol Exits | table_calc | table_calc | `` |
| Running Vol Exits YTD | table_calc | table_calc | `` |
| Title Rank | table_calc | unsupported | `depends on Latest Window` |
| Overdue Rate | aggregate | supported | `DIVIDE(SUMX('workers', IF(('training_completions'[status] = "Overdue"), 1, 0)), SUMX('workers', IF(('training_completions'[status] IN {"Completed", "Overdue"}), 1, 0)))` |
| Division Overdue Rate | lod | needs_override | `` |
| Fiscal Year | row | unsupported | `Unknown field 'As Of Quarter End'` |
| Fiscal Quarter | row | unsupported | `Unknown field 'As Of Quarter End'` |
| Budget Variance % | aggregate | unsupported | `depends on Headcount at As Of` |
| user_email (v_entitlement_expanded) | row | supported | `'v_entitlement_expanded'[user_email]` |
| Entitlement OK | row | unsupported | `Unknown field 'View As'` |
| Past Due Open HC | row | supported | `IF(((('opportunities'[stage] = "Won") && ('training_completions'[status] = "Open")) && ('staffing_requests'[needed_by] < TODAY())), 'staffing_requests'[headcount], 0)` |
| Opp Amount | lod | needs_override | `` |
| Opp Requested HC | lod | needs_override | `` |
| Opp Past Due HC | lod | needs_override | `` |
| Revenue at Risk (Won contracts) | aggregate | unsupported | `depends on Opp Requested HC` |

## Auto measures


## Lead overrides

- Measure **Headcount**: `CALCULATE(DISTINCTCOUNT('workers'[worker_id]), ISBLANK('workers'[term_date]))` (format `#,##0`)
- Measure **Vol Exits Latest**: `VAR WindowMonths = SELECTEDVALUE('Window Months'[Window Months], 3)
VAR LastFullMonth = EOMONTH(TODAY(), -1)
RETURN
    CALCULATE(
        [Vol Exits Monthly],
        DATESBETWEEN(
            'Calendar'[Date],
            EOMONTH(LastFullMonth, -WindowMonths) + 1,
            LastFullMonth
        )
    )
` (format `#,##0`)
- Measure **Vol Exits Prior**: `VAR WindowMonths = SELECTEDVALUE('Window Months'[Window Months], 3)
VAR LastFullMonth = EOMONTH(TODAY(), -1)
VAR PriorEnd = EOMONTH(LastFullMonth, -WindowMonths)
VAR PriorStart = EOMONTH(LastFullMonth, -2 * WindowMonths) + 1
RETURN
    CALCULATE(
        [Vol Exits Monthly],
        DATESBETWEEN('Calendar'[Date], PriorStart, PriorEnd)
    )
` (format `#,##0`)
- Measure **Attrition Ratio**: `DIVIDE([Vol Exits Latest], [Vol Exits Prior])` (format `0.00x`)
- Measure **Headcount at As Of**: `VAR AsOfDate = SELECTEDVALUE('As Of Quarter End'[As Of Quarter End], DATE(2026, 9, 30))
RETURN
    CALCULATE(
        DISTINCTCOUNT('workers'[worker_id]),
        FILTER(
            'workers',
            'workers'[hire_date] <= AsOfDate
                && (ISBLANK('workers'[term_date]) || 'workers'[term_date] > AsOfDate)
        )
    )
` (format `#,##0`)
- Measure **Tenure at Exit (yrs)**: `AVERAGEX(
    FILTER('workers', NOT ISBLANK('workers'[term_date])),
    DIVIDE(DATEDIFF('workers'[hire_date], 'workers'[term_date], DAY), 365.25)
)
` (format `0.0`)
- Measure **Division Avg Salary**: `CALCULATE(AVERAGE('workers'[base_salary]), ALLEXCEPT('workers', 'workers'[division]))` (format `$#,##0`)
- Measure **Salary vs Division Avg**: `DIVIDE(AVERAGE('workers'[base_salary]) - [Division Avg Salary], [Division Avg Salary])` (format `0.0%;-0.0%;-`)
- Measure **Title Exits (INCLUDE)**: `SUMX(VALUES('workers'[job_title]), [Vol Exits Latest])` (format `#,##0`)
- Measure **Division Headcount**: `CALCULATE([Headcount], ALLEXCEPT('workers', 'workers'[division]))` (format `#,##0`)
- Measure **Vol Exits Monthly**: `CALCULATE(DISTINCTCOUNT('workers'[worker_id]), 'workers'[term_type] = "Voluntary")` (format `#,##0`)
- Measure **Monthly Vol Exits YoY %**: `VAR CurrentExits = [Vol Exits Monthly]
VAR PriorYearExits =
    CALCULATE([Vol Exits Monthly], DATEADD('Calendar'[Date], -12, MONTH))
RETURN DIVIDE(CurrentExits - PriorYearExits, PriorYearExits)
` (format `0.0%;-0.0%;-`)
- Measure **Trailing 3M Vol Exits**: `CALCULATE(
    [Vol Exits Monthly],
    DATESINPERIOD('Calendar'[Date], MAX('Calendar'[Date]), -2, MONTH)
)
` (format `#,##0`)
- Measure **Running Vol Exits YTD**: `CALCULATE([Vol Exits Monthly], DATESYTD('Calendar'[Date]))` (format `#,##0`)
- Measure **Title Rank**: `RANKX(ALLSELECTED('workers'[job_title]), [Vol Exits Latest], , DESC, DENSE)` (format `0`)
- Measure **Top N Title Exits**: `VAR TopNCount = SELECTEDVALUE('Top N Titles'[Top N Titles], 10)
VAR TopTitles =
    TOPN(
        TopNCount,
        ALLSELECTED('workers'[job_title]),
        [Vol Exits Latest], DESC,
        'workers'[job_title], ASC
    )
VAR CurrentTitle = SELECTEDVALUE('workers'[job_title])
RETURN
    IF(
        CONTAINS(TopTitles, 'workers'[job_title], CurrentTitle),
        [Vol Exits Latest]
    )
` (format `#,##0`)
- Measure **Overdue Rate**: `DIVIDE(
    CALCULATE(
        COUNTROWS('training_completions'),
        'training_completions'[status] = "Overdue"
    ),
    CALCULATE(
        COUNTROWS('training_completions'),
        'training_completions'[status] IN {"Completed", "Overdue"}
    )
)
` (format `0.0%;-0.0%;-`)
- Measure **Security Overdue Rate**: `CALCULATE([Overdue Rate], 'courses'[category] = "Security")` (format `0.0%;-0.0%;-`)
- Measure **Division Overdue Rate**: `CALCULATE(
    [Security Overdue Rate],
    ALLEXCEPT('workers', 'workers'[division], 'workers'[business_unit])
)
` (format `0.0%;-0.0%;-`)
- Measure **Fiscal Year**: `VAR AsOfDate = SELECTEDVALUE('As Of Quarter End'[As Of Quarter End], DATE(2026, 9, 30))
RETURN "FY" & FORMAT(MOD(YEAR(AsOfDate), 100), "00")
`
- Measure **Fiscal Quarter**: `VAR AsOfDate = SELECTEDVALUE('As Of Quarter End'[As Of Quarter End], DATE(2026, 9, 30))
RETURN "Q" & FORMAT(ROUNDUP(MONTH(AsOfDate) / 3, 0), "0")
`
- Measure **Budget Variance %**: `VAR AsOfDate = SELECTEDVALUE('As Of Quarter End'[As Of Quarter End], DATE(2026, 9, 30))
VAR YearKey = "FY" & FORMAT(MOD(YEAR(AsOfDate), 100), "00")
VAR QuarterKey = "Q" & FORMAT(ROUNDUP(MONTH(AsOfDate) / 3, 0), "0")
VAR PeriodKey = YearKey & "|" & QuarterKey
VAR Budget =
    CALCULATE(
        SUM('FY Headcount Budget'[headcount_budget]),
        'Fiscal Period'[Fiscal Period Key] = PeriodKey
    )
RETURN DIVIDE([Headcount at As Of] - Budget, Budget)
` (format `0.0%;-0.0%;-`)
- Measure **Budget Headcount**: `SUM('FY Headcount Budget'[headcount_budget])` (format `#,##0`)
- Measure **Opp Amount**: `SUM('opportunities'[amount])` (format `$#,##0`)
- Measure **Opp Requested HC**: `CALCULATE(SUM('staffing_requests'[headcount]), ALLEXCEPT('staffing_requests', 'staffing_requests'[opp_id]))` (format `#,##0`)
- Measure **Past Due Open HC**: `CALCULATE(
    SUM('staffing_requests'[headcount]),
    'staffing_requests'[status] = "Open",
    'staffing_requests'[needed_by] < TODAY(),
    'opportunities'[stage] = "Won"
)
` (format `#,##0`)
- Measure **Opp Past Due HC**: `[Past Due Open HC]` (format `#,##0`)
- Measure **Revenue at Risk (Won contracts)**: `SUMX(
    FILTER(
        'staffing_requests',
        'staffing_requests'[status] = "Open"
            && 'staffing_requests'[needed_by] < TODAY()
            && RELATED('opportunities'[stage]) = "Won"
    ),
    DIVIDE(
        RELATED('opportunities'[amount]) * [Past Due Open HC],
        [Opp Requested HC]
    )
)
` (format `$#,##0.00`)
- Calculated column **FY Headcount Budget.Fiscal Period Key**: `'FY Headcount Budget'[fiscal_year] & "|" & 'FY Headcount Budget'[fiscal_quarter]` (string)
- Calculated table **Division**: columns division (string); DAX `DISTINCT(
    UNION(
        SELECTCOLUMNS('workers', "division", 'workers'[division]),
        SELECTCOLUMNS('opportunities', "division", 'opportunities'[division]),
        SELECTCOLUMNS('FY Headcount Budget', "division", 'FY Headcount Budget'[division]),
        SELECTCOLUMNS('v_entitlement_expanded', "division", 'v_entitlement_expanded'[division])
    )
)`
- Calculated table **Calendar**: columns Date (date), Month Start (date), Fiscal Year (string), Fiscal Quarter (string), Fiscal Period Key (string); DAX `VAR Dates = CALENDAR(DATE(2021, 1, 1), TODAY())
RETURN
    ADDCOLUMNS(
        Dates,
        "Month Start", DATE(YEAR([Date]), MONTH([Date]), 1),
        "Fiscal Year", "FY" & FORMAT(MOD(YEAR([Date]), 100), "00"),
        "Fiscal Quarter", "Q" & FORMAT(ROUNDUP(MONTH([Date]) / 3, 0), "0"),
        "Fiscal Period Key",
            "FY" & FORMAT(MOD(YEAR([Date]), 100), "00")
                & "|Q" & FORMAT(ROUNDUP(MONTH([Date]) / 3, 0), "0")
    )`
- Calculated table **Fiscal Period**: columns Fiscal Year (string), Fiscal Quarter (string), Fiscal Period Key (string); DAX `DISTINCT(
    SELECTCOLUMNS(
        'FY Headcount Budget',
        "Fiscal Year", 'FY Headcount Budget'[fiscal_year],
        "Fiscal Quarter", 'FY Headcount Budget'[fiscal_quarter],
        "Fiscal Period Key", 'FY Headcount Budget'[Fiscal Period Key]
    )
)`
- Relationship `workers.worker_id` → `worker_events.worker_id` (oneDirection)
- Relationship `workers.worker_id` → `training_completions.worker_id` (oneDirection)
- Relationship `training_completions.course_code` → `courses.course_code` (oneDirection)
- Relationship `opportunities.opp_id` → `staffing_requests.opp_id` (oneDirection)
- Relationship `FY Headcount Budget.Fiscal Period Key` → `Fiscal Period.Fiscal Period Key` (oneDirection)
- Relationship `Calendar.Fiscal Period Key` → `Fiscal Period.Fiscal Period Key` (oneDirection)
- Relationship `workers.division` → `Division.division` (oneDirection)
- Relationship `opportunities.division` → `Division.division` (oneDirection)
- Relationship `FY Headcount Budget.division` → `Division.division` (oneDirection)
- Relationship `workers.term_date` → `Calendar.Date` (oneDirection)

## Visuals

| Dashboard | ID | Type | Position | Fields |
|---|---|---|---|---|
| Attrition Watch | `z_0_2` | native | `{"x":0,"y":0,"w":288,"h":126,"z":1200}` | `[{"role": "Values", "field": "workers.Headcount"}]` |
| Attrition Watch | `z_1_3` | native | `{"x":288,"y":0,"w":288,"h":126,"z":1201}` | `[{"role": "Values", "field": "workers.Vol Exits Latest"}]` |
| Attrition Watch | `z_2_4` | native | `{"x":576,"y":0,"w":288,"h":126,"z":1202}` | `[{"role": "Values", "field": "workers.Vol Exits Prior"}]` |
| Attrition Watch | `z_3_5` | native | `{"x":864,"y":0,"w":288,"h":126,"z":1203}` | `[{"role": "Values", "field": "workers.Attrition Ratio"}]` |
| Attrition Watch | `z_4_6` | native | `{"x":0,"y":126,"w":1040,"h":324,"z":1300}` | `[{"role": "Category", "field": "Calendar.Month Start"}, {"role": "Y", "field": "workers.Vol Exits Monthly"}, {"role": "Y2", "field": "workers.Trailing 3M Vol Exits"}]` |
| Attrition Watch | `z_5_7` | native | `{"x":1040,"y":126,"w":560,"h":324,"z":500}` | `[{"role": "Category", "field": "workers.division"}, {"role": "Y", "field": "workers.Vol Exits Latest"}]` |
| Attrition Watch | `z_6_8` | native | `{"x":0,"y":450,"w":528,"h":450,"z":600}` | `[{"role": "Category", "field": "workers.job_title"}, {"role": "Y", "field": "workers.Top N Title Exits"}]` |
| Attrition Watch | `z_7_9` | native | `{"x":528,"y":450,"w":544,"h":450,"z":1400}` | `[{"role": "Rows", "field": "workers.clearance_level"}, {"role": "Columns", "field": "workers.job_family"}, {"role": "Values", "field": "workers.Vol Exits Latest"}]` |
| Attrition Watch | `z_8_10` | native | `{"x":1072,"y":450,"w":528,"h":450,"z":800}` | `[{"role": "Category", "field": "workers.location_state"}, {"role": "Color", "field": "workers.Vol Exits Latest"}]` |
| Attrition Watch | `z_9_11` | textbox | `{"x":1152,"y":0,"w":148,"h":126,"z":900}` | `[]` |
| Attrition Watch | `z_10_12` | slicer | `{"x":1300,"y":0,"w":148,"h":126,"z":900}` | `[{"field": "Window Months.Window Months"}]` |
| Attrition Watch | `z_11_13` | slicer | `{"x":1448,"y":0,"w":152,"h":126,"z":1000}` | `[{"field": "Top N Titles.Top N Titles"}]` |
| Staffing Risk | `z_4_6` | native | `{"x":0,"y":0,"w":320,"h":126,"z":400}` | `[{"role": "Values", "field": "workers.Revenue at Risk (Won contracts)"}]` |
| Staffing Risk | `z_0_2` | native | `{"x":0,"y":126,"w":1040,"h":549,"z":0}` | `[{"role": "Category", "field": "opportunities.account_name"}, {"role": "Y", "field": "workers.Revenue at Risk (Won contracts)"}, {"role": "Y2", "field": "workers.Past Due Open HC"}]` |
| Staffing Risk | `z_1_3` | native | `{"x":1040,"y":126,"w":560,"h":549,"z":100}` | `[{"role": "Rows", "field": "staffing_requests.job_family"}, {"role": "Columns", "field": "staffing_requests.clearance_required"}, {"role": "Values", "field": "workers.Past Due Open HC"}]` |
| Staffing Risk | `z_2_4` | native | `{"x":0,"y":675,"w":1600,"h":225,"z":200}` | `[{"role": "Values", "field": "staffing_requests.req_id"}, {"role": "Values", "field": "staffing_requests.opp_id"}, {"role": "Values", "field": "staffing_requests.job_family"}, {"role": "Values", "field": "staffing_requests.clearance_required"}, {"role": "Values", "field": "staffing_requests.headcount"}, {"role": "Values", "field": "staffing_requests.needed_by"}, {"role": "Values", "field": "workers.Past Due Open HC"}]` |
| Staffing Risk | `z_3_5` | textbox | `{"x":1360,"y":0,"w":240,"h":90,"z":300}` | `[]` |
| Training Compliance | `z_2_4` | native | `{"x":0,"y":0,"w":320,"h":126,"z":200}` | `[{"role": "Values", "field": "workers.Security Overdue Rate"}]` |
| Training Compliance | `z_0_2` | native | `{"x":0,"y":126,"w":800,"h":774,"z":0}` | `[{"role": "Category", "field": "workers.business_unit"}, {"role": "Y", "field": "workers.Overdue Rate"}, {"role": "Y2", "field": "workers.Division Overdue Rate"}]` |
| Training Compliance | `z_1_3` | native | `{"x":800,"y":126,"w":800,"h":774,"z":100}` | `[{"role": "Category", "field": "courses.category"}, {"role": "Y", "field": "workers.Overdue Rate"}]` |
| Headcount vs Budget | `z_2_4` | native | `{"x":0,"y":0,"w":320,"h":126,"z":200}` | `[{"role": "Values", "field": "workers.Budget Variance %"}]` |
| Headcount vs Budget | `z_0_2` | native | `{"x":0,"y":126,"w":1600,"h":774,"z":0}` | `[{"role": "Category", "field": "Division.division"}, {"role": "Y", "field": "workers.Headcount at As Of"}, {"role": "Y2", "field": "workers.Budget Headcount"}]` |
| Headcount vs Budget | `z_1_3` | slicer | `{"x":1312,"y":0,"w":288,"h":90,"z":100}` | `[{"field": "As Of Quarter End.As Of Quarter End"}]` |

## Duplicate-key conflicts

- None.
