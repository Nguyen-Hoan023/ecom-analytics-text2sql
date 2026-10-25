# Python tests

The root suite covers Text-to-SQL policy and output, repository paths/wrapper commands, runtime staging safety, and dbt-to-catalog contracts. It does not require SQL Server, a populated warehouse, Gemini, or Docker.

| Test module | Main contract |
|---|---|
| <code>test_text2sql_guardrails.py</code> | Validator/catalog/policy reject unsafe or unapproved queries. |
| <code>test_text2sql_nl_service_offline.py</code> | Offline routing and no-model-call guarantees. |
| <code>test_text2sql_output.py</code> | Safe bounded result formatting. |
| <code>test_text2sql_charting.py</code> | Deterministic chart suggestions for supported result shapes. |
| <code>test_project_paths.py</code> | Repository root and DuckDB path resolution. |
| <code>test_project_commands.py</code> | Command-wrapper behavior and missing-warehouse handling. |
| <code>test_prepare_runtime.py</code> | Astro staging allowlist, marker, and forbidden-file checks. |
| <code>test_dbt_contract.py</code> | Gold manifest and semantic catalog consistency. |

Run from the repository root after <code>uv sync --locked</code>:

    uv run --project . python -m unittest discover -s tests -p "test_*.py" -v

Airflow graph contracts live separately in <code>orchestration/tests/dags/</code> and run inside Astro Runtime. They validate DAG structure, not a live data refresh.
