with source_sales as (

    select count(*) as row_count
    from {{ ref('stg_ecom_sales') }}

),

enriched_sales as (

    select count(*) as row_count
    from {{ ref('int_sales_enriched') }}

)

select
    source_sales.row_count as source_rows,
    enriched_sales.row_count as enriched_rows
from source_sales
cross join enriched_sales
where source_sales.row_count <> enriched_sales.row_count