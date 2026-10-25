# dbt model map

This directory is the transformation graph. SQL defines the transformation; the adjacent YAML records model and column descriptions, tests, and metadata.

## Dependency graph

    sources.yml (DLT Bronze)
      ├── staging/stg_customers
      ├── staging/stg_ecom_sales
      ├── staging/stg_products
      └── staging/stg_regions
               ↓
        intermediate/int_sales_enriched
               ↓
        marts/{sales,products,customers,geography}

The four staging models are built from the four Bronze relations. Most marts depend on <code>int_sales_enriched</code>; customer profiles and RFM also use the customer dimension directly where their grain requires the full customer population.

## Directory guide

| Directory/file | Purpose |
|---|---|
| <code>sources.yml</code> | Names the DLT Bronze dataset and declares source keys/tests. |
| <code>staging/</code> | One source-aligned model per table. See its README for cleaning rules. |
| <code>intermediate/</code> | Shared transaction fact enrichment. See its README for grain and join behavior. |
| <code>marts/</code> | Twelve analytics marts grouped by business domain. See the mart index and domain guides. |

## Modeling rules

1. Preserve source transaction grain through the fact enrichment.
2. Keep source identifiers needed for joins/reconciliation, but do not expose personal fields in Gold.
3. Use left joins for optional dimensions and retain unknown/unmatched facts.
4. Make the output grain explicit in the model description and test it where practical.
5. Define metric meanings in the semantic catalog and keep dbt column names aligned.
6. Add tests where a failure would change a business answer: key uniqueness, row-count preservation, join coverage, and totals.

Run <code>dbt build</code> through <code>scripts/project.py</code> from the repository root. The dbt README documents commands and profile behavior.
