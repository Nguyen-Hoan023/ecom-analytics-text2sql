# Xóm E-Com Airflow/Cosmos orchestration

This Astro project runs the existing pipeline in order:

```text
SQL Server read-only preflight
  → DLT snapshot replace into DuckDB Bronze + source/target count reconciliation
  → Cosmos-rendered dbt models and tests (Silver → Intermediate → Gold)
  → offline Text-to-SQL warehouse baselines (Q01–Q15; no Gemini calls)
```

The DAG is `xom_ecom_warehouse_refresh`. Runtime acceptance has passed, but the DAG remains
manual-trigger only; no recurring schedule is enabled. `max_active_runs=1` and
`max_active_tasks=1` serialize runs and Cosmos' per-model/test tasks while they share the local
DuckDB file.

For fresh-clone configuration, see [`docs/setup.md`](../docs/setup.md). For refresh windows,
success criteria and failure recovery, see [`docs/operations.md`](../docs/operations.md) and
the [DuckDB access decision](../docs/decisions/0002-duckdb-access.md).

## Environment and packaging

- Airflow and Cosmos run in Astro Runtime `12.7.0` (Python 3.11 / Airflow 2.10.x).
- dbt Core and dbt-duckdb are isolated in `/usr/local/airflow/dbt_venv`; Cosmos invokes that
  venv using `ExecutionMode.LOCAL` and subprocess parsing/execution.
- Root source packages are staged into this Astro project's Docker build context by
  `scripts/prepare_runtime.py`. The generated `include/runtime/` folder is ignored by Git.
- Staging allowlists Python/YAML/SQL/dbt seed files and builds the container profile from
  `ecom_analytics/profiles.yml.example`. It excludes `.env`, the real `profiles.yml`, DuckDB,
  dbt artifacts, logs, and Python environments.
- The local override mounts staged source read-only and `../duckdb_warehouse` read-write. Only
  dbt's `target/` and `logs/` paths are temporary writable mounts for Cosmos DAG parsing.
  After changing source code, rerun the staging command before rebuilding/parsing.
- `orchestration/.env` supplies SQL Server settings and the Linux container path to DuckDB.
  It is local-only and must never be printed or committed. Do not add the Gemini API key here;
  this DAG runs only offline baselines.
- Airflow's PostgreSQL service is for Airflow metadata, not the analytics warehouse. The SQL
  Server remains an external read-only source.

## Prepare and validate

Run from the repository root in PowerShell:

```powershell
uv run --active python orchestration/scripts/prepare_runtime.py
Set-Location orchestration
astro dev parse
```

`prepare_runtime.py` refreshes only a generated stage carrying its own marker. If `include/runtime`
exists but is not marked as generated, the script stops rather than replacing it. Run it again
after changing ingestion, Text-to-SQL or dbt code.

After parsing passes, check port 8080 is free, then start Airflow:

```powershell
astro dev start
astro dev ps
astro dev run db check
astro dev run dags list-import-errors
astro dev run dags list
```

Run the project DAG contract tests inside the Astro image:

```powershell
astro dev pytest tests/dags
```

Before opening a scheduler shell, make sure no host CLI/UI or manual dbt command is reading the
same DuckDB file while the DAG refreshes it:

```powershell
astro dev bash --scheduler
```

Then, from the container's Linux shell:

```bash
git --version
python -m ingestion.check_source_connection
/usr/local/airflow/dbt_venv/bin/dbt --version
/usr/local/airflow/dbt_venv/bin/dbt --log-path /tmp/ecom-dbt-debug debug \
  --project-dir /usr/local/airflow/ecom_analytics \
  --profiles-dir /usr/local/airflow/ecom_analytics \
  --target dev
python -m text2sql.evaluation.run_baselines
```

The host connectivity check does not prove that Docker can reach SQL Server; run the read-only
smoke query from the scheduler container too. The dbt debug command writes logs under `/tmp`,
not into the read-only staged project. The Compose override also gives dbt's normal `target/`
and `logs/` locations ephemeral writable mounts for `dbt ls` during scheduler parsing.

`dbt debug` also checks for the system `git` executable. It is installed in the Astro image via
`packages.txt`; after changing that file, rebuild/restart the local Astro stack before rerunning
the container checks.

## Run and stop

After container checks pass, use the Airflow UI at `http://localhost:8080` to manually trigger
`xom_ecom_warehouse_refresh`. Verify preflight, DLT row-count reconciliation, all dbt model/test
tasks, and the 15-case offline quality gate. Run it a second time with unchanged source to check
idempotency. Do not schedule recurring runs until both runs and failure recovery pass.

To stop the local stack:

```powershell
astro dev stop
```

## Troubleshooting

- **Docker pipe/daemon error:** confirm Docker Desktop's Linux Engine is running and that the
  current PowerShell session can run `docker version` with both Client and Server details.
- **Missing root package or dbt project at parse:** rerun `prepare_runtime.py` from repo root,
  then rerun `astro dev parse` from `orchestration/`.
- **dbt profile uses a Windows path:** check only that `orchestration/.env` sets
  `DUCKDB_PATH=/usr/local/airflow/duckdb_warehouse/warehouse.duckdb`; the staged profile reads
  that variable. Keep the root Windows `ecom_analytics/profiles.yml` separate.
- **SQL Server works on host but fails in container:** validate injected variable presence
  without printing values, then diagnose Docker DNS/outbound network and SQL Server permissions.
- **A changed `.env` value is not visible:** restart the Astro stack so services receive the new
  environment. Preserve the failed run for diagnosis; after correcting the cause, prefer a new
  full DAG run as described in the operations runbook.
- **DuckDB is locked:** stop host Text-to-SQL, dbt docs/CLI and other processes using the same
  file before triggering a refresh.

For phase decisions, expected outcomes, and acceptance evidence, see
[`docs/phase-07-airflow-cosmos.md`](../docs/phase-07-airflow-cosmos.md).
