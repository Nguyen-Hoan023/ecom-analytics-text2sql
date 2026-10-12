{{ config(materialized='table', schema='gold') }}

with monthly_sales as (

    select
        cast(date_trunc('month', order_date) as date) as sales_month,
        count(*) as sales_line_count,
        count(distinct order_id) as order_count,
        sum(sales) as total_sales,
        sum(profit) as total_profit
    from {{ ref('int_sales_enriched') }}
    group by 1

),

sales_with_prior_year as (

    select
        current_month.*,
        previous_year.total_sales as prior_year_sales
    from monthly_sales as current_month
    left join monthly_sales as previous_year
        on previous_year.sales_month =
            cast(current_month.sales_month - interval '1 year' as date)

)

select
    sales_month,
    sales_line_count,
    order_count,
    total_sales,
    total_profit,
    total_profit / nullif(total_sales, 0) as profit_margin,
    prior_year_sales,
    total_sales / nullif(prior_year_sales, 0) - 1 as sales_yoy_growth_rate
from sales_with_prior_year