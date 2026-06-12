select
    station_id,
    station_name,
    date_trunc('day', observed_at) as observed_date,
    count(*) as observed_hours,
    avg(no2_ug_m3) as avg_no2_ug_m3,
    min(no2_ug_m3) as min_no2_ug_m3,
    max(no2_ug_m3) as max_no2_ug_m3
from {{ ref('fct_no2_observations') }}
group by 1, 2, 3
