# Astro runtime staging

<code>prepare_runtime.py</code> assembles a safe, generated source tree under <code>orchestration/include/runtime/</code> for the Astro Docker build.

## Run

    uv run --project . python scripts/project.py astro prepare

Direct invocation from the repository root is also supported:

    uv run --project . python orchestration/scripts/prepare_runtime.py

## What the helper copies

Only allowlisted Python files from <code>ingestion/</code>, Python/YAML files from <code>text2sql/</code>, and dbt SQL/YAML/seed files from <code>ecom_analytics/</code>. It then installs a container profile from <code>profiles.yml.example</code>.

The helper excludes symlinks, <code>.env</code>, real profiles, <code>.user.yml</code>, DuckDB, Airflow metadata, virtual environments, caches, dbt targets, and logs. It validates required staged files and scans for forbidden local data before swapping the stage.

A marker protects user data: an unmarked existing <code>include/runtime/</code> is never replaced. Edit root source files and rerun the helper; do not modify the generated stage by hand.
