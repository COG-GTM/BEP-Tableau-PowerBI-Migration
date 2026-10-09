"""Create the Metabase content for parts 1 and 2 through the Metabase REST API.

Part 1 (migrated from Tableau): 'Superstore — Sales Dashboard' and 'Superstore — Customer
Dashboard', one card per Tableau worksheet, with a 'Select Year' filter standing in for the
Tableau parameter. Part 2 (built from the raw table): 'Superstore — Executive Sales Dashboard'
on top of the analytics.* views, with a Region filter.

Idempotent: re-running archives the previous collection first.
Env: METABASE_URL (default http://localhost:3000), MB_USER, MB_PASSWORD.
"""
import json
import os
import sys
import time

import requests

MB = os.environ.get("METABASE_URL", "http://localhost:3000")
USER = os.environ.get("MB_USER", "devin@superstore.demo")
PASSWORD = os.environ.get("MB_PASSWORD", "Superstore-Demo-2026")
PG = {"host": "pg", "port": 5432, "dbname": "superstore", "user": "superstore", "password": "superstore",
      "schema-filters-type": "inclusion", "schema-filters-patterns": "superstore,analytics", "ssl": False, "tunnel-enabled": False}
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

s = requests.Session()


def api(method, path, **kw):
    r = s.request(method, MB + "/api" + path, **kw)
    if r.status_code >= 400:
        raise SystemExit(f"{method} {path} -> {r.status_code}: {r.text[:500]}")
    return r.json() if r.text else None


def login():
    props = api("GET", "/session/properties")
    if props.get("setup-token"):
        api("POST", "/setup", json={"token": props["setup-token"],
                                     "user": {"first_name": "Devin", "last_name": "Analyst", "email": USER, "password": PASSWORD, "site_name": "Superstore BI"},
                                     "prefs": {"site_name": "Superstore BI", "allow_tracking": False}})
    tok = api("POST", "/session", json={"username": USER, "password": PASSWORD})["id"]
    s.headers["X-Metabase-Session"] = tok


def ensure_database():
    for db in api("GET", "/database")["data"]:
        if db["name"] == "Superstore (Postgres)":
            return db["id"]
    db = api("POST", "/database", json={"engine": "postgres", "name": "Superstore (Postgres)", "details": PG, "is_full_sync": True})
    api("POST", f"/database/{db['id']}/sync_schema")
    for _ in range(60):
        time.sleep(2)
        tables = [t for t in api("GET", f"/table") if t["db_id"] == db["id"]]
        if any(t["schema"] == "analytics" for t in tables) and any(t["name"] == "orders" for t in tables):
            break
    return db["id"]


def collection(name, desc):
    for c in api("GET", "/collection"):
        if c.get("name") == name and not c.get("archived"):
            api("PUT", f"/collection/{c['id']}", json={"archived": True})
    return api("POST", "/collection", json={"name": name, "description": desc, "color": "#509EE3"})["id"]


# ------------------------------------------------------------------ SQL cards
# Variables: {{year}} -> Tableau 'Select Year' parameter. Metabase renders this as a dashboard filter.
YEAR_TAG = {"year": {"id": "year", "name": "year", "display-name": "Select Year", "type": "number", "default": "2023", "required": True}}
REGION_TAG = {"region": {"id": "region", "name": "region", "display-name": "Region", "type": "text", "required": False}}

