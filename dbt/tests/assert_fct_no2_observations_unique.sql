select
    station_id,
    observed_at,
    count(*) as row_count
from {{ ref('fct_no2_observations') }}
group by 1, 2
having count(*) > 1
