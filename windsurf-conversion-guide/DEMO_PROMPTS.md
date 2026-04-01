# Demo Prompts — Ready-to-Copy Mega-Prompts

> **Purpose**: Single copy-paste prompts for the Tableau → Power BI conversion demo.
> Instead of pasting 30+ individual prompts from [CONVERSION_OUTLINE.md](CONVERSION_OUTLINE.md),
> use the mega-prompts below to run the full 7-phase pipeline in one shot.

---

## Demo Day Cheat Sheet

> **Start the Streamlit app BEFORE the demo in a background terminal so it's pre-loaded:**
> ```bash
> streamlit run streamlit_app.py --server.headless true --server.port 8501 &
> ```

### 3-Step Demo Flow

| Step | Action | What It Shows |
|------|--------|---------------|
| **1** | Paste the **Windsurf Mega-Prompt** (Section 1 below) into Windsurf | Interactive single-workbook conversion — audience sees each phase execute in real time |
| **2** | Paste the **Devin Batch Prompt** (Section 2 below) into a Devin session | At-scale automation — Devin processes all workbooks, creates a PR with full artifacts |
| **3** | Run `bash scripts/run_full_pipeline.sh` then open the pre-loaded Streamlit app | Validation dashboard — visual proof of conversion accuracy across all dashboards |

---

## 1. Windsurf Single-Workbook Mega-Prompt

Copy the prompt below into Windsurf. Replace the workbook path and output directory to target any of the 4 main dashboards (variants provided after the prompt).

### Sales Dashboard (Default)

```
Run the full Tableau-to-Power BI conversion pipeline on the workbook at:
  projects/sales-dashboard-project/Sales & Customer Dashboards.twbx

Follow the 7-phase conversion workflow in windsurf-conversion-guide/CONVERSION_OUTLINE.md:

Phase 1 — PARSE: Unzip the .twbx, parse the .twb XML, extract all calculated fields 
(name, formula, data type, LOD/table calc/parameter classification), map all data sources 
and joins, and extract dashboard layout metadata.

Phase 2 — CONVERT: Convert every Tableau calculated field to DAX. Use these mappings:
- IF/THEN/ELSE → IF()
- { FIXED [Dim]: AGG() } → CALCULATE() + ALLEXCEPT()
- { INCLUDE [Dim]: AGG() } → CALCULATE() + VALUES()  
- { EXCLUDE [Dim]: AGG() } → CALCULATE() + ALL(dim)
- RUNNING_SUM → SUMX(FILTER(ALL(...)))
- RANK → RANKX()
- WINDOW_MAX/MIN → MAXX/MINX(ALLSELECTED())
- LOOKUP → OFFSET()
- TOTAL → CALCULATE(SUM(), ALL())
- COUNTD → DISTINCTCOUNT()
- Parameters → GENERATESERIES() + SELECTEDVALUE()
Include the original Tableau formula as a comment above each DAX measure.

Phase 3 — DATA MODEL: Create a TMDL model with star schema (fact + dimension tables), 
proper data types, relationships, an auto-generated Date table, and all DAX measures.

Phase 4 — LAYOUT: Map the Tableau dashboard layout to a Power BI page layout JSON. 
Generate a theme.json with colors, fonts, and formatting from the original workbook.

Phase 5 — INTERACTIVITY: Document filter actions, cross-filtering, navigation buttons, 
and highlight actions as a Power BI interaction specification.

Phase 6 — VALIDATE: Write a Python validation script that:
(a) Implements each original Tableau formula in Python
(b) Implements each converted DAX formula in Python  
(c) Runs both against the CSV datasets in this repo
(d) Compares results and reports PASS (exact match), WARN (within 0.001 tolerance), 
    or FAIL (mismatch)
Run the validation and generate a markdown report.

Phase 7 — OUTPUT: Generate all artifacts to conversion-output/sales-dashboard/:
- dax_measures.dax (all DAX measures with Tableau comments)
- model.tmdl (full data model)
- layout.json (dashboard layout specification)
- theme.json (visual theme)
- power_query.pq (Power Query M data loading scripts)
- validation_report.md (test results)

Show me the validation results when done.
```

### HR Dashboard Variant

