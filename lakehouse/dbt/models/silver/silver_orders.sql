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
    profit
from {{ ref('bronze_orders') }}
