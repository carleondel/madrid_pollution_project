select
    observed_at,
    temperature_2m,
    relative_humidity_2m,
    precipitation,
    pressure_msl,
    wind_speed_10m,
    wind_direction_10m,
    latitude,
    longitude,
    source,
    ingested_at
from {{ source('raw', 'weather') }}
