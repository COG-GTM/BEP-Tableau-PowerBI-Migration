select
    product_id,
    category,
    sub_category,
    product_name
from {{ ref('bronze_products') }}
where nullif(trim(product_id), '') is not null
qualify row_number() over (
    partition by product_id
    order by _row_number
) = 1
