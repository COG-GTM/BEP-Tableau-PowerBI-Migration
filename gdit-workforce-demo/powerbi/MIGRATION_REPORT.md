# GDIT Tableau → Power BI migration report

The converted project is in `output/GDIT Workforce & Pipeline.pbip`. The
Tableau inventory is 3 authored data sources plus the Tableau `Parameters`
source, 8 physical tables, 6 source relationships, 4 parameters, 34 calculated
fields, 2 sets, 16 worksheets, 4 dashboards, and 3 actions.

`exact` means the same model object/meaning is retained; `equivalent` means a
Power BI implementation provides the same user-facing result; `semantic
change` records an intentional change in evaluation/security semantics; and
`manual` means a Desktop-only visual/interaction decision remains.

| Source object | Power BI target | Status | Note |
|---|---|---|---|
| Workforce (live) PostgreSQL source | DirectQuery M source using `Host` parameter | equivalent | Pooler host is parameterized; set connector credentials externally as `tableau_reader.<project_ref>`. No password is stored. |
| Pipeline (live) PostgreSQL source | DirectQuery M source using `Host` parameter | equivalent | Same PostgreSQL endpoint and external credential requirement as Workforce. |
| FY Budget (extract) Excel/Hyper source | `FY Headcount Budget` Excel Import table | semantic change | Reads the Excel source by the `BudgetFile` M path parameter; Power BI refresh replaces the embedded Tableau Hyper extract. |
| Tableau Parameters source | Disconnected Power BI parameter tables | equivalent | The `View As` parameter is deliberately omitted and replaced by RLS roles. |
| `workday.workers` | DirectQuery table `workers` | exact | Workforce fact table. |
| `workday.worker_events` | DirectQuery table `worker_events` | exact | Worker event history. |
| `oracle_lms.training_completions` | DirectQuery table `training_completions` | exact | Training completion/status facts. |
| `oracle_lms.courses` | DirectQuery table `courses` | exact | Course category dimension. |
| `security.v_entitlement_expanded` | Hidden, disconnected DirectQuery table plus `Entitlement` role | semantic change | Division entitlement is enforced by a DAX filter on `Division[division]`; the entitlement table has no model relationship. |
| `salesforce.opportunities` | DirectQuery table `opportunities` | exact | Pipeline opportunity fact/dimension. |
| `salesforce.staffing_requests` | DirectQuery table `staffing_requests` | exact | Request-grain pipeline facts. |
| FY budget Excel worksheet | `FY Headcount Budget` Import table | equivalent | No database budget table or embedded credentials are used. |
| workers → worker_events on worker_id (1:*) | `worker_events.worker_id` → `workers.worker_id` | equivalent | Normalized many-to-one TMDL orientation; the many side is emitted as `fromColumn`. |
| workers → training_completions on worker_id (1:*) | `training_completions.worker_id` → `workers.worker_id` | equivalent | Normalized many-to-one TMDL orientation; the many side is emitted as `fromColumn`. |
| training_completions → courses on course_code (*:1) | `training_completions.course_code` → `courses.course_code` | equivalent | Explicit many-to-one relationship. |
| opportunities → staffing_requests on opp_id (1:*) | `staffing_requests.opp_id` → `opportunities.opp_id` | equivalent | Normalized many-to-one TMDL orientation; the many side is emitted as `fromColumn`. |
| workers ↔ v_entitlement_expanded on division (*:*) | Disconnected `v_entitlement_expanded` plus `Entitlement` filter on `Division[division]` | semantic change | No relationship or bidirectional security filter is emitted; the role uses `USERPRINCIPALNAME()` in `CALCULATETABLE(VALUES(...))`. |
| opportunities ↔ v_entitlement_expanded on division (*:*) | Disconnected `v_entitlement_expanded` plus the same `Entitlement` filter on `Division[division]` | semantic change | Source many-to-many relationship is omitted; the dynamic role filters the shared Division dimension instead. |
| v_entitlement_expanded visibility | Hidden table | semantic change | The DirectQuery entitlement source remains available to the role but is hidden from report authors and disconnected from model tables. |
| `[View As]` parameter | No parameter; `Entitlement`, `Defense Lead`, `Intel Lead`, and `Exec` roles | semantic change | The effective identity is the Power BI user/role, not a report control. |
| Added `Defense Lead` test role | `Division` role filter for Defense | semantic change | Static role retained for Desktop's View as role testing. |
| Added `Intel Lead` test role | `Division` role filter for Intelligence | semantic change | Static role retained for Desktop's View as role testing. |
| Added `Exec` test role | `Division` role filter for all four divisions | semantic change | Static role retained for Desktop's View as role testing. |
| `[Window Months]` parameter | What-if table `Window Months` | equivalent | Disconnected integer table; measures use `SELECTEDVALUE` with a 3-month fallback. |
| `[Top N Titles]` parameter | What-if table `Top N Titles` | equivalent | Disconnected integer table consumed by `TOPN`. |
| `[As Of Quarter End]` parameter | Disconnected date table `As Of Quarter End` | equivalent | Measures use `SELECTEDVALUE`, defaulting to 2026-09-30. |
| `[Entitlement OK]` (Workforce) | `Entitlement` DAX role on `Division` | semantic change | Tableau data-source filtering is replaced by `Division[division] IN CALCULATETABLE(VALUES(v_entitlement_expanded[division]), v_entitlement_expanded[user_email] = USERPRINCIPALNAME())`. |
| `[Is Active]` | `workers.Is Active` calculated field | equivalent | Blank `term_date` denotes active, as in Tableau. |
| `[Months Ago Term]` | DAX month difference using the calendar | equivalent | Uses month-truncated dates; the generic `DATETRUNC` translator now covers month, quarter, year, and day. |
| `[Latest Window]` | `[Vol Exits Latest]` measure | equivalent | Dynamic date-window logic is evaluated in the measure rather than a Tableau row filter. |
| `[Prior Window]` | `[Vol Exits Prior]` measure | equivalent | Uses the immediately preceding window of the selected length. |
| `[Voluntary Exit ID]` | `workers.Voluntary Exit ID` | equivalent | Returns worker ID only for voluntary terminations. |
| `[Vol Exits Latest]` | `workers.Vol Exits Latest` measure | equivalent | Counts voluntary exits in the last N full months. |
| `[Vol Exits Prior]` | `workers.Vol Exits Prior` measure | equivalent | Counts the prior N full months. |
| `[Attrition Ratio]` | `workers.Attrition Ratio` measure | equivalent | Latest window divided by prior window. |
| `[Headcount]` | `workers.Headcount` measure | equivalent | Distinct active worker count. |
| `[Headcount at As Of]` | `workers.Headcount at As Of` measure | equivalent | Applies the disconnected quarter-end selection to hire/termination dates. |
| `[Tenure at Exit (yrs)]` FIXED LOD | `workers.Tenure at Exit (yrs)` measure | equivalent | Uses `AVERAGEX` over exited workers and date difference in days. |
| `[Division Avg Salary]` FIXED LOD | `workers.Division Avg Salary` measure | equivalent | Uses `CALCULATE`/`ALLEXCEPT` on division. |
| `[Salary vs Division Avg]` | `workers.Salary vs Division Avg` measure | equivalent | Compares average salary with the division-level average. |
| `[Title Exits (INCLUDE)]` INCLUDE LOD | `workers.Title Exits (INCLUDE)` measure | equivalent | Uses `SUMX` over `VALUES(job_title)`. |
| `[Division Headcount]` FIXED LOD | `workers.Division Headcount` measure | equivalent | Uses `CALCULATE`/`ALLEXCEPT` on division. |
| `[Vol Exits Monthly]` | `workers.Vol Exits Monthly` measure | equivalent | Monthly voluntary-exit count. |
| `[Monthly Vol Exits YoY %]` LOOKUP(-12) | `workers.Monthly Vol Exits YoY %` measure | equivalent | Uses `DATEADD(Calendar[Date], -12, MONTH)` over the continuous month series. |
| `[Trailing 3M Vol Exits]` WINDOW_SUM(-2,0) | `workers.Trailing 3M Vol Exits` measure | equivalent | Uses a three-month `DATESINPERIOD` window. |
| `[Running Vol Exits YTD]` RUNNING_SUM | `workers.Running Vol Exits YTD` measure | equivalent | Uses `DATESYTD`; the year boundary restarts the running total. |
| `[Title Rank]` RANK | `workers.Title Rank` measure | equivalent | Uses `RANKX(ALLSELECTED(job_title))`. |
| `[Overdue Rate]` | `workers.Overdue Rate` measure | equivalent | Denominator includes only Completed and Overdue training rows. |
| `[Division Overdue Rate]` FIXED LOD | `workers.Division Overdue Rate` measure | equivalent | Uses Security training and `ALLEXCEPT` on division/business unit. |
| `[Fiscal Year]` | `workers.Fiscal Year` measure | equivalent | Derived from the selected As Of Quarter End date. |
| `[Fiscal Quarter]` | `workers.Fiscal Quarter` measure | equivalent | Derived from the selected As Of Quarter End date. |
| `[Budget Variance %]` | `workers.Budget Variance %` measure | semantic change | Blending is modeled with the Division dimension and a FY/quarter `Fiscal Period Key`, not Tableau's secondary-source blend. |
| `[user_email]` (Workforce entitlement) | `v_entitlement_expanded[user_email]` | exact | DirectQuery source field used by the RLS role. |
| `[Entitlement OK]` (Pipeline) | `Entitlement` DAX role | semantic change | Replaces the second Tableau data-source filter with the same user-principal RLS rule. |
| `[Past Due Open HC]` | `workers.Past Due Open HC` measure | semantic change | Includes only Open, past-due requests whose opportunity stage is Won. |
| `[Opp Amount]` FIXED LOD | `workers.Opp Amount` measure | equivalent | Opportunity amount is read through the one-to-many relationship. |
| `[Opp Requested HC]` FIXED LOD | `workers.Opp Requested HC` measure | equivalent | Uses `CALCULATE`/`ALLEXCEPT` to total request headcount at opportunity grain. |
| `[Opp Past Due HC]` FIXED LOD | `workers.Opp Past Due HC` measure | equivalent | References the Won-only past-due headcount measure. |
| `[Revenue at Risk (Won contracts)]` | `workers.Revenue at Risk (Won contracts)` measure | equivalent | Iterates qualifying request rows and prorates opportunity amount by request headcount / FIXED requested headcount; all Won accounts are included. |
| `[Selected Accounts]` set | Account-bar cross-filter to Open Requests Detail | semantic change | Power BI selection filters the related request table; there is no persisted Tableau set membership. |
| `[Top N Titles]` set | `TOPN`-based measure and title visual | equivalent | The measure returns values only for the selected Top N titles. |
| KPI Headcount worksheet | Attrition Watch card | equivalent | Native card. |
| KPI Vol Exits Latest worksheet | Attrition Watch card | equivalent | Native card. |
| KPI Vol Exits Prior worksheet | Attrition Watch card | equivalent | Native card. |
| KPI Attrition Ratio worksheet | Attrition Watch card | equivalent | Native card. |
| Monthly Exits Trend worksheet | Attrition Watch line/clustered-column combo | equivalent | Continuous `Calendar.Month Start`; monthly bars and Trailing 3M line. |
| Exits by Division worksheet | Attrition Watch clustered bar | equivalent | Default Power BI visual interaction filters related visuals. |
| Top Titles worksheet | Attrition Watch clustered bar | equivalent | `TOPN` measure plus the Top N Titles slicer replaces the Tableau set coloring/filter. |
| Clearance x Family Heatmap worksheet | Attrition Watch pivot table | semantic change | Rows/columns and counts are retained; heatmap conditional formatting is a Desktop styling step. |
| Exits by State worksheet | Attrition Watch filled map | equivalent | Uses state and voluntary exits; requires map visuals enabled in Desktop. |
| Running YTD Exits worksheet | `Running Vol Exits YTD` measure | manual | The workbook worksheet is a hidden/helper sheet, not a dashboard zone; the measure is in the model but no separate report visual is placed. |
| Revenue at Risk by Account worksheet | Staffing Risk line/clustered-column combo | semantic change | Revenue bars plus Past Due HC line replace Tableau's bar/circle dual axis. |
| Past Due HC by Family x Clearance worksheet | Staffing Risk pivot table | semantic change | Won-only measure is retained; conditional heatmap styling is a Desktop step. |
| Open Requests Detail worksheet | Staffing Risk table with Open and Won categorical filters | equivalent | The account bar cross-filters the related request rows. |
| Overdue Rate by BU worksheet | Training Compliance line/clustered-column combo | semantic change | Overdue and division-rate measures replace the bar plus reference-line encoding. |
| Overdue by Course Category worksheet | Training Compliance clustered column | equivalent | Uses the overall overdue-rate measure by course category. |
| Headcount vs Budget worksheet | Headcount vs Budget combo chart | semantic change | Actual headcount columns and budget line use the FY/quarter key; Tableau bullet/reference-line styling and variance coloring need Desktop refinement. |
| Attrition Watch dashboard | Attrition Watch report page | equivalent | 1600×900 source canvas; RLS replaces View As. |
| Staffing Risk dashboard | Staffing Risk report page | equivalent | 1600×900 source canvas; account selection filters the detail visual. |
| Training Compliance dashboard | Training Compliance report page | equivalent | 1600×900 source canvas. |
| Headcount vs Budget dashboard | Headcount vs Budget report page | equivalent | 1600×900 source canvas; As Of Quarter End slicer is disconnected. |
| Exits by Division filter action | Default cross-filter interactions | equivalent | Power BI cross-filtering is enabled on native visuals; confirm interaction direction in Desktop. |
| job_family highlight action | Power BI visual highlight interaction | manual | Highlight-versus-filter interaction is not generated by the converter and requires Desktop interaction setup. |
| Revenue at Risk by Account set action | Account-bar cross-filter interaction | semantic change | Cross-filters Open Requests Detail through opportunity relationships rather than persisting set membership. |

## Model additions and manual completion

Power BI adds the `Division` calculated dimension, `Calendar`, and `Fiscal
Period` tables, with a calculated FY/quarter key on the imported budget and a
matching key on Calendar. This is the documented semantic change for Tableau
data blending. The output defines DAX roles `Entitlement`,
`Defense Lead`, `Intel Lead`, and `Exec`. The `Entitlement` role filters
`Division[division]` with
`CALCULATETABLE(VALUES(v_entitlement_expanded[division]), ...)`; the hidden
`v_entitlement_expanded` DirectQuery table is disconnected and no bidirectional
security-filter relationship is used. The three static roles filter Division
for Desktop testing. The model does not use the demo app's HMAC token.

Manual completion is limited to external PostgreSQL credential entry in
Power BI Desktop, confirming the generated filled-map and combo-chart visuals
render in the installed Desktop build, setting the `job_family` highlight
interaction, and refining heatmap/bullet-style conditional formatting. Tableau
Desktop/Power BI Desktop rendering was not available in this migration
environment.
