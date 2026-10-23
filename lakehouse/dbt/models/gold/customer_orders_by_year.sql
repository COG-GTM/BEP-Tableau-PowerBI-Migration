with customers as (
    select distinct customer_id
    from {{ ref('fact_orders') }}
),
order_counts as (
    select
        customer_id,
        order_year as year,
        count(distinct order_id) as nr_of_orders_per_customers
    from {{ ref('fact_orders') }}
    group by customer_id, order_year
)
select
    customers.customer_id,
    years.select_year as year,
    coalesce(order_counts.nr_of_orders_per_customers, 0) as nr_of_orders_per_customers
from customers
cross join {{ ref('dim_select_year') }} as years
left join order_counts
    on customers.customer_id = order_counts.customer_id
    and years.select_year = order_counts.year
