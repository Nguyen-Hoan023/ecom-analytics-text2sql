{{ config(materialized='view', schema='silver') }}

with sales as (

    select *
    from {{ ref('stg_ecom_sales') }}

),

customers as (

    select *
    from {{ ref('stg_customers') }}

),

products as (

    select *
    from {{ ref('stg_products') }}

),

regions as (

    select *
    from {{ ref('stg_regions') }}

)

select
    s.sales_line_id,
    s.order_id,
    s.order_date,
    s.customer_id,
    s.segment,
    s.product_code,
    s.region_code,
    s.quantity,
    s.sales,
    s.discount,
    s.profit,

    c.birth_date,
    c.marital_status,
    c.gender,
    c.annual_income,
    c.education_level,
    c.occupation,
    c.home_owner,

    p.product_name,
    p.category,
    p.subcategory,

    r.city,
    r.state,
    r.country,
    r.country_latitude,
    r.country_longitude,
    r.region_name,
    r.market,

    case
        when s.customer_id is null then 'missing_key'
        when c.customer_id is null then 'unmatched_key'
        else 'matched'
    end as customer_match_status,

    case
        when s.product_code is null then 'missing_key'
        when p.product_code is null then 'unmatched_key'
        else 'matched'
    end as product_match_status,

    case
        when s.region_code is null then 'missing_key'
        when r.region_code is null then 'unmatched_key'
        else 'matched'
    end as region_match_status

from sales as s
left join customers as c
    on s.customer_id = c.customer_id
left join products as p
    on s.product_code = p.product_code
left join regions as r
    on s.region_code = r.region_code