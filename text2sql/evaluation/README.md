# Text-to-SQL evaluation

The project separates warehouse correctness, deterministic safety, and model interpretation into independent evaluation lanes.

| Runner | Warehouse | Gemini | Purpose |
|---|---:|---:|---|
| <code>run_baselines</code> | Required | No | 15 SQL/template cases: relation, columns, grain, row count, and values. |
| <code>run_offline_checks</code> | Not required | No | Deterministic Vietnamese/English refusal, clarification, and paraphrase-inventory checks. |
| <code>run_nl_evaluation</code> | Required for answers | Yes | End-to-end natural-language routing, policy/template choice, and result contract. |

The versioned <code>golden_set_v1.yml</code> contains 15 business cases and 8 guardrail cases. The offline suite defers cases that require model semantics or an unimplemented route; it does not silently count deferred cases as passes.

## Commands

Offline, no API key or warehouse:

    uv run --project . python scripts/project.py offline-checks

Warehouse baseline after ingestion and dbt build:

    uv run --project . python -m text2sql.evaluation.run_baselines

One Gemini case:

    uv run --project . python -m text2sql.evaluation.run_nl_evaluation --case-id q01 --language vi --variant canonical

Use <code>--help</code> for other languages, paraphrases, guardrails, pacing, and sanitized JSON output. Start with a single case when quota is limited. Avoid rerunning all cases after code-only edits.

## Contract and evidence

Each analytical case specifies expected relation, columns, metrics, row count, and values. The loader checks that these contracts match the semantic catalog and policy before any model request. Baselines test warehouse outputs, not language understanding.

Use a new path for every JSON report. Reports contain sanitized case/status/assertion metadata only; never store prompts, API keys, generated SQL, result rows, customer identifiers, or source extracts. Provider quotas and availability are time-varying and are not project guarantees.
