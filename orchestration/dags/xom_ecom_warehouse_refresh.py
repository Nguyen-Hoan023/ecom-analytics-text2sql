"""Airflow DAG to orchestrate the Xóm E-Com analytics pipeline end-to-end.

Flow:
  1. preflight_check: verify read-only connectivity to SQL Server source.
  2. dlt_ingestion: ingest snapshot from SQL Server into DuckDB Bronze (write_disposition='replace').
  3. dbt_transform: run and test dbt models via Astronomer Cosmos (Silver, Intermediate, 12 Gold marts).
  4. quality_gate: run baseline assertions on Gold marts to guarantee analytical integrity.

Airflow limits both active runs and active tasks to one because Cosmos expands the dbt
project into multiple model/test tasks that all read or write the shared DuckDB file.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from airflow.decorators import dag, task
from cosmos import DbtTaskGroup, ExecutionConfig, ProfileConfig, ProjectConfig, RenderConfig
from cosmos.constants import ExecutionMode, InvocationMode, LoadMode

# Paths inside the Airflow container (as mounted in docker-compose.override.yml)
AIRFLOW_HOME = Path("/usr/local/airflow")
DBT_PROJECT_PATH = AIRFLOW_HOME / "ecom_analytics"
DBT_PROFILES_PATH = DBT_PROJECT_PATH / "profiles.yml"
DBT_EXECUTABLE_PATH = Path("/usr/local/airflow/dbt_venv/bin/dbt")


@dag(
    dag_id="xom_ecom_warehouse_refresh",
    schedule=None,  # Manual trigger; schedule after verifying idempotency and recovery
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,  # Serialize DAG runs that read/write the shared DuckDB file.
    max_active_tasks=1,  # Cosmos expands to many tasks; serialize those too.
    default_args={"retries": 0},  # Do not retry source writes until recovery is validated.
    doc_md=__doc__,
    tags=["xom-ecom", "medallion", "dbt", "cosmos"],
)
def warehouse_refresh():

    @task(task_id="preflight_check")
    def task_preflight_check() -> None:
        """Verify SQL Server source read-only connectivity before starting ingestion."""
        from ingestion.check_source_connection import main as check_connection

        print("Executing SQL Server preflight connection check...")
        check_connection()
        print("SQL Server preflight check succeeded.")

    @task(task_id="dlt_ingestion")
    def task_dlt_ingestion() -> None:
        """Ingest the 4 source tables via DLT into DuckDB Bronze and verify row counts."""
        from ingestion.run_pipeline import main as run_ingestion

        print("Executing DLT snapshot ingestion into DuckDB Bronze...")
        run_ingestion()
        print("DLT ingestion and Bronze row count reconciliation succeeded.")

    # Cosmos task group for dbt transformation (Silver -> Intermediate -> 12 Gold marts)
    dbt_transform = DbtTaskGroup(
        group_id="dbt_transform",
        project_config=ProjectConfig(dbt_project_path=DBT_PROJECT_PATH),
        profile_config=ProfileConfig(
            profile_name="ecom_analytics",
            target_name="dev",
            profiles_yml_filepath=DBT_PROFILES_PATH,
        ),
        execution_config=ExecutionConfig(
            execution_mode=ExecutionMode.LOCAL,
            dbt_executable_path=str(DBT_EXECUTABLE_PATH),
        ),
        render_config=RenderConfig(
            load_method=LoadMode.DBT_LS,
            dbt_executable_path=str(DBT_EXECUTABLE_PATH),
            invocation_mode=InvocationMode.SUBPROCESS,
        ),
        operator_args={"append_env": True},
    )

    @task(task_id="quality_gate")
    def task_quality_gate() -> None:
        """Run golden baseline assertions against DuckDB Gold marts."""
        from text2sql.evaluation.run_baselines import main as run_baselines

        print("Running warehouse baseline assertions (Q01-Q15)...")
        exit_code = run_baselines([])
        if exit_code != 0:
            raise RuntimeError(f"Quality gate baseline evaluation failed with code {exit_code}")
        print("Quality gate passed: all baseline assertions verified.")

    # Enforce strictly sequential DAG flow
    preflight = task_preflight_check()
    ingest = task_dlt_ingestion()
    gate = task_quality_gate()

    preflight >> ingest >> dbt_transform >> gate


dag_instance = warehouse_refresh()
