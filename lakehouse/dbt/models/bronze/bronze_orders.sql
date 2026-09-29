{{ config(materialized='view') }}

select *
from delta_scan(
    '{{ var("lake_root") }}/lh_bronze.Lakehouse/Tables/orders'
)
