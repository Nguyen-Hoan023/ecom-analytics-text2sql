{{ config(materialized='view', schema='silver') }}

with source as (

    select
        region_code,
        city,
        state,
        country,
        country_latitude,
        country_longitude,
        region,
        market
    from {{ source('bronze', 'region') }}

)

select
    cast(region_code as varchar) as region_code,
    cast(city as varchar) as city,
    cast(state as varchar) as state,
    cast(country as varchar) as country,
    cast(country_latitude as decimal(10, 6)) as country_latitude,
    cast(country_longitude as decimal(10, 6)) as country_longitude,
    cast(region as varchar) as region_name,
    cast(market as varchar) as market
from source