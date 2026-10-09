-- Modeled views for the executive sales dashboard. Built straight from the raw
-- superstore.orders table; no Tableau involved in this part.
CREATE SCHEMA IF NOT EXISTS analytics;

-- One row per order line with the lookups joined in (the "wide" table every view starts from).
CREATE OR REPLACE VIEW analytics.order_lines AS
SELECT o.row_id, o.order_id, o.order_date, o.ship_date, o.ship_mode, o.segment,
       o.customer_id, c.customer_name,
       o.product_id, p.category, p.sub_category, p.product_name,
       l.city, l.state, l.region,
       o.sales, o.quantity, o.discount, o.profit
FROM superstore.orders o
JOIN superstore.customers c ON c.customer_id = o.customer_id
LEFT JOIN LATERAL (SELECT category, sub_category, product_name
                   FROM superstore.products p WHERE p.product_id = o.product_id
                   ORDER BY product_name LIMIT 1) p ON true
LEFT JOIN LATERAL (SELECT city, state, region FROM superstore.location l
                   WHERE l.postal_code = o.postal_code LIMIT 1) l ON true;

-- Monthly sales, profit and margin, by region.
CREATE OR REPLACE VIEW analytics.monthly_sales AS
SELECT date_trunc('month', order_date)::date AS month,
       region,
       SUM(sales)   AS sales,
       SUM(profit)  AS profit,
       SUM(profit) / NULLIF(SUM(sales), 0) AS margin,
       COUNT(DISTINCT order_id) AS orders
FROM analytics.order_lines
GROUP BY 1, 2;

-- Margin by category / sub-category, by year.
CREATE OR REPLACE VIEW analytics.margin_by_category AS
SELECT EXTRACT(year FROM order_date)::int AS year,
       category, sub_category,
       SUM(sales)  AS sales,
       SUM(profit) AS profit,
       SUM(profit) / NULLIF(SUM(sales), 0) AS margin,
       AVG(discount) AS avg_discount
FROM analytics.order_lines
GROUP BY 1, 2, 3;

-- Customers ranked by profit within each year.
CREATE OR REPLACE VIEW analytics.top_customers AS
SELECT *, RANK() OVER (PARTITION BY year ORDER BY profit DESC) AS profit_rank
FROM (
    SELECT EXTRACT(year FROM order_date)::int AS year,
           customer_id, customer_name, segment,
           SUM(sales)  AS sales,
           SUM(profit) AS profit,
           COUNT(DISTINCT order_id) AS orders
    FROM analytics.order_lines
    GROUP BY 1, 2, 3, 4
) yearly;

-- Region x year scorecard used by the KPI tiles.
CREATE OR REPLACE VIEW analytics.region_scorecard AS
SELECT EXTRACT(year FROM order_date)::int AS year,
       region,
       SUM(sales)  AS sales,
       SUM(profit) AS profit,
       SUM(profit) / NULLIF(SUM(sales), 0) AS margin,
       COUNT(DISTINCT order_id) AS orders,
       COUNT(DISTINCT customer_id) AS customers
FROM analytics.order_lines
GROUP BY 1, 2;
