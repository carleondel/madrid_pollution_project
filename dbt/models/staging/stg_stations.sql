select
    station_id,
    station_code,
    station_name,
    address,
    station_type_code,
    station_type,
    altitude_m,
    longitude,
    latitude,
    opened_on,
    measures_no2,
    ingested_at
from {{ source('raw', 'stations') }}
where measures_no2
