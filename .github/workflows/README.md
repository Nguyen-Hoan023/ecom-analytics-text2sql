# GitHub Actions

The workflows validate code and orchestration contracts without access to local credentials or the analytics warehouse.

| Workflow | Trigger | Checks |
|---|---|---|
| <code>offline.yml</code> | Push, pull request, manual dispatch | Python tests on Ubuntu/Windows, deterministic offline guardrails, dbt parse, and dbt Gold/catalog contract. |
| <code>orchestration.yml</code> | Relevant source changes or manual dispatch | Safe runtime staging, Astro image build, DAG/Cosmos parse, and DAG graph tests in the image. |

Both workflows use <code>uv.lock</code>, read-only repository permissions, and cancel superseded runs for the same ref. They do not call Gemini or the private SQL Server source.

Equivalent local checks:

    uv sync --locked
    uv run --project . python -m unittest discover -s tests -p "test_*.py" -v
    uv run --project . python scripts/project.py offline-checks
    uv run --project . python scripts/project.py dbt parse
    uv run --project . python -m text2sql.dbt_contract --manifest ecom_analytics/target/manifest.json

The Astro workflow additionally needs Docker and Astro CLI. Update path filters and staging allowlists when moving a package; update DAG contract tests when changing the workflow graph.
