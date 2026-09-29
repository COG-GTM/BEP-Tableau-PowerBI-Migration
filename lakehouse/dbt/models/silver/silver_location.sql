select
    postal_code,
    city,
    state,
    region,
    country_region
from {{ ref('bronze_location') }}
where postal_code is not null
qualify row_number() over (
    partition by postal_code
    order by _row_number
) = 1
