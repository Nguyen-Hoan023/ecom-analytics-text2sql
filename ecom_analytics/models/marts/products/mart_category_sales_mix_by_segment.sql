{{ config(materialized='table', schema='gold') }}

with sales as (

    select
        coalesce(nullif(trim(segment), ''), 'Unknown') as segment,
        coalesce(nullif(trim(category), ''), 'Unknown') as category,
        order_id,
        sales,
        profit
    from {{ ref('int_sales_enriched') }}

),

category_totals as (

    select
        segment,
        category,
        count(*) as sales_line_count,
        count(distinct order_id) as order_count,
        sum(sales) as total_sales,
        sum(profit) as total_profit
    from sales
    group by
        segment,
        category

),

with_segment_totals as (

    select
        *,
        sum(total_sales) over (
            partition by segment
        ) as segment_total_sales
    from category_totals

)

select
    segment,
    category,
    sales_line_count,
    order_count,
    total_sales,
    total_profit,
    segment_total_sales,
    total_sales / nullif(segment_total_sales, 0) as sales_share_of_segment
from with_segment_totals