# Phase 7 runtime acceptance — evidence record

**Recorded:** 2026-10-25 (Asia/Saigon)
**Runtime events:** 2026-10-24
**Suite:** Astro CLI / Airflow / Cosmos manual DAG acceptance
**Result:** owner-confirmed pass for image/parse, container checks, 15/15 offline baselines, two successful DAG runs, idempotency comparison and fail-fast recovery.

## Evidence provenance

This is a sanitized summary of the project owner's confirmations in the project conversation, including terminal output and Airflow UI review. It is not an exported Airflow log or machine-generated report. Exact DAG run IDs and the original full logs were not retained, so this file does not invent them. See [`docs/phase-07-airflow-cosmos.md`](../../docs/phase-07-airflow-cosmos.md) for design, commands and the acceptance checklist.

## Acceptance results

| Check | Status | Recorded evidence | Scope and limits |
|---|---|---|---|
| Astro image and DAG parsing | Pass, owner-confirmed | Image build completed; `astro dev parse` and Airflow UI succeeded; `dags list-import-errors` returned `No data found`. | Local image/runtime only; not a production deployment. |
| Container environment | Pass, owner-confirmed | Scheduler container connected to SQL Server; source smoke query returned `1`; dbt used isolated `/usr/local/airflow/dbt_venv`. | Credentials are local and are intentionally not stored here. |
| Baseline quality gate | Pass, owner-confirmed | `python -m text2sql.evaluation.run_baselines` reported 15/15. | Offline warehouse baseline; no Gemini calls. |
| DAG run 1 | Pass, owner-confirmed | Owner confirmed the run and the 15/15 gate. | Run ID not retained. |
| DAG run 2 / idempotency | Pass, owner-confirmed | Two runs against unchanged source were compared; counts and business totals matched. | Confirms repeatability for this snapshot, not future freshness. |
| Failure recovery | Pass, owner-confirmed | Changing the source host made `preflight_check` fail and downstream tasks become `upstream_failed`. Restoring the host allowed a successful run. | Intentional fail-fast check; no automatic retries enabled. |

### Reconciled snapshot values

| Measure | Value |
|---|---:|
| Customer rows | 17.415 |
| Sales lines | 51.290 |
| Total sales | 6.517.674,00 |
| Total profit | 1.065.413,58 |

Values retain source units. Currency and whether source `sales` is gross or net have not been confirmed. The snapshot covers 2020–2023.

## Runtime contract captured

- DAG `xom_ecom_warehouse_refresh` remains manual (`schedule=None`), serialized (`max_active_runs=1`, `max_active_tasks=1`) and uses `retries=0`.
- Logical flow: preflight → DLT snapshot ingestion → dbt/Cosmos models and tests → 15-case baseline quality gate.
- The local Text-to-SQL service and refresh DAG share one DuckDB file. Do not query through the UI while the DAG writes; see [`docs/operations.md`](../../docs/operations.md).
- No production schedule, production deployment, Gemini call or future data-freshness guarantee is implied by this acceptance.

## Related evidence

- [Phase 7 design and owner-confirmed checklist](../../docs/phase-07-airflow-cosmos.md)
- [Q1–Q15 warehouse reconciliation](../../docs/checkpoint-q1-q15-reconciliation.md)
- [Phase 6 Text-to-SQL acceptance](../../docs/phase-06-progress-checkpoint.md)
