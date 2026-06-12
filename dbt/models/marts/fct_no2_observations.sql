select
    station_id,
    observed_at,
    no2_ug_m3,
    station_name,
    station_type,
    altitude_m,
    station_longitude,
    station_latitude,
    source_year
from {{ ref('int_station_hourly') }}
