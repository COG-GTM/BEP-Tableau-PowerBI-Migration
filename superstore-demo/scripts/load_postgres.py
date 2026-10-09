"""Load the CSVs extracted from the Tableau workbook into Postgres.

Usage: DATABASE_URL=postgresql://superstore:superstore@localhost:5432/superstore \
       python scripts/load_postgres.py
"""
import os

import psycopg2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DSN = os.environ.get("DATABASE_URL", "postgresql://superstore:superstore@localhost:5432/superstore")

TABLES = ["customers", "products", "location", "orders"]  # parents first (FKs)


def main():
    conn = psycopg2.connect(DSN)
    conn.autocommit = False
    cur = conn.cursor()
    with open(os.path.join(ROOT, "part2-data-to-dashboard", "01_schema.sql")) as fh:
        cur.execute(fh.read())
    for t in TABLES:
        with open(os.path.join(ROOT, "data", f"{t}.csv"), encoding="utf-8") as fh:
            cur.copy_expert(f"COPY superstore.{t} FROM STDIN WITH (FORMAT csv, HEADER true)", fh)
        cur.execute(f"SELECT COUNT(*) FROM superstore.{t}")
        print(f"superstore.{t}: {cur.fetchone()[0]:,} rows")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