```
Run the full Tableau-to-Power BI conversion pipeline on the workbook at:
  projects/hr-dashboard-project/HR Dashboard.twbx

Follow the 7-phase conversion workflow in windsurf-conversion-guide/CONVERSION_OUTLINE.md:

Phase 1 — PARSE: Unzip the .twbx, parse the .twb XML, extract all calculated fields 
(name, formula, data type, LOD/table calc/parameter classification), map all data sources 
and joins, and extract dashboard layout metadata.

Phase 2 — CONVERT: Convert every Tableau calculated field to DAX. Use these mappings:
- IF/THEN/ELSE → IF()
- { FIXED [Dim]: AGG() } → CALCULATE() + ALLEXCEPT()
- { INCLUDE [Dim]: AGG() } → CALCULATE() + VALUES()  
- { EXCLUDE [Dim]: AGG() } → CALCULATE() + ALL(dim)
- RUNNING_SUM → SUMX(FILTER(ALL(...)))
- RANK → RANKX()
- WINDOW_MAX/MIN → MAXX/MINX(ALLSELECTED())
- LOOKUP → OFFSET()
- TOTAL → CALCULATE(SUM(), ALL())
- COUNTD → DISTINCTCOUNT()
- Parameters → GENERATESERIES() + SELECTEDVALUE()
Include the original Tableau formula as a comment above each DAX measure.

Phase 3 — DATA MODEL: Create a TMDL model with star schema (fact + dimension tables), 
proper data types, relationships, an auto-generated Date table, and all DAX measures.

Phase 4 — LAYOUT: Map the Tableau dashboard layout to a Power BI page layout JSON. 
Generate a theme.json with colors, fonts, and formatting from the original workbook.

Phase 5 — INTERACTIVITY: Document filter actions, cross-filtering, navigation buttons, 
and highlight actions as a Power BI interaction specification.

Phase 6 — VALIDATE: Write a Python validation script that:
(a) Implements each original Tableau formula in Python
(b) Implements each converted DAX formula in Python  
(c) Runs both against the CSV datasets in this repo
(d) Compares results and reports PASS (exact match), WARN (within 0.001 tolerance), 
    or FAIL (mismatch)
Run the validation and generate a markdown report.

Phase 7 — OUTPUT: Generate all artifacts to conversion-output/hr-dashboard/:
- dax_measures.dax (all DAX measures with Tableau comments)
- model.tmdl (full data model)
- layout.json (dashboard layout specification)
- theme.json (visual theme)
- power_query.pq (Power Query M data loading scripts)
- validation_report.md (test results)

Show me the validation results when done.
```

### CISO Cybersecurity Dashboard Variant

```
Run the full Tableau-to-Power BI conversion pipeline for the CISO Cybersecurity dashboard.

Source data: projects/ciso-cybersecurity-project/vulnerabilities.csv
Conversion guide: windsurf-conversion-guide/CISO_CYBERSECURITY_CONVERSION.md

Follow the 7-phase conversion workflow in windsurf-conversion-guide/CONVERSION_OUTLINE.md:

Phase 1 — PARSE: Parse the CISO dashboard specification from 
CISO_CYBERSECURITY_CONVERSION.md. Extract all calculated fields (Critical Open Count, 
MTTR, Risk Score by BU, Patch SLA Compliance, Aging Buckets), data source schema from 
vulnerabilities.csv, and dashboard layout metadata.

Phase 2 — CONVERT: Convert every Tableau calculated field to DAX. Use these mappings:
- IF/THEN/ELSE → IF()
- { FIXED [Dim]: AGG() } → CALCULATE() + ALLEXCEPT()
- { INCLUDE [Dim]: AGG() } → CALCULATE() + VALUES()  
- { EXCLUDE [Dim]: AGG() } → CALCULATE() + ALL(dim)
- RUNNING_SUM → SUMX(FILTER(ALL(...)))
- RANK → RANKX()
- WINDOW_MAX/MIN → MAXX/MINX(ALLSELECTED())
- LOOKUP → OFFSET()
- TOTAL → CALCULATE(SUM(), ALL())
- COUNTD → DISTINCTCOUNT()
- Parameters → GENERATESERIES() + SELECTEDVALUE()
Include the original Tableau formula as a comment above each DAX measure.

Phase 3 — DATA MODEL: Create a TMDL model with star schema (fact + dimension tables), 
proper data types, relationships, an auto-generated Date table, and all DAX measures.

Phase 4 — LAYOUT: Map the dashboard layout to a Power BI page layout JSON. 
Generate a theme.json with colors, fonts, and formatting.

Phase 5 — INTERACTIVITY: Document filter actions, cross-filtering, navigation buttons, 
and highlight actions as a Power BI interaction specification.

Phase 6 — VALIDATE: Write a Python validation script that:
(a) Implements each original Tableau formula in Python
(b) Implements each converted DAX formula in Python  
(c) Runs both against projects/ciso-cybersecurity-project/vulnerabilities.csv
(d) Compares results and reports PASS (exact match), WARN (within 0.001 tolerance), 
    or FAIL (mismatch)
Run the validation and generate a markdown report.

Phase 7 — OUTPUT: Generate all artifacts to conversion-output/ciso-dashboard/:
- dax_measures.dax (all DAX measures with Tableau comments)
- model.tmdl (full data model)
- layout.json (dashboard layout specification)
- theme.json (visual theme)
- power_query.pq (Power Query M data loading scripts)
- validation_report.md (test results)

Show me the validation results when done.
```

