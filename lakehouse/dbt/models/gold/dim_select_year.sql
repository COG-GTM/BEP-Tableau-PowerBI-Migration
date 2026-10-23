select distinct
    order_year as select_year
from {{ ref('fact_orders') }}
order by select_year
