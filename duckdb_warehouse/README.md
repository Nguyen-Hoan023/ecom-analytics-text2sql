# Local DuckDB warehouse

This directory is the local runtime location for the analytical warehouse. DuckDB is embedded and stored as a file; it is not a separately managed database server.

## Lifecycle

1. DLT loads the SQL Server snapshot into Bronze tables.
2. dbt builds staging, intermediate, and Gold models in the same warehouse.
3. Tests, static charts, and the Text-to-SQL read-only executor consume the curated data.
4. Astro mounts this directory into its Linux container at `/usr/local/airflow/duckdb_warehouse/` so scheduled/manual orchestration writes to the same file.

The default file is `warehouse.duckdb`; the resolver is `ingestion.config.resolve_warehouse_path()`. Override it with `DUCKDB_PATH` when necessary. Host paths can be relative to the repository root; the container path must be an absolute Linux path.

## Local files and safety

- The database file, WAL files, and locks are runtime state and are excluded from Git.
- Do not commit or share this directory's database contents; it contains source-derived data.
- Do not delete the warehouse or WAL to work around a lock. Stop the process that owns the file and diagnose the active reader/writer first.
- DLT replaces the source snapshot. Do not run ingestion/dbt writes while the Text-to-SQL UI, charts, or other readers are using the same file.
- Treat the DAG refresh as a maintenance window; reopen readers after the DAG quality gate succeeds.

See [warehouse access decisions](../docs/decisions/0002-duckdb-access.md), [operations](../docs/operations.md), and [setup](../docs/setup.md).
