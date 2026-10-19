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

By default the loader reuses role passwords already in `~/gdit/.secrets/supabase_roles.json` and the signing key already in Supabase (falling back to `~/gdit/.secrets/app_signing_key`). Pass `--rotate-passwords` only when intentionally changing role passwords and the app signing key.

Database credentials are read from `~/gdit/.secrets/` or the corresponding `SUPABASE_*` environment variables. Runtime passwords for the demo roles are written to `~/gdit/.secrets/supabase_roles.json`.

Run the feed as `feed_writer`; `--once` emits one visible Defense TS/SCI Software Engineering termination. The default continuous interval is 30 seconds:

```bash
python scripts/live_feed.py --once
python scripts/live_feed.py --interval 30
```

`app_reader` queries the `_v` views with a signed `app.user_token`; create one with `python scripts/sign_identity.py --email defense.lead@gdit-demo.example`. Unsigned or expired identities are denied by default. `tableau_reader` intentionally bypasses database RLS for the Tableau workbook's separate View As filter.

Export the current Tableau ground truth with `python tableau/expected_values.py`. After a fresh seeded reload, run `python tableau/expected_values.py --assert-seed` to check the fixed story targets.

## Alternate web dashboard

Install the additional web dependencies with `pip install -r requirements.txt`. The FastAPI app uses Jinja, vanilla JavaScript, and Vega-Lite:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Set `APP_DEMO_PASSWORD` and `SESSION_SECRET` in the process environment; startup fails if either is unset or if `SESSION_SECRET` is shorter than 32 characters. Set `APP_COOKIE_SECURE=0` only for local HTTP testing; HTTPS deployments keep secure cookies enabled. Database connections use only the `app_reader` role credentials in `~/gdit/.secrets/supabase_roles.json`. The app signs a five-minute database identity token with the cached key in `~/gdit/.secrets/app_signing_key`; it does not use a client-supplied division or audit identity. The session cookie has a 15-minute idle timeout.

Set the demo password and session secret in `~/gdit/.secrets/gdit_alt_dashboard.env` and source it before running Uvicorn. Never place these values in the repository.

This worktree has no local virtual environment; use `~/repos/BEP-Tableau-PowerBI-Migration/gdit-workforce-demo/.venv` for app tests and generator commands.
