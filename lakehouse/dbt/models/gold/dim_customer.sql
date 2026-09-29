select
    customer_id,
    customer_name
from {{ ref('silver_customers') }}
