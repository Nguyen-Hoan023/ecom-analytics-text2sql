# E-Commerce Analytics & Text-to-SQL

A learning project to rebuild an end-to-end analytics pipeline from the Xóm E-Com dataset, following the reference flow while documenting design choices and validating each layer.

## Project goals

- Answer the 15 business questions in the Xóm E-Com context with traceable, tested data models.
- Build the flow incrementally: SQL Server source → DLT ingestion → DuckDB → dbt Bronze/Silver/Gold → analytics and Text-to-SQL.
- Keep Apache Airflow/Cosmos in the planned architecture, then add orchestration after the data pipeline works locally.
- Treat the reference repository as a design reference; verify assumptions against the live source and explain changes.

## Current status

**Phase 1 — source understanding and data contract:** source profile and metric contract v1 are recorded in the docs. The latest profile run is recorded at `2026-10-10 14:25:29.4548071 UTC`. Customer joins match; three unique sales rows are missing product/region matches (sales 506, profit 253). v1 assumptions are explicit, including source `sales` gross/net semantics and heuristic VIP/churn thresholds; validate them during analysis.

**Phase 2 — project setup:** Python 3.11 dependencies are locked in `uv.lock` and installed into the existing workspace venv. `.env.example` and a validated settings module are ready; the actual SQL password remains local, and no source data has been queried. See [Phase 2: Project setup](docs/phase-02-project-setup.md).

**Phase 3 — source connection:** the local `.env` has the non-secret SQL Server settings. DNS and TCP port 1433 are reachable; SQL authentication is pending the local password entry. A read-only connection smoke check is documented in [Phase 3: SQL Server connection](docs/phase-03-source-connection.md).

Start here: [Phase 1: Data understanding](docs/phase-01-data-understanding.md), [read-only SQL profile](sql/phase_01_profile.sql), [Phase 2 setup guide](docs/phase-02-project-setup.md), and [Phase 3 connection guide](docs/phase-03-source-connection.md).

## Planned stages

| Stage | Outcome |
|---|---|
| 1. Understand the source | Verified table grain, candidate keys, join coverage, data quality baseline, metric definitions |
| 2. Set up the project | Reproducible Python environment, configuration and secret handling |
| 3. Ingest with DLT | Repeatable SQL Server → DuckDB Bronze load with load metadata |
| 4. Transform with dbt | Typed/clean Silver models and tested Gold marts |
| 5. Answer business questions | SQL analyses, validated KPI definitions and documented insights |
| 6. Add Text-to-SQL | Constrained generation, SQL validation, read-only execution and evaluation cases |
| 7. Orchestrate with Airflow/Cosmos | Scheduled, observable workflow after each task works independently |
| 8. Polish and publish | Architecture docs, reproducible setup, CI checks and final project walkthrough |

## Security and data handling

- Never commit .env files, API keys, source credentials, local database files, or source extracts.
- Phase 1 profiling is read-only and avoids selecting names, emails, or other customer-level PII.
- Share only aggregate profiling results in issues or documentation.

## Reference material

- [Xóm E-Com schema and business context](https://dataset.xomdata.com/datasets/schema/e_commerce)
- [Reference implementation](https://github.com/tunguyenn99/a-simple-t2s-flow)
- [Reference business context and 15 questions](https://github.com/tunguyenn99/a-simple-t2s-flow/blob/main/context.md)
