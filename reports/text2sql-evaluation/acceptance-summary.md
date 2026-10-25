# Text-to-SQL acceptance summary

**Record updated:** 2026-10-25
**Scope:** Golden SQL/template baselines, selected Gemini natural-language evaluations, deterministic offline guardrails, and local UI behavior.

## Evidence and provenance

This summary consolidates user-confirmed command outputs and earlier project acceptance notes. A machine-generated JSON report for the complete passing canonical run was not retained; older JSON files remain historical failures/unavailable outcomes and are not rewritten.

## Recorded outcomes

| Suite/behavior | Recorded result | Interpretation |
|---|---|---|
| SQL/template warehouse baselines | 15/15 passed in the user-shared runner output. | Gold mart output contracts passed for the evaluated warehouse snapshot. |
| Canonical Vietnamese Gemini cases | 15/15 owner-confirmed in the project acceptance record. | This is a recorded historical acceptance, not a guarantee about current provider availability or a new run. |
| Deterministic offline guardrails | 14/14 language cases passed: seven deterministic behaviors in Vietnamese and English, with zero model calls. | Does not test semantic understanding by Gemini. |
| Paraphrase inventory | 15/15 non-empty and unique; at least one live paraphrase pilot was confirmed. | Inventory validation is not full semantic validation of all paraphrases. |
| Basket no-supported-pairs behavior | At 0.5% support the mart returns no qualifying pairs; the safe response preserves this result and includes a scope caveat. | Sparse lower-threshold pairs are exploratory and are not a recommendation-quality signal. |
| Local Text-to-SQL UI | Table, KPI cards, and supported result-shaped charts were confirmed. | Local single-user UI; not an authenticated shared deployment. |

## Safety contract

- Only approved Gold data is eligible for direct generated SQL.
- Restricted customer-level RFM and region marts use named aggregate templates; customer identifiers and raw customer-level rows are not sent to the model or returned.
- Generated SQL is parsed/validated with SQLGlot before a read-only, resource-limited DuckDB executor runs it.
- API failures such as unavailable/429/503 are failures to evaluate, not passes. Do not retry in a loop.
- Preserve failed/unavailable JSON artifacts; save future runs to a new date- and case-specific report path.

For current commands and suite boundaries, see [Text-to-SQL evaluation](../../text2sql/evaluation/README.md). This summary is not a current API quota reading.