P1_CARDS = {
    # name: (display, sql, viz settings, tableau sheet)
    "KPI Sales": ("smartscalar", """
        SELECT make_date(EXTRACT(year FROM order_date)::int, 1, 1) AS year, SUM(sales) AS "Sales"
        FROM superstore.orders WHERE EXTRACT(year FROM order_date) IN ({{year}}-1, {{year}}) GROUP BY 1 ORDER BY 1""",
        {"scalar.field": "Sales", "column_settings": {'["name","Sales"]': {"number_style": "currency", "currency": "USD", "decimals": 0}}}, "KPI Sales"),
    "KPI Profit": ("smartscalar", """
        SELECT make_date(EXTRACT(year FROM order_date)::int, 1, 1) AS year, SUM(profit) AS "Profit"
        FROM superstore.orders WHERE EXTRACT(year FROM order_date) IN ({{year}}-1, {{year}}) GROUP BY 1 ORDER BY 1""",
        {"scalar.field": "Profit", "column_settings": {'["name","Profit"]': {"number_style": "currency", "currency": "USD", "decimals": 0}}}, "KPI Profit"),
    "KPI Quantity": ("smartscalar", """
        SELECT make_date(EXTRACT(year FROM order_date)::int, 1, 1) AS year, SUM(quantity) AS "Quantity"
        FROM superstore.orders WHERE EXTRACT(year FROM order_date) IN ({{year}}-1, {{year}}) GROUP BY 1 ORDER BY 1""",
        {"scalar.field": "Quantity"}, "KPI Quantity"),
    "Weekly Trends": ("line", """
        SELECT date_trunc('week', order_date + 1)::date - 1 AS week, SUM(sales) AS "Sales", SUM(profit) AS "Profit"
        FROM superstore.orders WHERE EXTRACT(year FROM order_date) = {{year}} GROUP BY 1 ORDER BY 1""",
        {"graph.dimensions": ["week"], "graph.metrics": ["Sales", "Profit"], "graph.x_axis.title_text": "Week of Order Date"}, "Weekly Trends"),
    "Subcategory Comparison": ("bar", """
        WITH p AS (SELECT DISTINCT product_id, sub_category FROM superstore.products)
        SELECT p.sub_category AS "Sub-Category",
               SUM(CASE WHEN EXTRACT(year FROM o.order_date) = {{year}}   THEN sales END) AS "CY Sales",
               SUM(CASE WHEN EXTRACT(year FROM o.order_date) = {{year}}-1 THEN sales END) AS "PY Sales"
        FROM superstore.orders o JOIN p ON p.product_id = o.product_id
        GROUP BY 1 ORDER BY 2 DESC""",
        {"graph.dimensions": ["Sub-Category"], "graph.metrics": ["CY Sales", "PY Sales"], "graph.y_axis.title_text": "Sales"}, "Subcategory Comparison"),
    "Subcategory KPI flags": ("table", """
        WITH p AS (SELECT DISTINCT product_id, sub_category FROM superstore.products),
        s AS (SELECT p.sub_category,
                     SUM(CASE WHEN EXTRACT(year FROM order_date) = {{year}}   THEN sales END) AS cy_sales,
                     SUM(CASE WHEN EXTRACT(year FROM order_date) = {{year}}-1 THEN sales END) AS py_sales,
                     SUM(CASE WHEN EXTRACT(year FROM order_date) = {{year}}   THEN profit END) AS cy_profit
              FROM superstore.orders o JOIN p ON p.product_id = o.product_id GROUP BY 1)
        SELECT sub_category AS "Sub-Category", round(cy_profit) AS "CY Profit",
               CASE WHEN cy_sales > AVG(cy_sales) OVER () THEN 'Above' ELSE 'Below' END AS "KPI Sales Avg",
               CASE WHEN cy_sales < py_sales THEN '⬤' ELSE '' END AS "KPI CY Less PY"
        FROM s ORDER BY cy_sales DESC""", {}, "Legend KPI / Legend Subcategory"),
    "KPI Customers": ("smartscalar", """
        SELECT make_date(EXTRACT(year FROM order_date)::int, 1, 1) AS year, COUNT(DISTINCT customer_id) AS "Customers"
        FROM superstore.orders WHERE EXTRACT(year FROM order_date) IN ({{year}}-1, {{year}}) GROUP BY 1 ORDER BY 1""",
        {"scalar.field": "Customers"}, "KPI Customers"),
    "KPI Orders": ("smartscalar", """
        SELECT make_date(EXTRACT(year FROM order_date)::int, 1, 1) AS year, COUNT(DISTINCT order_id) AS "Orders"
        FROM superstore.orders WHERE EXTRACT(year FROM order_date) IN ({{year}}-1, {{year}}) GROUP BY 1 ORDER BY 1""",
        {"scalar.field": "Orders"}, "KPI Orders"),
    "KPI Sales per Customer": ("smartscalar", """
        SELECT make_date(EXTRACT(year FROM order_date)::int, 1, 1) AS year, SUM(sales) / COUNT(DISTINCT customer_id) AS "Sales per Customer"
        FROM superstore.orders WHERE EXTRACT(year FROM order_date) IN ({{year}}-1, {{year}}) GROUP BY 1 ORDER BY 1""",
        {"scalar.field": "Sales per Customer", "column_settings": {'["name","Sales per Customer"]': {"number_style": "currency", "currency": "USD", "decimals": 0}}}, "KPI Sales Per Customers"),
    "Customer Distribution": ("bar", """
        WITH per_customer AS (SELECT customer_id, COUNT(DISTINCT order_id) AS orders
                              FROM superstore.orders WHERE EXTRACT(year FROM order_date) = {{year}} GROUP BY 1)
        SELECT orders AS "Orders per Customer", COUNT(*) AS "Customers" FROM per_customer GROUP BY 1 ORDER BY 1""",
        {"graph.dimensions": ["Orders per Customer"], "graph.metrics": ["Customers"]}, "Customer Distribution"),
    "Top Customers": ("table", """
        SELECT RANK() OVER (ORDER BY SUM(o.sales) DESC) AS "#", c.customer_name AS "Customer Name",
               round(SUM(o.sales)) AS "Sales", round(SUM(o.profit)) AS "Profit", COUNT(DISTINCT o.order_id) AS "Orders",
               MAX(o.order_date) AS "Last Order"
        FROM superstore.orders o JOIN superstore.customers c ON c.customer_id = o.customer_id
        WHERE EXTRACT(year FROM o.order_date) = {{year}} GROUP BY c.customer_name ORDER BY 1 LIMIT 10""", {}, "Top Customers"),
}

