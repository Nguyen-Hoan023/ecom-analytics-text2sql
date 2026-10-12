{{ config(materialized='view', schema='silver') }}

with source as (

    select
        customer_id,
        birth_date,
        marital_status,
        gender,
        annual_income,
        education_level,
        occupation,
        home_owner
    from {{ source('bronze', 'customer') }}

)

select
    cast(customer_id as varchar) as customer_id,
    cast(birth_date as date) as birth_date,
    cast(marital_status as varchar) as marital_status,
    cast(gender as varchar) as gender,
    cast(annual_income as integer) as annual_income,
    cast(education_level as varchar) as education_level,
    cast(occupation as varchar) as occupation,
    cast(home_owner as varchar) as home_owner
from source