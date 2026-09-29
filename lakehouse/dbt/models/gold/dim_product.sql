select
    product_id,
    category,
    sub_category,
    product_name
from {{ ref('silver_products') }}
