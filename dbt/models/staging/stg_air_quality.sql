with source as (

    select * from {{ source('raw', 'air_quality') }}

),

renamed as (

    select
        station_id,
        observed_at,
        no2_ug_m3,
        source_year,
        source_file,
        ingested_at
    from source
    where validity = 'V'

)

select * from renamed
