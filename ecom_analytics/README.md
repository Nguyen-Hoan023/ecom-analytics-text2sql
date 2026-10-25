# E-Commerce Analytics dbt project

This dbt project transforms the DLT-loaded DuckDB Bronze tables into staging,
intermediate, and Gold analytics models.

## Model layers

- **Sources:** Four Bronze tables loaded from SQL Server by DLT.
- **Staging:** `stg_customers`, `stg_ecom_sales`, `stg_products`, and `stg_regions`.
- **Intermediate:** `int_sales_enriched`, which enriches sales with customer,
  product, and region attributes while retaining unmatched dimension keys.
- **Gold marts:** Business-facing models for segment profitability, discount
  analysis, loss-making orders, RFM, monthly performance, product performance,
  geography, and category mix.

## Run dbt

Run dbt through the repository wrapper from the repository root. It supplies the
absolute DuckDB path and a temporary profile generated from the safe project
template, so it does not depend on the current directory or replace the local
Windows profile.

```powershell
uv run --active python scripts/project.py dbt parse
uv run --active python scripts/project.py dbt build
uv run --active python scripts/project.py dbt show --select mart_sales_by_segment
```

`dbt build` runs models and their configured data tests. `dbt parse` only checks
the project graph and does not require a warehouse. Data-running commands stop
before execution if the warehouse file is missing. See
[`docs/phase-04-dbt-transformation.md`](../docs/phase-04-dbt-transformation.md)
for project-specific model validation steps. To run from another working
directory, invoke the wrapper using the absolute path to the clone and its active
Python environment.

The root `README.md` documents the full DLT → DuckDB → dbt → analytics and
Text-to-SQL → Airflow/Cosmos workflow.

