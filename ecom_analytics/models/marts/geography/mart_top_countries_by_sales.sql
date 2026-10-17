{{ config(materialized='table', schema='gold') }}

with country_sales as (

    select
        coalesce(nullif(trim(country), ''), 'Unknown') as country,
        order_id,
        sales,
        profit
    from {{ ref('int_sales_enriched') }}

),

country_totals as (

    select
        country,
        count(*) as sales_line_count,
        count(distinct order_id) as order_count,
        sum(sales) as total_sales,
        sum(profit) as total_profit,
        sum(profit) / nullif(sum(sales), 0) as profit_margin
    from country_sales
    group by country

),

ranked_countries as (

    select
        *,
        row_number() over (
            order by total_sales desc, country
        ) as sales_rank
    from country_totals
    where country <> 'Unknown'

)

select
    country,
    sales_line_count,
    order_count,
    total_sales,
    total_profit,
    profit_margin,
    sales_rank
from ranked_countries
where sales_rank <= 15

union all

select
    country,
    sales_line_count,
    order_count,
    total_sales,
    total_profit,
    profit_margin,
    cast(null as bigint) as sales_rank
from country_totals
where country = 'Unknown'

order by sales_rank nulls last, country