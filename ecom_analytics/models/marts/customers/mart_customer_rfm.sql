{{ config(materialized='table', schema='gold') }}

with snapshot as (

    select
        cast(max(order_date) + interval '1 day' as date) as snapshot_date
    from {{ ref('stg_ecom_sales') }}

),

customer_sales as (

    select
        customer_id,
        max(order_date) as last_order_date,
        count(distinct order_id) as frequency_orders,
        sum(sales) as monetary_sales
    from {{ ref('int_sales_enriched') }}
    group by customer_id

),

rfm_base as (

    select
        cs.customer_id,
        cs.last_order_date,
        cs.frequency_orders,
        cs.monetary_sales,
        s.snapshot_date,
        date_diff('day', cs.last_order_date, s.snapshot_date) as recency_days
    from customer_sales as cs
    cross join snapshot as s

),

rfm_scores as (

    select
        *,
        6 - ntile(5) over (
            order by recency_days asc, customer_id asc
        ) as recency_score,
        ntile(5) over (
            order by frequency_orders asc, customer_id asc
        ) as frequency_score,
        ntile(5) over (
            order by monetary_sales asc, customer_id asc
        ) as monetary_score
    from rfm_base

)

select
    c.customer_id,
    s.snapshot_date,
    r.last_order_date,
    r.recency_days,
    r.frequency_orders,
    r.monetary_sales,
    r.recency_score,
    r.frequency_score,
    r.monetary_score,
    case
        when r.customer_id is null then null
        else r.monetary_score = 5
    end as is_vip,
    case
        when r.customer_id is null then null
        else r.recency_days >= 90
    end as churn_risk_90d,
    case
        when r.customer_id is null then null
        else r.monetary_score = 5 and r.recency_days >= 90
    end as vip_churn_risk,
    case
        when r.customer_id is null then 'no_purchase_history'
        else 'scored'
    end as rfm_status
from {{ ref('stg_customers') }} as c
cross join snapshot as s
left join rfm_scores as r
    on c.customer_id = r.customer_id