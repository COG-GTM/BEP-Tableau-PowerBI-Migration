#!/usr/bin/env bash
# Rebuilds everything in superstore-demo/ from the Tableau workbook. ~3 minutes on a laptop.
set -euo pipefail
cd "$(dirname "$0")"
pip install -q -r requirements.txt
docker compose up -d
until docker exec pg pg_isready -U superstore >/dev/null 2>&1; do sleep 1; done
until curl -sf http://localhost:3000/api/health >/dev/null; do sleep 2; done

python3 scripts/extract_twbx.py "../course/tableau-files/Section 15 - Tableau Sales & Customer Dashboards.twbx"   # data/*.csv + inventory
python3 scripts/build_pbip.py                                                                               # Power BI project
python3 scripts/validate_pbip.py                                                                            # static checks on the PBIP
python3 scripts/load_postgres.py                                                                            # raw tables -> Postgres
docker exec -i pg psql -U superstore -d superstore -v ON_ERROR_STOP=1 < part2-data-to-dashboard/02_views.sql   # analytics views
python3 scripts/metabase_setup.py                                                                           # Metabase dashboards (parts 1 + 2)
python3 scripts/number_check.py                                                                             # Tableau vs Postgres vs DAX replica
python3 scripts/analyst_answers.py                                                                          # part 3 answers + charts
