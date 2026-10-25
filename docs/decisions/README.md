# Architecture decision records

Decision records capture choices that affect more than one module. Each record explains the context, decision, consequences, and alternatives considered.

## Records

| Record | Decision |
|---|---|
| [0001 — Repository layout](0001-repository-layout.md) | Keep ingestion, dbt, serving, orchestration, and reports in explicit modules within one repository. |
| [0002 — DuckDB access](0002-duckdb-access.md) | Use one local DuckDB warehouse, resolve its path consistently, and serialize writers because the file is shared. |

## Adding a decision

Create the next numbered file as <code>0003-short-title.md</code>. Include:

1. Status and date.
2. Context and constraints.
3. The decision and the reason it fits this system.
4. Consequences, including operational trade-offs.
5. Alternatives rejected and the evidence that would cause the decision to be revisited.

Do not use a decision record as a step-by-step runbook; link to the relevant module README for operations.