P2_CARDS = {
    "Sales (selected region)": ("scalar", "SELECT SUM(sales) AS \"Sales\" FROM analytics.region_scorecard WHERE year = 2023 [[AND region = {{region}}]]",
                                {"column_settings": {'["name","Sales"]': {"number_style": "currency", "currency": "USD", "decimals": 0}}}),
    "Profit margin": ("scalar", "SELECT SUM(profit) / SUM(sales) AS \"Margin\" FROM analytics.region_scorecard WHERE year = 2023 [[AND region = {{region}}]]",
                      {"column_settings": {'["name","Margin"]': {"number_style": "percent", "decimals": 1}}}),
    "Orders": ("scalar", "SELECT SUM(orders) AS \"Orders\" FROM analytics.region_scorecard WHERE year = 2023 [[AND region = {{region}}]]", {}),
    "Monthly sales by region": ("area", "SELECT month, region, sales FROM analytics.monthly_sales WHERE 1=1 [[AND region = {{region}}]] ORDER BY 1",
                                {"graph.dimensions": ["month", "region"], "graph.metrics": ["sales"], "stackable.stack_type": "stacked"}),
    "Margin by sub-category (2023)": ("bar", "SELECT sub_category, category, margin, sales FROM analytics.margin_by_category WHERE year = 2023 ORDER BY margin",
                                      {"graph.dimensions": ["sub_category"], "graph.metrics": ["margin"], "graph.y_axis.title_text": "Profit margin"}),
    "Top 10 customers by profit (2023)": ("table", "SELECT profit_rank AS \"#\", customer_name, segment, round(sales) AS sales, round(profit) AS profit, orders FROM analytics.top_customers WHERE year = 2023 AND profit_rank <= 10 ORDER BY 1", {}),
    "Region scorecard (2023)": ("table", "SELECT region, round(sales) AS sales, round(profit) AS profit, round(margin*100,1) AS margin_pct, orders, customers FROM analytics.region_scorecard WHERE year = 2023 [[AND region = {{region}}]] ORDER BY sales DESC", {}),
}


def make_card(db_id, coll_id, name, display, sql, viz, tags, desc=""):
    card = api("POST", "/card", json={
        "name": name, "display": display, "description": desc, "collection_id": coll_id,
        "dataset_query": {"type": "native", "database": db_id,
                          "native": {"query": " ".join(sql.split()), "template-tags": {k: v for k, v in tags.items() if "{{" + k + "}}" in sql}}},
        "visualization_settings": viz})
    card["_tags"] = [k for k in tags if "{{" + k + "}}" in sql]
    return card


