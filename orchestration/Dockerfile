# Astro Runtime 12.7.0 (Apache Airflow 2.10.x + Python 3.11).
FROM quay.io/astronomer/astro-runtime:12.7.0-python-3.11

# The Astro project lives in a subdirectory, so sibling packages are staged under
# include/runtime by scripts/prepare_runtime.py before parsing/building the image.
COPY --chown=astro:0 include/runtime/ingestion/ /usr/local/airflow/ingestion/
COPY --chown=astro:0 include/runtime/text2sql/ /usr/local/airflow/text2sql/
COPY --chown=astro:0 include/runtime/ecom_analytics/ /usr/local/airflow/ecom_analytics/

# Keep dbt isolated from Airflow's Python environment. Cosmos LOCAL invokes this
# executable directly for both DAG parsing and dbt tasks.
USER astro
RUN python -m pip check && \
    python -m venv /usr/local/airflow/dbt_venv && \
    /usr/local/airflow/dbt_venv/bin/pip install --no-cache-dir \
        "dbt-core==1.12.5" \
        "dbt-duckdb==1.11.0" \
        "duckdb==1.5.6" && \
    /usr/local/airflow/dbt_venv/bin/pip check && \
    mkdir -p /usr/local/airflow/ecom_analytics/target \
             /usr/local/airflow/ecom_analytics/logs
