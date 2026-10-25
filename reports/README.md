# Sanitized project evidence

This directory stores aggregate, sanitized evaluation and runtime evidence. Do not store raw logs, prompts, customer rows, source extracts, credentials, or warehouse files here.

## Index

| Report | Content |
|---|---|
| [Warehouse reconciliation](warehouse-reconciliation.md) | Q1–Q15 source/mart comparisons for the documented snapshot; original ad-hoc source SQL was not retained. |
| [Text-to-SQL acceptance summary](text2sql-evaluation/acceptance-summary.md) | Owner-confirmed baseline, canonical NL, offline guardrail, and UI outcomes with evidence limits. |
| [Text-to-SQL run artifacts](text2sql-evaluation/README.md) | Rules for individual sanitized JSON evaluations. |
| [Orchestration acceptance](orchestration/README.md) | Provenance and limits for local Astro/Airflow runs. |

## Evidence rules

- A report describes a specific snapshot, model, suite, and date; it is not live system status or a quota reading.
- Keep owner-confirmed summaries distinct from exported logs; never invent run IDs or timings.
- Preserve failed/unavailable runs as historical evidence. A later success updates current acceptance but does not erase earlier outcomes.
- Write new results to a new file and record the exact suite/variant. Do not overwrite a historical artifact.
- Keep SQL baselines, deterministic guardrails, model evaluation, and Airflow acceptance as separate claims.
- Store only sanitized case/status/assertion metadata and aggregate values.

The chart images are reproducible outputs; see <code>docs/assets/charts/README.md</code> for their source.
