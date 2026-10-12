{{ config(materialized='table', schema='gold') }}

with sales as (

    select
        coalesce(category, 'Unknown') as category,
        case
            when discount is null then 'Unknown'
            when discount = 0 then '0%'
            when discount <= 0.20 then '(0-20%]'
            when discount <= 0.40 then '(20-40%]'
            when discount <= 0.60 then '(40-60%]'
            else '>60%'
        end as discount_band,
        discount,
        order_id,
        sales,
        profit
    from {{ ref('int_sales_enriched') }}

)

select
    category,
    discount_band,
    count(*) as sales_line_count,
    count(distinct order_id) as orders_with_sales_lines,
    avg(discount) as avg_discount,
    sum(sales) as total_sales,
    sum(profit) as total_profit,
    sum(profit) / nullif(sum(sales), 0) as profit_margin,
    sum(case when profit < 0 then 1 else 0 end) as loss_making_line_count,
    1.0 * sum(case when profit < 0 then 1 else 0 end)
        / nullif(count(*), 0) as loss_making_line_rate
from sales
group by category, discount_band