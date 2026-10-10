# E-Commerce Analytics & Text-to-SQL

A learning project to rebuild an end-to-end analytics pipeline from the Xóm E-Com dataset, following the reference flow while documenting design choices and validating each layer.

## Project goals

- Answer the 15 business questions in the Xóm E-Com context with traceable, tested data models.
- Build the flow incrementally: SQL Server source → DLT ingestion → DuckDB → dbt Bronze/Silver/Gold → analytics and Text-to-SQL.
- Keep Apache Airflow/Cosmos in the planned architecture, then add orchestration after the data pipeline works locally.
- Treat the reference repository as a design reference; verify assumptions against the live source and explain changes.

## Current status

**Phase 1 — source understanding and data contract:** first source profile is recorded in the docs. Customer join coverage is complete; product and region each have two unmatched fact rows that need classification. Add the profile date and remaining market-domain results before closing this phase.

Start here: [Phase 1: Data understanding](docs/phase-01-data-understanding.md) and [read-only SQL profile](sql/phase_01_profile.sql).

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
