# "GDIT Workforce & Pipeline" Tableau workbook spec (v1)

Output: gdit-workforce-demo/tableau/GDIT Workforce & Pipeline.twbx (plus the unpacked .twb next to it for diffing).
Built for Tableau Desktop 2026.2. Generated on Linux, then opened, repaired if needed and re-saved in Tableau on Windows.
Every number shown must reconcile with scripts/verify_stories.py (same definitions as below).

## Data sources (3, deliberately mixed)
1. "Workforce (live)": PostgreSQL connector, LIVE (no extract), Supabase connection the loader already uses (host/port/db; sslmode=require), user tableau_reader, password NOT saved in the file.
   Relationships (logical layer, not joins):
   - workday.workers (root) 1..* workday.worker_events on worker_id
   - workday.workers 1..* oracle_lms.training_completions on worker_id; training_completions *..1 oracle_lms.courses on course_code
   - workday.workers *..* security.v_entitlement_expanded on division
2. "Pipeline (live)": PostgreSQL LIVE, same connection.
   - salesforce.opportunities (root) 1..* salesforce.staffing_requests on opp_id
   - salesforce.opportunities *..* security.v_entitlement_expanded on division
3. "FY Budget (extract)": Excel file data/finance/fy_headcount_budget.xlsx -> Hyper extract embedded in the .twbx. Blended to Workforce on Division (+ fiscal year/quarter via calcs below).
New DB object (add to load_postgres.py): view security.v_entitlement_expanded(user_email, division) that expands '*' to all four divisions. GRANT SELECT to tableau_reader.

