select
    station_id,
    observed_at,
    count(*) as row_count
from {{ ref('int_station_hourly') }}
group by 1, 2
having count(*) > 1
