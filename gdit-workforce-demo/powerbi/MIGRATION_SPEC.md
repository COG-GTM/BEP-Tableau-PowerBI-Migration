# GDIT workbook -> Power BI migration spec (v1)

Tooling: reuse tableau2pbip from PR #12 (branch devin/1790678582-tableau-to-pbip, open, author robertbromley-cog). Do not fork or copy it. The GDIT migration branch is cut from that branch, so it inherits the converter. Extend the converter there only where the GDIT workbook needs features it lacks, and keep those changes generic (no GDIT names in tableau2pbip/).
Output: gdit-workforce-demo/powerbi/GDIT Workforce & Pipeline.pbip (+ .SemanticModel TMDL, .Report PBIR), plus MIGRATION_REPORT.md.

## Mapping decisions
- Live PostgreSQL datasources -> DirectQuery tables via M `PostgreSQL.Database(Host, "postgres")`. Host is an M parameter, credentials are not stored. Same pooler user convention (tableau_reader.<ref>). DirectQuery is deliberate: it keeps the "live" semantics and makes freshness visible.
- Hyper extract of the Excel budget -> Import table from the same Excel file (path is an M parameter). It stays explicitly "extract/import" so the report shows mixed storage modes.
- Tableau relationships -> model relationships with the same cardinality. The workers <-> v_entitlement_expanded many-to-many becomes RLS (below), not a model relationship.
- Data blending (Workforce <-> Budget on division + FY/quarter) -> a Division dimension table plus relationships, with a calculated FY/quarter key. Document this as a semantic change.
- Parameters: [Window Months], [Top N Titles] -> numeric-range what-if parameter tables. [As Of Quarter End] -> disconnected date table + SELECTEDVALUE. [View As] -> NOT migrated as a parameter. It becomes Power BI RLS roles.
- RLS: keep `v_entitlement_expanded` as a hidden, disconnected DirectQuery table and define an "Entitlement" role on `Division` with `Division[division] IN CALCULATETABLE(VALUES(v_entitlement_expanded[division]), v_entitlement_expanded[user_email] = USERPRINCIPALNAME())`. Do not use a bidirectional security-filter relationship. Also add static test roles "Defense Lead" / "Intel Lead" / "Exec" with fixed Division filters so "View as role" in Desktop demonstrates the model without a tenant.
- LOD FIXED -> CALCULATE(..., ALLEXCEPT/REMOVEFILTERS) or SUMX over VALUES(key). INCLUDE -> SUMX/MAXX over VALUES(job_title). Table calcs: LOOKUP -12 -> DATEADD on a date table; WINDOW_SUM(-2,0) -> DATESINPERIOD 3 months; RUNNING_SUM by year -> DATESYTD; RANK -> RANKX(ALLSELECTED(job_title)).
- Sets / set actions -> Top N: TOPN measure + visual-level filter. "Selected Accounts" set action -> cross-filter interaction from the account bar to the detail table. Filter action -> default cross-filter; highlight action -> cross-highlight.
- Dual axis -> line-and-clustered-column combo visual. Filled map -> filled map (or shape map if filled map is disabled; note this). Bullet -> clustered bar + target line (or a Deneb spec if the layout engine already supports it).
- Pages mirror the 4 dashboards, canvas 1600x900, same titles.
Every Tableau object gets a row in MIGRATION_REPORT.md: source object, Power BI target, status (exact / equivalent / semantic change / manual), and a note.

## Validation
1. Static: the TMDL validator from PR #12 (validate_tmdl.ps1, Windows) plus the PBIR schema validation in tableau2pbip/schema_validation.py.
2. Numeric parity: a script evaluates the generated DAX measures through the same SQL/pandas path as expected_values.py and compares them to expected_values_latest.json. Exact match for counts and money (to the cent) and for percentages to 0.1pt.
3. Rendered: Windows child opens the .pbip in Power BI Desktop, connects to Supabase, and screenshots each page, including View as role = Defense Lead / Intel Lead. In Desktop, DAX query view runs the KPI measures and the results are compared with expected_values.
