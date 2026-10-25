# Staging models

Staging models are the Silver entry point. They select from the DLT Bronze snapshot and apply source-aligned typing, naming, whitespace cleanup, and safe unknown-value handling. They should remain close to one source table per model.

## Models

| Model | Source | Grain/key contract |
|---|---|---|
| <code>stg_customers</code> | <code>bronze.customer</code> | One row per <code>customer_id</code>; personal names and email are not selected into this analytical model. |
| <code>stg_ecom_sales</code> | <code>bronze.ecom_sales</code> | One row per source sales line; <code>sales_line_id</code> comes from source <code>row_id</code>. |
| <code>stg_products</code> | <code>bronze.product</code> | One row per <code>product_code</code>. |
| <code>stg_regions</code> | <code>bronze.region</code> | One row per <code>region_code</code>. |

## Transaction handling

The sales model keeps <code>sales</code>, <code>profit</code>, and <code>discount</code> numeric, casts order date to a date type, and retains all dimension keys. Amounts keep source units. Discounts are treated as source fractions for banding; do not reinterpret them as absolute currency discounts.

## Tests and edits

YAML files next to each model declare descriptions and generic <code>not_null</code>/<code>unique</code> tests for the primary key. The next layer tests enrichment behavior and join quality.

When changing a cast, column name, or unknown-value convention, update the model YAML, dependent references, semantic catalog if it changes Gold-facing fields, and the relevant contract tests. Validate with:

    uv run --project . python scripts/project.py dbt parse
    uv run --project . python scripts/project.py dbt build --select stg_customers stg_ecom_sales stg_products stg_regions
