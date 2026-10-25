# Airflow and Astronomer Cosmos

This optional Astro project orchestrates the batch refresh and exposes task-level logs, dependencies, and a quality gate. Local ingestion and dbt development do not require Airflow.

## Workflow

Manual DAG <code>ecommerce_warehouse_refresh</code>:

    preflight_check → dlt_ingestion → dbt_transform (Cosmos models/tests) → quality_gate (15 SQL/template baselines)

There is no recurring schedule. Active runs and tasks are serialized because all stages share one DuckDB file. Retries are disabled while snapshot-write recovery remains a manual decision. The quality gate does not call Gemini.

## Runtime and mounts

- Astro Runtime runs Linux containers; dbt Core and dbt-duckdb run in the isolated <code>/usr/local/airflow/dbt_venv</code>.
- Cosmos uses local execution and subprocess invocation to execute dbt graph nodes.
- <code>orchestration/scripts/prepare_runtime.py</code> stages allowlisted Python/YAML/SQL/dbt files under generated <code>include/runtime/</code>.
- Staging uses the safe dbt profile template and excludes local env files, real profiles, warehouse, logs, target directories, and Python environments.
- Staged code is mounted read-only; the shared warehouse is writable. Astro Postgres stores Airflow metadata, not analytical data.
- Container environment lives in <code>orchestration/.env</code>, separate from the host root <code>.env</code>. Use the Linux DuckDB path and do not add Gemini credentials.

## Prepare and run

Prerequisites: Docker Desktop with Linux Engine and Astro CLI. From repository root:

    if (-not (Test-Path orchestration/.env)) {
        Copy-Item -LiteralPath orchestration/.env.example -Destination orchestration/.env
    }
    notepad orchestration/.env
    uv run --project . python scripts/project.py astro prepare

In the container environment, set the source variables and <code>DUCKDB_PATH=/usr/local/airflow/duckdb_warehouse/warehouse.duckdb</code>. Then run:

    Set-Location orchestration
    astro dev parse
    astro dev pytest tests/dags
    astro dev start
    astro dev ps
    astro dev run dags list-import-errors
    astro dev run dags list

Open <http://localhost:8080> and trigger the DAG manually. For task-level details see [dags/README.md](dags/README.md); the DAG contract test is in [tests/dags/README.md](tests/dags/README.md).

## Operations and recovery

Stop host dbt, charts, and Text-to-SQL processes before a refresh. Validate SQL Server access from the scheduler container as well as from the host. Preflight must succeed before DLT; DLT replaces Bronze and reconciles counts; dbt builds/tests; the quality gate evaluates Gold.

If a run fails, preserve the logs, diagnose the failed task, correct configuration, then trigger a complete new DAG run. Do not delete failed run history. Do not run a concurrent writer against the same DuckDB file.

The DAG is a local development workflow, not a production schedule or freshness guarantee. Never print environment values in shared logs.
