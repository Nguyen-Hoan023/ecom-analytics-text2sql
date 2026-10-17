{{ config(materialized='table', schema='gold') }}

with basket_items as (

    select distinct
        order_id,
        product_code
    from {{ ref('int_sales_enriched') }}
    where order_id is not null
      and product_code is not null

),

valid_orders as (

    select count(distinct order_id) as total_valid_orders
    from basket_items

),

product_order_counts as (

    select
        product_code,
        count(*) as product_order_count
    from basket_items
    group by product_code

),

unordered_pairs as (

    select
        a.order_id,
        a.product_code as product_code_a,
        b.product_code as product_code_b
    from basket_items as a
    inner join basket_items as b
        on a.order_id = b.order_id
       and a.product_code < b.product_code

),

pair_order_counts as (

    select
        product_code_a,
        product_code_b,
        count(*) as pair_order_count
    from unordered_pairs
    group by
        product_code_a,
        product_code_b

),

eligible_pairs as (

    select
        p.product_code_a,
        p.product_code_b,
        p.pair_order_count,
        o.total_valid_orders,
        cast(
            ceil(o.total_valid_orders * {{ var('market_basket_min_support', 0.005) }})
            as bigint
        ) as min_pair_order_count
    from pair_order_counts as p
    cross join valid_orders as o
    where p.pair_order_count >= ceil(
        o.total_valid_orders * {{ var('market_basket_min_support', 0.005) }}
    )

),

directed_rules as (

    select
        product_code_a as antecedent_product_code,
        product_code_b as consequent_product_code,
        pair_order_count,
        total_valid_orders,
        min_pair_order_count
    from eligible_pairs

    union all

    select
        product_code_b as antecedent_product_code,
        product_code_a as consequent_product_code,
        pair_order_count,
        total_valid_orders,
        min_pair_order_count
    from eligible_pairs

),

rule_counts as (

    select
        r.*,
        antecedent.product_order_count as antecedent_order_count,
        consequent.product_order_count as consequent_order_count
    from directed_rules as r
    inner join product_order_counts as antecedent
        on r.antecedent_product_code = antecedent.product_code
    inner join product_order_counts as consequent
        on r.consequent_product_code = consequent.product_code

)

select
    r.antecedent_product_code,
    coalesce(pa.product_name, 'Unknown product') as antecedent_product_name,
    case
        when pa.product_code is null then 'unmatched'
        else 'matched'
    end as antecedent_match_status,

    r.consequent_product_code,
    coalesce(pb.product_name, 'Unknown product') as consequent_product_name,
    case
        when pb.product_code is null then 'unmatched'
        else 'matched'
    end as consequent_match_status,

    r.pair_order_count,
    r.antecedent_order_count,
    r.consequent_order_count,
    r.total_valid_orders,
    r.min_pair_order_count,

    1.0 * r.pair_order_count
        / nullif(r.total_valid_orders, 0) as support,

    1.0 * r.pair_order_count
        / nullif(r.antecedent_order_count, 0) as confidence,

    (1.0 * r.pair_order_count * r.total_valid_orders)
        / nullif(
            r.antecedent_order_count * r.consequent_order_count,
            0
        ) as lift

from rule_counts as r
left join {{ ref('stg_products') }} as pa
    on r.antecedent_product_code = pa.product_code
left join {{ ref('stg_products') }} as pb
    on r.consequent_product_code = pb.product_code