def make_dashboard(coll_id, name, desc, layout, param, cards, param_type):
    """layout: list of (card_name, col, row, w, h)."""
    dash = api("POST", "/dashboard", json={"name": name, "description": desc, "collection_id": coll_id,
                                            "parameters": [param]})
    dashcards = []
    for i, (cname, col, row, w, h) in enumerate(layout):
        card = cards[cname]
        tag_name = param["slug"]
        has_tag = tag_name in card["_tags"]
        dashcards.append({"id": -(i + 1), "card_id": card["id"], "col": col, "row": row, "size_x": w, "size_y": h,
                          "parameter_mappings": ([{"parameter_id": param["id"], "card_id": card["id"],
                                                   "target": ["variable", ["template-tag", tag_name]]}] if has_tag else [])})
    api("PUT", f"/dashboard/{dash['id']}", json={"dashcards": dashcards, "parameters": [param]})
    return dash["id"]


def main():
    login()
    db_id = ensure_database()
    # ---------------- Part 1
    coll1 = collection("Part 1 — Migrated from Tableau", "Sales & Customer Dashboards (Dynamic).twbx, rebuilt sheet by sheet.")
    cards1 = {}
    for name, (display, sql, viz, sheet) in P1_CARDS.items():
        cards1[name] = make_card(db_id, coll1, name, display, sql, viz, YEAR_TAG, f"Migrated from Tableau worksheet '{sheet}'.")
    year_param = {"id": "year", "slug": "year", "name": "Select Year", "type": "number/=", "sectionId": "number", "default": [2023]}
    sales_id = make_dashboard(coll1, "Superstore — Sales Dashboard", "Migrated from the Tableau 'Sales Dashboard'.",
                              [("KPI Sales", 0, 0, 6, 3), ("KPI Profit", 6, 0, 6, 3), ("KPI Quantity", 12, 0, 6, 3),
                               ("Weekly Trends", 0, 3, 18, 5), ("Subcategory Comparison", 0, 8, 12, 6), ("Subcategory KPI flags", 12, 8, 6, 6)],
                              year_param, cards1, "number")
    cust_id = make_dashboard(coll1, "Superstore — Customer Dashboard", "Migrated from the Tableau 'Customer Dashboard'.",
                             [("KPI Customers", 0, 0, 6, 3), ("KPI Orders", 6, 0, 6, 3), ("KPI Sales per Customer", 12, 0, 6, 3),
                              ("Customer Distribution", 0, 3, 18, 5), ("Top Customers", 0, 8, 18, 6)],
                             year_param, cards1, "number")
    # ---------------- Part 2
    coll2 = collection("Part 2 — Built from the raw table", "Executive sales dashboard on analytics.* views (no Tableau involved).")
    cards2 = {}
    for name, (display, sql, viz) in P2_CARDS.items():
        cards2[name] = make_card(db_id, coll2, name, display, sql, viz, REGION_TAG, "Built from analytics views in part2-data-to-dashboard/02_views.sql.")
    region_param = {"id": "region", "slug": "region", "name": "Region", "type": "string/=", "sectionId": "string"}
    exec_id = make_dashboard(coll2, "Superstore — Executive Sales Dashboard", "Built directly from superstore.orders via analytics views.",
                             [("Sales (selected region)", 0, 0, 6, 3), ("Profit margin", 6, 0, 6, 3), ("Orders", 12, 0, 6, 3),
                              ("Monthly sales by region", 0, 3, 18, 5), ("Margin by sub-category (2023)", 0, 8, 9, 6),
                              ("Top 10 customers by profit (2023)", 9, 8, 9, 6), ("Region scorecard (2023)", 0, 14, 18, 4)],
                             region_param, cards2, "string")
    out = {"metabase_url": MB, "sales_dashboard": f"{MB}/dashboard/{sales_id}", "customer_dashboard": f"{MB}/dashboard/{cust_id}",
           "executive_dashboard": f"{MB}/dashboard/{exec_id}"}
    json.dump(out, open(os.path.join(ROOT, "part2-data-to-dashboard", "metabase_links.json"), "w"), indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
