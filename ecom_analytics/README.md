# dbt analytics project

This is the dbt project that turns DLT-loaded DuckDB Bronze tables into documented staging models, enriched facts, and business-facing Gold marts.

## Model flow

    source: bronze
      → staging: stg_customers, stg_ecom_sales, stg_products, stg_regions
      → intermediate: int_sales_enriched
      → marts: sales, products, customers, geography

The fact grain remains one row per source sales line, identified by <code>sales_line_id</code>. Dimension joins use left joins so an unmatched product or region does not silently remove revenue or profit.

## Model layers

- **Sources:** Four tables in the DLT <code>bronze</code> dataset.
- **Staging:** Renamed, typed, trimmed, and normalized source columns; source keys remain available for quality analysis.
- **Intermediate:** Adds customer, product, and geographic attributes to transaction lines while preserving unmatched keys as explicit unknown values.
- **Gold:** Twelve marts at business grains such as segment, month, product, country, category mix, customer snapshot, and product pair.

See [models/README.md](models/README.md) for model conventions and links to layer guides.

## Run dbt

From the repository root, use the project wrapper. It resolves the DuckDB path, supplies the dbt project and a temporary profile from <code>profiles.yml.example</code>, and does not overwrite a local dbt profile.

    uv run --project . python scripts/project.py dbt parse
    uv run --project . python scripts/project.py dbt build
    uv run --project . python scripts/project.py dbt show --select mart_sales_by_segment

- <code>dbt parse</code> validates project configuration and the dependency graph; it does not read source tables or require a populated warehouse.
- <code>dbt build</code> builds selected models and runs their configured tests; a populated warehouse is required.
- <code>dbt show</code> previews a model; it also requires the warehouse.

The wrapper owns <code>--project-dir</code> and <code>--profiles-dir</code> so runs use repository-controlled paths. Do not point dbt at an unrelated profile for project acceptance.

## Quality

Model descriptions and column contracts live alongside SQL in YAML files. Generic dbt tests cover nullability/uniqueness and selected relationships; singular SQL tests cover grain, row-count preservation, and aggregate reconciliation.

    uv run --project . python -m text2sql.dbt_contract --manifest ecom_analytics/target/manifest.json

That command checks the parsed dbt Gold graph against the Text-to-SQL semantic catalog. Build the manifest first with the wrapper's <code>dbt parse</code> command.

## More detail

- [Layer map](models/README.md)
- [Staging](models/staging/README.md)
- [Intermediate fact](models/intermediate/README.md)
- [Gold marts](models/marts/README.md)
- [dbt project configuration](dbt_project.yml)
- [Safe profile template](profiles.yml.example)

Never commit a real <code>profiles.yml</code>, warehouse, source extract, or generated dbt <code>target/</code> and <code>logs/</code> directories.
