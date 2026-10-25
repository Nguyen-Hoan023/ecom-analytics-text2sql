# Airflow DAG graph tests

These tests load the DAG into an Airflow <code>DagBag</code>. They do not start a scheduler, connect to SQL Server, execute DLT, or write to DuckDB.

## Contracts covered

- No DAG import errors and expected DAG ID <code>ecommerce_warehouse_refresh</code>.
- Manual schedule, no catch-up, one active run/task, and no retries.
- Preflight before ingestion, a rendered Cosmos dbt task group, and a downstream quality gate.
- A test-only temporary SQLite metadata database initialized by <code>conftest.py</code> for Cosmos/Airflow Variables.

Run inside the Astro Runtime from <code>orchestration/</code>:

    astro dev pytest tests/dags

This is a structural contract. A passing graph test does not prove source access or a successful live pipeline run.
