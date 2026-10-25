"""Project-specific contracts for the e-commerce warehouse refresh DAG."""

from __future__ import annotations

from airflow.models import DagBag


DAG_ID = "ecommerce_warehouse_refresh"


def _load_dag():
    dag_bag = DagBag(include_examples=False)
    assert not dag_bag.import_errors, dag_bag.import_errors
    # Inspect the parsed graph directly, without a scheduler/serialized-DAG lookup.
    dag = dag_bag.dags.get(DAG_ID)
    assert dag is not None, f"Expected DAG {DAG_ID!r} to be loaded"
    return dag


def _reachable_task_ids(dag, start_task_id: str) -> set[str]:
    reached: set[str] = set()
    pending = [start_task_id]
    while pending:
        task_id = pending.pop()
        if task_id in reached:
            continue
        reached.add(task_id)
        pending.extend(dag.get_task(task_id).downstream_task_ids - reached)
    return reached


def test_refresh_dag_is_manual_and_serialized():
    dag = _load_dag()

    assert dag.schedule_interval is None
    assert dag.catchup is False
    assert dag.max_active_runs == 1
    assert dag.max_active_tasks == 1
    assert dag.default_args.get("retries") == 0


def test_refresh_flow_orders_ingestion_dbt_and_quality_gate():
    dag = _load_dag()
    task_ids = {task.task_id for task in dag.tasks}
    dbt_task_ids = {task_id for task_id in task_ids if task_id.startswith("dbt_transform.")}

    assert "preflight_check" in task_ids
    assert "dlt_ingestion" in task_ids
    assert "quality_gate" in task_ids
    assert dbt_task_ids, "Cosmos should render dbt model/test tasks into this DAG"
    assert "dlt_ingestion" in dag.get_task("preflight_check").downstream_task_ids

    reachable_after_ingestion = _reachable_task_ids(dag, "dlt_ingestion")
    assert dbt_task_ids & reachable_after_ingestion
    assert "quality_gate" in reachable_after_ingestion


def test_every_task_has_retries_disabled_until_recovery_is_accepted():
    dag = _load_dag()

    assert all(task.retries == 0 for task in dag.tasks)
