# Airflow DAGs

The current pipeline DAG is <code>ecommerce_warehouse_refresh</code>, defined in <code>ecommerce_warehouse_refresh.py</code>.

## Task sequence

    preflight_check → dlt_ingestion → dbt_transform → quality_gate

- <code>preflight_check</code> runs a read-only SQL Server connectivity smoke check.
- <code>dlt_ingestion</code> replaces the DuckDB Bronze snapshot and reconciles four table counts.
- <code>dbt_transform</code> is a Cosmos-rendered group of dbt model and test tasks.
- <code>quality_gate</code> runs the 15 warehouse baseline cases; it does not contact Gemini.

The DAG is manually triggered, has catch-up disabled, allows one active run/task, and has retries disabled. These controls serialize access to the shared DuckDB file and avoid blindly repeating a snapshot write.

## Change contract

The graph tests in <code>orchestration/tests/dags/test_ecommerce_warehouse_refresh.py</code> verify importability, schedule, serialization, retries, and task ordering. Update them whenever the task graph or run policy changes. Business transformations belong in dbt; ingestion logic belongs in <code>ingestion/</code>.
