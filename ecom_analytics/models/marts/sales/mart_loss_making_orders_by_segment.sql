{{ config(materialized='table', schema='gold') }}

with order_profit as (

    select
        order_id,
        coalesce(segment, 'Unknown') as segment,
        sum(profit) as order_profit
    from {{ ref('int_sales_enriched') }}
    group by
        order_id,
        coalesce(segment, 'Unknown')

)

select
    segment,
    count(*) as order_count,
    sum(case when order_profit < 0 then 1 else 0 end)
        as loss_making_order_count,
    1.0 * sum(case when order_profit < 0 then 1 else 0 end)
        / nullif(count(*), 0) as loss_making_order_rate
from order_profit
group by segment