# SQL Server ingestion

This package owns the source connection, read-only preflight/profile checks, DLT extraction, and reconciliation of the source snapshot against DuckDB Bronze.

## Data flow

    SQL Server: customer, ecom_sales, product, region
        → DLT SQL database source
        → DuckDB dataset bronze
        → exact per-table source/target row-count comparison

The pipeline uses DLT with <code>write_disposition="replace"</code>. Each run replaces the Bronze snapshot with the current source contents; it is not an incremental CDC pipeline. A mismatch raises an error so downstream dbt work should not be treated as accepted.

## Main files

| File | Responsibility |
|---|---|
| <code>config.py</code> | Loads and validates local connection settings; resolves DuckDB path from the repository root. |
| <code>sqlserver.py</code> | Builds the SQLAlchemy SQL Server engine and redacts configured credentials from driver errors. |
| <code>check_source_connection.py</code> | Read-only connection smoke check. |
| <code>profile_source_tables.py</code> | Checks required source tables and aggregate row counts without returning source rows. |
| <code>run_pipeline.py</code> | Reads the four tables, loads Bronze, and compares source and target counts. |

## Configuration

Create the root <code>.env</code> from <code>.env.example</code>. Required values are <code>SOURCE_SQLSERVER_HOST</code>, <code>SOURCE_SQLSERVER_DATABASE</code>, <code>SOURCE_SQLSERVER_USERNAME</code>, and <code>SOURCE_SQLSERVER_PASSWORD</code>. Optional values are <code>SOURCE_SQLSERVER_PORT</code> (default 1433), <code>SOURCE_SQLSERVER_SCHEMA</code> (default <code>e_commerce</code>), and <code>DUCKDB_PATH</code>.

Use a source account with the least permissions needed to read these four tables. Never print or commit the local environment file.

## Run

Execute from the repository root:

    uv run --project . python -m ingestion.check_source_connection
    uv run --project . python -m ingestion.profile_source_tables
    uv run --project . python -m ingestion.run_pipeline

The profile command reports table names/counts, not raw records. The source profile SQL in <code>sql/</code> is a separate manual, read-only profiling aid.

## Operational constraints

- Stop dbt, chart generation, CLI, and UI processes that use the same DuckDB file before a refresh.
- Airflow runs the same ingestion entry point from its scheduler container; container network access to SQL Server must be checked separately from host connectivity.
- A successful connection smoke test proves connectivity, not that DLT finished or row counts reconciled.
- If extraction fails, inspect the sanitized error and container network configuration. Do not paste credentials or raw customer values into logs/issues.
