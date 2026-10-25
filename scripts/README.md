# Repository command wrapper

<code>project.py</code> provides stable commands whose paths are anchored at the repository root rather than the caller's current directory.

| Command | Purpose |
|---|---|
| <code>doctor</code> | Check local Python/dbt/path prerequisites without creating a warehouse. |
| <code>dbt parse</code> | Parse dbt with the project template profile. |
| <code>dbt build</code>, <code>dbt test</code>, <code>dbt show</code> | Run dbt with the resolved warehouse and a temporary profile. |
| <code>offline-checks</code> | Run deterministic no-Gemini guardrails without a warehouse. |
| <code>baselines</code> | Run 15 warehouse SQL/template cases; requires existing data. |
| <code>charts</code> | Generate ten Gold charts; requires Gold marts. |
| <code>ui</code> | Start local Text-to-SQL UI; requires a warehouse. |
| <code>astro prepare</code> | Rebuild the generated allowlisted Astro runtime stage. |

Examples from repository root:

    uv run --project . python scripts/project.py doctor
    uv run --project . python scripts/project.py dbt parse
    uv run --project . python scripts/project.py offline-checks

The wrapper resolves relative DuckDB paths from repository root, supplies the dbt project and safe temporary profile, and refuses data-dependent commands when the warehouse is missing rather than creating an empty file. It does not print credentials.

The wrapper coordinates existing tools; use dbt, DLT, and Astro native commands when debugging their internals.
