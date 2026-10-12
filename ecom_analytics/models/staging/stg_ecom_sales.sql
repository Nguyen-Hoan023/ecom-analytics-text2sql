{{ config(materialized='view', schema='silver') }}

with source as (

    select
        row_id,
        order_id,
        order_date,
        customer_id,
        segment,
        region_code,
        product_code,
        quantity,
        sales,
        discount,
        profit
    from {{ source('bronze', 'ecom_sales') }}

)

select
    cast(row_id as integer) as sales_line_id,
    cast(order_id as varchar) as order_id,
    cast(order_date as date) as order_date,
    cast(customer_id as varchar) as customer_id,
    cast(segment as varchar) as segment,
    cast(region_code as varchar) as region_code,
    cast(product_code as varchar) as product_code,
    cast(quantity as integer) as quantity,
    cast(sales as decimal(10, 2)) as sales,
    cast(discount as decimal(10, 2)) as discount,
    cast(profit as decimal(10, 2)) as profit
from source