### IT Project Management Dashboard Variant

```
Run the full Tableau-to-Power BI conversion pipeline for the IT Project Management dashboard.

Source data: projects/it-project-mgmt-project/jira_issues.csv
Conversion guide: windsurf-conversion-guide/IT_PROJECT_MGMT_CONVERSION.md

Follow the 7-phase conversion workflow in windsurf-conversion-guide/CONVERSION_OUTLINE.md:

Phase 1 — PARSE: Parse the IT PM dashboard specification from 
IT_PROJECT_MGMT_CONVERSION.md. Extract all calculated fields (Sprint Velocity, 
Burn-down Remaining, Bug Escape Rate, Cycle Time, Story Points by Status), data source 
schema from jira_issues.csv, and dashboard layout metadata.

Phase 2 — CONVERT: Convert every Tableau calculated field to DAX. Use these mappings:
- IF/THEN/ELSE → IF()
- { FIXED [Dim]: AGG() } → CALCULATE() + ALLEXCEPT()
- { INCLUDE [Dim]: AGG() } → CALCULATE() + VALUES()  
- { EXCLUDE [Dim]: AGG() } → CALCULATE() + ALL(dim)
- RUNNING_SUM → SUMX(FILTER(ALL(...)))
- RANK → RANKX()
- WINDOW_MAX/MIN → MAXX/MINX(ALLSELECTED())
- LOOKUP → OFFSET()
- TOTAL → CALCULATE(SUM(), ALL())
- COUNTD → DISTINCTCOUNT()
- Parameters → GENERATESERIES() + SELECTEDVALUE()
Include the original Tableau formula as a comment above each DAX measure.

Phase 3 — DATA MODEL: Create a TMDL model with star schema (fact + dimension tables), 
proper data types, relationships, an auto-generated Date table, and all DAX measures.

Phase 4 — LAYOUT: Map the dashboard layout to a Power BI page layout JSON. 
Generate a theme.json with colors, fonts, and formatting.

Phase 5 — INTERACTIVITY: Document filter actions, cross-filtering, navigation buttons, 
and highlight actions as a Power BI interaction specification.

Phase 6 — VALIDATE: Write a Python validation script that:
(a) Implements each original Tableau formula in Python
(b) Implements each converted DAX formula in Python  
(c) Runs both against projects/it-project-mgmt-project/jira_issues.csv
(d) Compares results and reports PASS (exact match), WARN (within 0.001 tolerance), 
    or FAIL (mismatch)
Run the validation and generate a markdown report.

Phase 7 — OUTPUT: Generate all artifacts to conversion-output/it-pm-dashboard/:
- dax_measures.dax (all DAX measures with Tableau comments)
- model.tmdl (full data model)
- layout.json (dashboard layout specification)
- theme.json (visual theme)
- power_query.pq (Power Query M data loading scripts)
- validation_report.md (test results)

Show me the validation results when done.
```

---

## 2. Devin Batch Prompt

The batch prompt for at-scale automation already exists in
[DEVIN_BATCH_WORKFLOW.md](DEVIN_BATCH_WORKFLOW.md), Section "Sample Devin Session Prompts — Prompt A: Full Batch Conversion" (lines 193-208).

Copy this prompt into a Devin session to process **all** workbooks in the repository at once:

```
Convert all .twbx files in this repository to Power BI DAX and TMDL format.

For each workbook:
1. Parse the .twbx archive and extract the .twb XML
2. Inventory all calculated fields, data sources, and dashboard layouts
3. Convert each Tableau calculated field to an equivalent DAX measure
4. Generate a TMDL data model with proper relationships and a Date table
5. Create a Power BI layout specification (JSON)
6. Write a Python validation script that proves conversion accuracy
7. Run the validation and include the report

Follow the conversion patterns established in CONVERSION_OUTLINE.md.
Output all artifacts under conversion-output/{workbook-name}/.
Create a single PR with all conversions and include a migration tracker.
```

---

## 3. Validation Dashboard

After running conversions, launch the validation dashboard to visualize results:

```bash
# Run the full pipeline (parse, generate datasets, run validation)
bash scripts/run_full_pipeline.sh

# Launch the Streamlit validation dashboard
streamlit run streamlit_app.py --server.headless true --server.port 8501
```

The Streamlit app provides:
- Per-dashboard validation results (PASS / WARN / FAIL)
- Side-by-side Tableau vs. DAX formula comparison
- Interactive formula testing with live data
- Conversion artifact viewer (DAX, TMDL, Power Query, Layout JSON)
