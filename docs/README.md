# Documentation

This folder contains current architecture, setup, operating, analytical, and decision documents.

## Start here

| Document | Use it for |
|---|---|
| [Architecture](architecture.md) | Data flow, component ownership, runtime boundaries, and repository conventions. |
| [Setup](setup.md) | Host/container prerequisites, environment configuration, and first run. |
| [Operations](operations.md) | Refresh windows, quality gates, concurrency, and failure recovery. |
| [Demo walkthrough](demo.md) | A concise path from source data to marts, charts, and Text-to-SQL answers. |
| [Data contract](data-contract.md) | Source tables/grain, metric definitions, data quality, and assumptions. |
| [Business insights](business-insights.md) | Snapshot findings, decision questions, and interpretation limits. |
| [Decision records](decisions/README.md) | Repository boundaries and shared DuckDB access decisions. |
| [Visual assets](assets/README.md) | Architecture diagram and chart inventory. |

Project code owns executable contracts: dbt YAML/SQL, the Text-to-SQL semantic catalog/policy, and the evaluation golden set. This folder explains how to operate and interpret those contracts.

## Documentation conventions

- Describe the current implementation and link to the code that owns behavior.
- State metric grain, units, snapshot date, and caveats.
- Keep credentials, API keys, customer-level examples, raw extracts, and local database files out of docs.
- Assume commands run from the repository root unless stated otherwise.
- Treat evidence as historical unless a run date, suite, and provenance are stated.
- Record lasting cross-module choices in decision records; put procedures in setup and operations guides.
