"""Number check: do the migrated dashboards show the same numbers as the Tableau workbook?

Three independent sources are compared for the selected year (default 2023):
  1. Tableau extract  - the .hyper inside the .twbx, queried with Tableau's own Hyper engine
  2. Postgres         - the superstore.* tables the new dashboards read from
  3. DAX replica      - the translated measures re-evaluated in pandas (same logic as the TMDL)

Writes part1-tableau-to-powerbi/number_check.md. Exit 1 if anything differs by > 0.01.
"""
import glob
import os
import sys
import tempfile
import zipfile

import pandas as pd
import psycopg2
from tableauhyperapi import Connection, HyperProcess, Telemetry

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
YEAR = int(os.environ.get("SELECT_YEAR", "2023"))
DSN = os.environ.get("DATABASE_URL", "postgresql://superstore:superstore@localhost:5432/superstore")
TWBX = os.path.join(os.path.dirname(ROOT), "course", "tableau-files", "Section 15 - Tableau Sales & Customer Dashboards.twbx")

KPIS = ["CY Sales", "PY Sales", "CY Profit", "CY Quantity", "CY Orders", "CY Customers", "CY Sales per Customer"]


def from_hyper():
    out = {}
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(TWBX) as z:
            z.extractall(tmp)
        hyper = glob.glob(os.path.join(tmp, "**", "*.hyper"), recursive=True)[0]
        with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp, Connection(hp.endpoint, hyper) as c:
            orders = [t for t in c.catalog.get_table_names("Extract") if t.name.unescaped.startswith("Orders")][0]
            products = [t for t in c.catalog.get_table_names("Extract") if t.name.unescaped.startswith("Products")][0]
            q = lambda sql: c.execute_list_query(sql)
            out["CY Sales"] = q(f'SELECT SUM("Sales") FROM {orders} WHERE EXTRACT(year FROM "Order Date") = {YEAR}')[0][0]
            out["PY Sales"] = q(f'SELECT SUM("Sales") FROM {orders} WHERE EXTRACT(year FROM "Order Date") = {YEAR - 1}')[0][0]
            out["CY Profit"] = q(f'SELECT SUM("Profit") FROM {orders} WHERE EXTRACT(year FROM "Order Date") = {YEAR}')[0][0]
            out["CY Quantity"] = q(f'SELECT SUM("Quantity") FROM {orders} WHERE EXTRACT(year FROM "Order Date") = {YEAR}')[0][0]
            out["CY Orders"] = q(f'SELECT COUNT(DISTINCT "Order ID") FROM {orders} WHERE EXTRACT(year FROM "Order Date") = {YEAR}')[0][0]
            out["CY Customers"] = q(f'SELECT COUNT(DISTINCT "Customer ID") FROM {orders} WHERE EXTRACT(year FROM "Order Date") = {YEAR}')[0][0]
            out["CY Sales per Customer"] = out["CY Sales"] / out["CY Customers"]
            rows = q(f'''SELECT p."Sub-Category", SUM(o."Sales") FROM {orders} o
                         JOIN (SELECT DISTINCT "Product ID", "Sub-Category" FROM {products}) p ON p."Product ID" = o."Product ID"
                         WHERE EXTRACT(year FROM o."Order Date") = {YEAR} GROUP BY 1''')
            out["subcat"] = {r[0]: float(r[1]) for r in rows}
    return out


def from_postgres():
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    out = {}
    cur.execute(f"SELECT SUM(sales), SUM(profit), SUM(quantity), COUNT(DISTINCT order_id), COUNT(DISTINCT customer_id) FROM superstore.orders WHERE EXTRACT(year FROM order_date) = {YEAR}")
    s, p, qn, o, cst = cur.fetchone()
    cur.execute(f"SELECT SUM(sales) FROM superstore.orders WHERE EXTRACT(year FROM order_date) = {YEAR - 1}")
    out.update({"CY Sales": float(s), "PY Sales": float(cur.fetchone()[0]), "CY Profit": float(p), "CY Quantity": int(qn),
                "CY Orders": o, "CY Customers": cst, "CY Sales per Customer": float(s) / cst})
    cur.execute(f"SELECT sub_category, SUM(sales) FROM analytics.order_lines WHERE EXTRACT(year FROM order_date) = {YEAR} GROUP BY 1")
    out["subcat"] = {r[0]: float(r[1]) for r in cur.fetchall()}
    conn.close()
    return out


def from_dax_replica():
    """Evaluate the translated measures the way the DAX does: filter Orders[Order Year] = y, then aggregate."""
    o = pd.read_csv(os.path.join(ROOT, "data", "orders.csv"), parse_dates=["Order Date"])
    p = pd.read_csv(os.path.join(ROOT, "data", "products.csv")).drop_duplicates("Product ID")
    o["Order Year"] = o["Order Date"].dt.year                      # calculated column
    cy, py = o[o["Order Year"] == YEAR], o[o["Order Year"] == YEAR - 1]  # CALCULATE(..., Order Year = y)
    out = {"CY Sales": cy["Sales"].sum(), "PY Sales": py["Sales"].sum(), "CY Profit": cy["Profit"].sum(),
           "CY Quantity": int(cy["Quantity"].sum()), "CY Orders": cy["Order ID"].nunique(), "CY Customers": cy["Customer ID"].nunique()}
    out["CY Sales per Customer"] = out["CY Sales"] / out["CY Customers"]  # DIVIDE
    out["subcat"] = cy.merge(p, on="Product ID").groupby("Sub-Category")["Sales"].sum().to_dict()
    return out


def fmt(v):
    return f"{v:,.2f}" if isinstance(v, float) else f"{v:,}"


def main():
    h, pg, dax = from_hyper(), from_postgres(), from_dax_replica()
    bad = 0
    L = [f"# Number check — selected year {YEAR}", "",
         "Same question asked of three independent engines. Tableau's Hyper engine reads the original extract; "
         "Postgres is what the new dashboards query; the DAX replica re-evaluates the translated measures.", "",
         "| Measure | Tableau extract (Hyper) | Postgres | DAX replica | Match |", "|---|---|---|---|---|"]
    for k in KPIS:
        ok = abs(float(h[k]) - float(pg[k])) < 0.01 and abs(float(h[k]) - float(dax[k])) < 0.01
        bad += not ok
        L.append(f"| {k} | {fmt(h[k])} | {fmt(pg[k])} | {fmt(dax[k])} | {'✅' if ok else '❌'} |")
    L += ["", f"## CY Sales by Sub-Category ({YEAR})", "", "| Sub-Category | Tableau extract | Postgres | DAX replica | Match |", "|---|---|---|---|---|"]
    for sc in sorted(h["subcat"]):
        a, b, c = h["subcat"][sc], pg["subcat"].get(sc, 0.0), dax["subcat"].get(sc, 0.0)
        ok = abs(a - b) < 0.01 and abs(a - c) < 0.01
        bad += not ok
        L.append(f"| {sc} | {a:,.2f} | {b:,.2f} | {c:,.2f} | {'✅' if ok else '❌'} |")
    L += ["", f"**Result: {'all numbers match' if not bad else str(bad) + ' mismatches'}** (tolerance 0.01)."]
    text = "\n".join(L) + "\n"
    open(os.path.join(ROOT, "part1-tableau-to-powerbi", "number_check.md"), "w", encoding="utf-8").write(text)
    print(text)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
