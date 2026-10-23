select
    row_id,
    order_id,
    order_date,
    ship_date,
    ship_mode,
    customer_id,
    segment,
    postal_code,
    product_id,
    sales,
    quantity,
    discount,
    profit,
    year(order_date) as order_year,
    month(order_date) as order_month,
    (
        (
            dayofyear(order_date) - 1
            + isodow(make_date(year(order_date), 1, 1)) - 1
        ) // 7
    ) + 1 as order_week
from {{ ref('silver_orders') }}
