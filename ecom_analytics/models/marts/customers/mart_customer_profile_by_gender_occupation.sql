{{ config(materialized='table', schema='gold') }}

with customer_attributes as (

    select
        customer_id,
        coalesce(gender, 'Unknown') as gender,
        coalesce(occupation, 'Unknown') as occupation
    from {{ ref('stg_customers') }}

)

select
    gender,
    occupation,
    count(distinct customer_id) as customer_count
from customer_attributes
group by
    gender,
    occupation