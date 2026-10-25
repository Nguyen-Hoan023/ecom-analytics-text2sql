# Warehouse refresh workflow acceptance

**Evidence recorded:** 2026-10-25
**Runtime observations:** 2026-10-24
**Scope:** Local Astro Runtime, Airflow, Cosmos, and the manual refresh DAG.

## Provenance

This is a sanitized summary of owner-confirmed terminal and Airflow UI results. It is not an exported Airflow log. Exact run identifiers were not retained and are therefore not stated.

## Recorded checks

| Check | Result | Limits |
|---|---|---|
| Image and DAG parsing | Owner confirmed successful image build, Airflow UI access, and no DAG import errors. | Local runtime only. |
| Scheduler checks | Owner confirmed SQL Server connectivity, isolated dbt environment, and baseline command in the scheduler container. | Does not certify production deployment. |
| Repeated DAG runs | Two runs were confirmed successful; counts and aggregate totals were compared for unchanged source. | Repeatability for the observed snapshot only. |
| Fail-fast recovery | Incorrect source host caused preflight failure and downstream upstream-failed states; restored configuration allowed a successful run. | No automatic retries. |

## Snapshot comparison

| Measure | Value |
|---|---:|
| Customers | 17,415 |
| Sales lines | 51,290 |
| Total sales | 6,517,674.00 |
| Total profit | 1,065,413.58 |

Amounts retain source units; currency and gross/net semantics are unconfirmed. Transaction dates span 2020–2023.

## Current DAG contract

DAG <code>ecommerce_warehouse_refresh</code> is manual-only and serialized:

    preflight → DLT snapshot/reconciliation → Cosmos dbt models/tests → 15-case SQL/template quality gate

It does not call Gemini and has no recurring schedule. The UI and DAG share a DuckDB file, so avoid concurrent writers/readers during refresh. See the [current orchestration guide](../../orchestration/README.md) for run and recovery procedures.
