{{ config(materialized='table', schema='gold') }}

with customers as (

    select customer_id
    from {{ ref('stg_customers') }}

),

sales as (

    select
        customer_id,
        sales_line_id,
        region_code,
        region_match_status,
        sales,
        profit
    from {{ ref('int_sales_enriched') }}

),

customer_metrics as (

    select
        c.customer_id,

        count(s.sales_line_id) as sales_line_count,

        count(distinct case
            when s.region_match_status = 'matched'
                then s.region_code
        end) as matched_region_count,

        sum(case
            when s.sales_line_id is not null
                and s.region_match_status <> 'matched'
                then 1
            else 0
        end) as orphan_region_sales_line_count,

        coalesce(sum(s.sales), 0) as total_sales,
        coalesce(sum(s.profit), 0) as total_profit,

        coalesce(sum(case
            when s.sales_line_id is not null
                and s.region_match_status <> 'matched'
                then s.sales
            else 0
        end), 0) as orphan_region_sales,

        coalesce(sum(case
            when s.sales_line_id is not null
                and s.region_match_status <> 'matched'
                then s.profit
            else 0
        end), 0) as orphan_region_profit

    from customers as c
    left join sales as s
        on c.customer_id = s.customer_id
    group by c.customer_id

)

select
    customer_id,
    sales_line_count,
    matched_region_count,
    matched_region_count > 1 as is_multi_region_customer,
    orphan_region_sales_line_count,
    orphan_region_sales_line_count > 0 as has_orphan_region_activity,
    total_sales,
    total_profit,
    orphan_region_sales,
    orphan_region_profit
from customer_metrics