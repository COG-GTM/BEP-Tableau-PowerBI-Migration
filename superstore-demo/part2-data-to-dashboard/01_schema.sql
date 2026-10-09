-- Raw Superstore tables, loaded 1:1 from the Tableau extract (data/*.csv).
DROP SCHEMA IF EXISTS superstore CASCADE;
CREATE SCHEMA superstore;

CREATE TABLE superstore.customers (
    customer_id   text PRIMARY KEY,
    customer_name text NOT NULL
);

-- Superstore quirk: 32 product IDs map to two product names, so product_id is not unique.
CREATE TABLE superstore.products (
    product_id   text NOT NULL,
    category     text NOT NULL,
    sub_category text NOT NULL,
    product_name text NOT NULL
);

-- Superstore quirk: Burlington, VT has no postal code and one code appears twice, so no primary key.
CREATE TABLE superstore.location (
    postal_code    integer,
    city           text NOT NULL,
    state          text NOT NULL,
    region         text NOT NULL,
    country_region text NOT NULL
);

CREATE TABLE superstore.orders (
    row_id      integer PRIMARY KEY,
    order_id    text NOT NULL,
    order_date  date NOT NULL,
    ship_date   date NOT NULL,
    ship_mode   text NOT NULL,
    customer_id text NOT NULL REFERENCES superstore.customers (customer_id),
    segment     text NOT NULL,
    postal_code integer,
    product_id  text NOT NULL,
    sales       numeric(12, 4) NOT NULL,
    quantity    integer NOT NULL,
    discount    numeric(5, 2) NOT NULL,
    profit      numeric(12, 4) NOT NULL
);

CREATE INDEX ON superstore.orders (order_date);
CREATE INDEX ON superstore.orders (customer_id);
CREATE INDEX ON superstore.orders (product_id);
CREATE INDEX ON superstore.products (product_id);
CREATE INDEX ON superstore.location (postal_code);
