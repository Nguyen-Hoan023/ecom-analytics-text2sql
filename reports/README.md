# Project evidence index

**Index updated:** 2026-10-25. This page links the accepted project checkpoints,
the sanitized evaluation artifacts, the saved Gold charts and the current CI
state. The records describe different snapshots and suites; do not combine them
into one claim of a live end-to-end run.

## Acceptance and analysis records

| Evidence | Recorded date | Suite/model | Status and scope |
|---|---|---|---|
| [Q1–Q15 reconciliation](../docs/checkpoint-q1-q15-reconciliation.md) | 2026-10-18 | Warehouse baselines; no LLM | Source/mart results reconciled for the documented 2020–2023 snapshot. Source SQL output shared at the time; the original ad-hoc SQL is not stored. |
| [Business insights](../docs/phase-05-business-insights.md) and [10-chart guide](../analytics/visualization/README.md) | Snapshot 2020–2023 | Gold marts; static charts | Aggregate findings and reproducible PNG outputs. These are descriptive and retain the documented metric caveats. |
| [Phase 6 checkpoint](../docs/phase-06-progress-checkpoint.md) | 2026-10-23 | Golden set v1; Gemini `gemini-3.5-flash-lite` for canonical NL; offline baseline/guardrail suites | Checkpoint records 15/15 baseline, 15/15 canonical Vietnamese, 14/14 deterministic offline guardrails and the basket guardrail behavior. Final owner-confirmed canonical results are documented here; no final all-cases JSON export is stored. |
| [Phase 7 runtime acceptance](orchestration/phase-07-acceptance.md) | Runtime events 2026-10-24; recorded 2026-10-25 | Astro CLI / Airflow / Cosmos; no LLM | Owner-confirmed image/parse, container checks, 15/15 baseline gate, two successful DAG runs, idempotency and failure recovery. Run IDs and original full logs were not retained. |
| [Phase 8 plan](../docs/phase-08-polish-and-release.md) | 2026-10-25 | Offline/dbt/Astro CI | Workflows are implemented; the first clean GitHub Actions run is still pending. Workflow files are configuration, not evidence of a completed CI run. |

## Sanitized Text-to-SQL run artifacts

The JSON files below are **historical run artifacts**. Do not overwrite them to
represent a later run; use a new filename and record its model, timestamp,
evaluation set, variant and scope.

| File | Recorded run | Model | Recorded result | Interpretation |
|---|---|---|---|---|
| [`vi-canonical.json`](text2sql-evaluation/vi-canonical.json) | 2026-10-21 02:45 UTC | `gemini-3.8-flash` | 1/15 passed | Early run stopped passing most cases because the service was unavailable. It predates the later owner-confirmed canonical Q01–Q15 acceptance in the [Phase 6 checkpoint](../docs/phase-06-progress-checkpoint.md). |
| [`guardrail-basket-vi.json`](text2sql-evaluation/guardrail-basket-vi.json) | 2026-10-23 14:59 UTC | `gemini-3.5-flash-lite` | Evaluator marked 0/1 passed | The answer was routed and executed, but the evaluator reported a Q15 output-column contract mismatch. The later [Phase 6 checkpoint](../docs/phase-06-progress-checkpoint.md) records the reviewed safe behavior: zero qualifying pairs at the configured 0.5% support and no hallucinated pairs. Keep the evaluator artifact as-is; it is not a current rerun. |

The payloads contain case IDs, sanitized statuses and assertion messages; they
do not represent a live quota snapshot. Keep their failed/unavailable outcomes
as history. They predate later owner-confirmed Phase 6 acceptance and must not be
rewritten as if they were the final passing run.

For a new run, use a distinct case/date-specific output path under
`reports/text2sql-evaluation/`. Never store `.env`, credentials, prompts containing
private data, raw query rows, source extracts, or warehouse files in `reports/`.

## Evidence handling rules

- The Phase 7 acceptance summary is sourced from owner confirmations and shared
  terminal/UI results. It is not a raw log export; no run ID is invented.
- The final Phase 6 canonical acceptance is recorded in its checkpoint because
  no sanitized JSON artifact for the complete 15-case passing run was retained.
- The saved charts are outputs from the documented Gold visualization script;
  they are not a fresh regeneration in this documentation update.
- Do not store `.env`, credentials, private prompts, raw customer rows, source
  extracts, local exports, or warehouse files in reports.
- For a new evaluation, write to a distinct date/case-specific file under
  `reports/text2sql-evaluation/`; record model and exact suite/variant.

The presentation path and reproducible commands are in the
[project walkthrough](../docs/project-walkthrough.md).
