with observations as (

    select * from {{ ref('stg_air_quality') }}

),

stations as (

    select * from {{ ref('stg_stations') }}

),

weather as (

    select * from {{ ref('stg_weather') }}

)

select
    observations.station_id,
    observations.observed_at,
    observations.no2_ug_m3,
    stations.station_name,
    stations.station_type,
    stations.altitude_m,
    stations.longitude as station_longitude,
    stations.latitude as station_latitude,
    weather.temperature_2m,
    weather.relative_humidity_2m,
    weather.precipitation,
    weather.pressure_msl,
    weather.wind_speed_10m,
    weather.wind_direction_10m,
    observations.source_year,
    observations.ingested_at
from observations
inner join stations
    on observations.station_id = stations.station_id
left join weather
    on observations.observed_at = weather.observed_at
