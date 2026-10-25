"""Initialize isolated Airflow metadata for Astro DAG contract tests."""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session", autouse=True)
def isolated_airflow_metadata(tmp_path_factory):
    # `astro dev parse` and `astro dev pytest` use separate containers. Cosmos
    # writes its dbt-ls cache to Airflow Variables even when no task is executed.
    # Initialize a temporary metadata DB rather than relying on a running stack.
    from airflow import settings
    from airflow.utils.db import initdb

    metadata_path = tmp_path_factory.mktemp("airflow-metadata") / "airflow.db"
    metadata_uri = f"sqlite:///{metadata_path.as_posix()}"
    with pytest.MonkeyPatch.context() as configuration:
        configuration.setenv("AIRFLOW__DATABASE__SQL_ALCHEMY_CONN", metadata_uri)
        configuration.setenv("AIRFLOW__CORE__LOAD_EXAMPLES", "false")
        # Airflow can already be imported during test collection, so rebind its
        # cached connection string and engine as well as the environment setting.
        configuration.setattr(settings, "SQL_ALCHEMY_CONN", metadata_uri)
        settings.dispose_orm()
        settings.configure_orm()
        try:
            initdb(load_connections=False)
            yield
        finally:
            settings.dispose_orm()
