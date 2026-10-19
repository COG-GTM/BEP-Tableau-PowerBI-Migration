# GDIT Workforce & Pipeline demo data

All records are synthetic. The schemas represent Workday HCM (`workday`), Salesforce (`salesforce`), Oracle LMS (`oracle_lms`), and division access entitlements (`security`). The finance headcount budget remains an Excel extract at `data/finance/fy_headcount_budget.xlsx`.

The generator creates 16,500 worker records, with about 9,500 active on the run date, and assigns divisions using noisy 35/25/25/15 weights. It also produces 30,000 worker events, 2,400 opportunities, 9,000 staffing requests, 40 courses, and 150,000 training completions.

Regenerate the seeded CSV and Parquet files plus the budget workbook:

```bash
cd gdit-workforce-demo
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python data/generate.py
```

Load the generated tables into Supabase (the loader recreates the demo schemas):

```bash
python scripts/load_postgres.py --target supabase
```

Database credentials are read from `~/gdit/.secrets/` or the corresponding `SUPABASE_*` environment variables. Runtime passwords for the demo roles are written to `~/gdit/.secrets/supabase_roles.json`.

Run the feed as `feed_writer`; `--once` emits one visible Defense TS/SCI Software Engineering termination. The default continuous interval is 30 seconds:

```bash
python scripts/live_feed.py --once
python scripts/live_feed.py --interval 30
```

`app_reader` queries the `_v` views with `app.user_email` set for row-level division access. `tableau_reader` can read all demo schemas without write access.
