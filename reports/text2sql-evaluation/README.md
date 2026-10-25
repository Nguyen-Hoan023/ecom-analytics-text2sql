# Text-to-SQL evaluation artifacts

This folder contains sanitized JSON outputs from selected natural-language evaluation runs.

## Artifact policy

- Preserve each run separately and do not overwrite older outcomes.
- Record model, evaluation-set version, timestamp, cases, language, and variant when available.
- Keep only case IDs, statuses, and sanitized pass/fail diagnostics.
- Do not store API keys, prompts, generated SQL, result rows, customer identifiers, or source extracts.
- Provider quota and availability change over time; these files are not quota dashboards.

Use a new descriptive path such as <code>YYYY-MM-DD-canonical-vi-q01-q05.json</code> for new output. The NL evaluator's <code>--output</code> option selects the file.

For suite semantics and commands see [Text-to-SQL evaluation](../../text2sql/evaluation/README.md).