## Parameters
- [View As] string, list = the 4 entitlement emails, default exec@gdit-demo.example. Stand-in for USERNAME() on Server/Cloud. Put the comment "replace with USERNAME() when published" in the calc.
- [Window Months] int 1..12, default 3.
- [Top N Titles] int 5..25, default 10.
- [As Of Quarter End] date, default = last day of the latest full quarter (2026-09-30 for today's data).

## Calculated fields (Workforce)
- [Entitlement OK] = [user_email (v_entitlement_expanded)] = [View As]  -> data source filter TRUE on both live sources (row-level security, Tableau-side)
- [Is Active] = ISNULL([term_date])
- [Months Ago Term] = DATEDIFF('month', [term_date], DATETRUNC('month', TODAY()))
- [Latest Window] = [Months Ago Term] >= 1 AND [Months Ago Term] <= [Window Months]
- [Prior Window] = [Months Ago Term] > [Window Months] AND [Months Ago Term] <= 2*[Window Months]
- [Voluntary Exit ID] = IF [term_type]='Voluntary' THEN [worker_id] END
- [Vol Exits Latest] = COUNTD(IF [Latest Window] THEN [Voluntary Exit ID] END)
- [Vol Exits Prior] = COUNTD(IF [Prior Window] THEN [Voluntary Exit ID] END)
- [Attrition Ratio] = [Vol Exits Latest] / [Vol Exits Prior]
- [Headcount] = COUNTD(IF [Is Active] THEN [worker_id] END)
- [Headcount at As Of] = COUNTD(IF [hire_date] <= [As Of Quarter End] AND (ISNULL([term_date]) OR [term_date] > [As Of Quarter End]) THEN [worker_id] END)
- LOD [Tenure at Exit (yrs)] = {FIXED [worker_id]: MIN(DATEDIFF('day',[hire_date],[term_date]))} / 365.25
- LOD [Division Avg Salary] = {FIXED [division]: AVG([base_salary])}
- LOD [Salary vs Division Avg] = AVG([base_salary]) / AVG([Division Avg Salary]) - 1
- LOD [Title Exits (INCLUDE)] = {INCLUDE [job_title]: [Vol Exits Latest]}  (used for "max exits by any title" per division)
- LOD [Division Headcount] = {FIXED [division]: COUNTD(IF [Is Active] THEN [worker_id] END)}
- Table calc [Monthly Vol Exits YoY %] = (SUM(vol exits per month) - LOOKUP(..., -12)) / ABS(LOOKUP(..., -12)) on MONTH([term_date])
- Table calc [Trailing 3M Vol Exits] = WINDOW_SUM(COUNTD([Voluntary Exit ID]), -2, 0)
- Table calc [Running Vol Exits YTD] = RUNNING_SUM(COUNTD([Voluntary Exit ID])), restarting every YEAR
- Table calc [Title Rank] = RANK(COUNTD(IF [Latest Window] THEN [Voluntary Exit ID] END))
- Training: [Overdue Rate] = SUM(IF [status]='Overdue' THEN 1 ELSE 0 END) / SUM(IF [status] IN ('Completed','Overdue') THEN 1 ELSE 0 END)
  LOD [Division Overdue Rate] = {FIXED [division], [category]: <same ratio>} (reference line)
- Budget blend: [Fiscal Year] = "FY" + RIGHT(STR(YEAR([As Of Quarter End])),2), [Fiscal Quarter] = "Q" + STR(DATEPART('quarter',[As Of Quarter End])) on Workforce; blend on division, fiscal_year, fiscal_quarter.
  [Budget Variance %] = [Headcount at As Of] / SUM([FY Budget (extract)].[headcount_budget]) - 1

## Calculated fields (Pipeline)
- [Past Due Open HC] = IF [status]='Open' AND [needed_by] < TODAY() THEN [headcount] ELSE 0 END
- LOD [Opp Amount] = {FIXED [opp_id]: MIN([amount])}   (avoids fan-out from the 1..* relationship)
- LOD [Opp Requested HC] = {FIXED [opp_id]: SUM([headcount])}
- LOD [Opp Past Due HC] = {FIXED [opp_id]: SUM([Past Due Open HC])}
- [Revenue at Risk] = SUM( {FIXED [opp_id]: MIN([amount]) * SUM([Past Due Open HC]) / SUM([headcount])} )
- Set [Selected Accounts] on account_name (set action target). Set [Top N Titles] on Workforce job_title by [Vol Exits Latest], top [Top N Titles].

## Worksheets (each name is used by the migration inventory)
Attrition: "KPI Headcount", "KPI Vol Exits Latest", "KPI Vol Exits Prior", "KPI Attrition Ratio", "Monthly Exits Trend" (DUAL AXIS: bars COUNTD vol exits by month + line Trailing 3M, synchronized=false, last 36 months), "Exits by Division" (bar, source of the filter action), "Top Titles" (bars, Title Rank <= Top N, colored by the Top N Titles set), "Clearance x Family Heatmap" (Vol Exits Latest, highlight table), "Exits by State" (filled map, US states), "Running YTD Exits" (line, running sum by year).
Staffing: "Revenue at Risk by Account" (bar + DUAL AXIS circle = Past Due HC; source of a set action -> Selected Accounts), "Past Due HC by Family x Clearance" (highlight table), "Open Requests Detail" (text table filtered by Selected Accounts).
Training: "Overdue Rate by BU" (bar + reference line = Division Overdue Rate), "Overdue by Course Category".
Budget: "Headcount vs Budget" (bullet: bar actual, reference line budget, colored by sign of Budget Variance %).

## Dashboards
1. "Attrition Watch": the 4 KPIs across the top; trend; division bar; titles; heatmap; map. Filter action: Exits by Division -> all other sheets on this dashboard (on select). Highlight action on job_family. Parameter controls for View As, Window Months, Top N Titles.
2. "Staffing Risk": set action from Revenue at Risk by Account -> Selected Accounts; detail table follows it. View As control.
3. "Training Compliance".
4. "Headcount vs Budget": As Of Quarter End control.
Fixed size 1600x900 so the screenshots look the same in the Tableau and Power BI captures.

## Expected values (today's load, View As = exec, Window Months = 3), from ~/gdit/evidence/verify_stories.txt
Defense Vol Exits Latest/Prior = 156/78 (2.00x); Revenue at Risk (Won Army+Navy) = $236,023,502.67; Intelligence Programs Security overdue = 29.4%; Civilian budget variance = -5.9%.
With View As = defense.lead, only Defense rows appear anywhere; with intel.lead, only Intelligence. Data changes when live_feed runs, so record the expected values with a timestamp at validation time instead of hardcoding them.
