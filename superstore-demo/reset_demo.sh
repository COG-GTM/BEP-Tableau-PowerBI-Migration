#!/usr/bin/env bash
# Puts superstore-demo/ back to its empty state so run_demo.sh (or the steps inside it) can be
# shown running from scratch: drops the Postgres + Metabase containers and their data, and deletes
# everything the scripts generate. The Tableau workbook and the hand-written SQL are left alone.
set -euo pipefail
cd "$(dirname "$0")"
docker compose down -v --remove-orphans
rm -rf data part1-tableau-to-powerbi part3-data-analyst/*.png part3-data-analyst/answers.md part2-data-to-dashboard/metabase_links.json
echo "empty state: $(find . -type f -not -path './scripts/*' | wc -l) files left (scripts/, SQL, compose, README)"
