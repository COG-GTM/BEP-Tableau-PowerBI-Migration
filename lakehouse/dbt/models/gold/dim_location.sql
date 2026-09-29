select
    postal_code,
    city,
    state,
    region,
    country_region
from {{ ref('silver_location') }}
