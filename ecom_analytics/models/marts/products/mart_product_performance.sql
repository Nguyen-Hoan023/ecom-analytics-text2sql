{{ config(materialized='table', schema='gold') }}

with product_sales as (

    select
        s.product_code,
        coalesce(s.product_name, 'Unknown product') as product_name,
        coalesce(s.category, 'Unknown') as category,
        coalesce(s.subcategory, 'Unknown') as subcategory,
        count(*) as sales_line_count,
        count(distinct s.order_id) as order_count,
        sum(s.quantity) as units_sold,
        sum(s.sales) as total_sales,
        sum(s.profit) as total_profit,
        sum(s.profit) / nullif(sum(s.sales), 0) as profit_margin
    from {{ ref('int_sales_enriched') }} as s
    group by
        s.product_code,
        coalesce(s.product_name, 'Unknown product'),
        coalesce(s.category, 'Unknown'),
        coalesce(s.subcategory, 'Unknown')

),

ranked_products as (

    select
        *,
        row_number() over (
            order by units_sold desc, product_code asc
        ) as units_sold_rank,
        case
            when category is null or category = 'Unknown' then null
            else row_number() over (
                partition by category
                order by total_profit desc, product_code asc
            )
        end as category_profit_rank
    from product_sales

)

select *
from ranked_products