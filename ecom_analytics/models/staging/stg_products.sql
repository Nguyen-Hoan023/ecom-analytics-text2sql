{{ config(materialized='view', schema='silver') }}

with source as (

    select
        product_code,
        product,
        category,
        subcategory
    from {{ source('bronze', 'product') }}

)

select
    cast(product_code as varchar) as product_code,
    cast(product as varchar) as product_name,
    cast(category as varchar) as category,
    cast(subcategory as varchar) as subcategory
from source