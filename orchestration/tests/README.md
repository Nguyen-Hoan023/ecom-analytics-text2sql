# Orchestration tests

This directory holds contract tests for the Airflow workflow. They validate the DAG structure and safety properties without contacting SQL Server, calling Gemini, or running a warehouse refresh.

## Test areas

| Path | Scope |
|---|---|
| [`dags/`](dags/README.md) | DAG identity, manual-only schedule, task graph, serialization, retry policy, and quality-gate dependency. |

Run the contract suite inside the project image with Astro CLI:

    cd orchestration
    astro dev pytest tests/dags

The GitHub Actions orchestration workflow builds the image, parses DAGs, and runs these tests. A DAG parse checks import/render behavior; contract tests check expected scheduling and dependencies; neither is evidence of a live end-to-end data refresh. The recorded local runtime observations are in [workflow acceptance](../../reports/orchestration/workflow-acceptance.md).

When changing the workflow, update both the contract tests and [DAG guide](../dags/README.md). Keep external connectivity and credential checks out of unit/contract tests; those belong to preflight at runtime.
