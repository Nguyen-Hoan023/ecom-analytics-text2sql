# Governed Text-to-SQL

This package turns English or Vietnamese business questions into bounded queries over approved Gold marts. The browser UI returns a result table, KPI cards, and a chart when the result shape supports one. Static executive charts are generated separately.

## Request lifecycle

Question → local checks → semantic catalog and policy context → Gemini structured decision → direct-SQL or approved-template path → SQLGlot validation → read-only DuckDB executor → bounded result → CLI/browser rendering.

Local checks can refuse a sensitive or destructive request or ask for clarification before an API call. If the request passes, Gemini must be configured; a missing key, provider/quota error, or invalid decision returns <code>unavailable</code> and does not execute SQL. The model output is untrusted until the application validates it. The executor accepts a <code>ValidatedQuery</code>, not raw SQL. The [main README's T2S section](../README.md) contains the request-flow diagram and step-by-step explanation.

## Responsibilities

| File | Responsibility |
|---|---|
| <code>catalog.py</code> | Load and validate catalog and policy YAML. |
| <code>semantic_catalog.yml</code> | Gold relations, exposed columns, metrics, language support, and caveats. |
| <code>access_policy.yml</code> | Role, allowlist, restricted templates, SQL rules, and resource limits. |
| <code>nl_service.py</code> | Clarification, refusal, model context construction, and routing. |
| <code>gemini.py</code> | Optional Gemini client and constrained decision parsing. |
| <code>validator.py</code> | SQLGlot AST checks and creation of the validated-query type. |
| <code>executor.py</code> | Read-only DuckDB connection, query limits, result cap, and revalidation. |
| <code>service.py</code> | Approved aggregate templates for restricted customer marts. |
| <code>cli.py</code>, <code>web_app.py</code> | Command-line and local browser interfaces. |
| <code>output.py</code>, <code>charting.py</code> | Bounded result formatting and deterministic chart suggestion. |

## Run locally

A populated warehouse is required. From the repository root:

    uv run --project . python -m text2sql.cli "Show total sales and profit by segment"
    uv run --project . python scripts/project.py ui

The UI defaults to <http://127.0.0.1:8765>. It is local and single-user; it has no authentication. Do not expose it to remote or untrusted users.

For live model generation, set <code>GEMINI_API_KEY</code> in the ignored root <code>.env</code>; optionally set <code>GEMINI_MODEL</code>. Offline routes and safety checks do not require the key.

## Security boundary

The policy allows only one SELECT statement over catalog-approved Gold relations. It rejects unapproved columns/functions, joins, CTEs, SELECT *, external access, and destructive operations. Restricted RFM and region marts are available only through approved aggregate templates. Demographic queries enforce a minimum group size.

DuckDB opens read-only, disables external access and extension loading, enforces a 10-second runtime, 2 threads, 1 GB memory/temp limits, and a 500-row hard cap. For shared deployment, add trusted identity, authorization, process/container isolation, network/filesystem controls, and application-enforced timeouts before exposing the service.

See [evaluation/README.md](evaluation/README.md) for quality suites and API-quota-aware evaluation.
