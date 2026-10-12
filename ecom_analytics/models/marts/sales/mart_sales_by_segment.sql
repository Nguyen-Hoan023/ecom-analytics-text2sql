{{ config(materialized='table', schema='gold') }}

with sales as (

    select
        coalesce(segment, 'Unknown') as segment,
        order_id,
        sales,
        profit
    from {{ ref('int_sales_enriched') }}

)

select
    segment,
    count(*) as sales_line_count,
    count(distinct order_id) as order_count,
    sum(sales) as total_sales,
    sum(profit) as total_profit,
    sum(profit) / nullif(sum(sales), 0) as profit_margin
from sales
group by segment