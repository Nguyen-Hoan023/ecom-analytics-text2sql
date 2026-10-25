# Phase 6 progress checkpoint

**Captured:** 2026-10-23 (Asia/Saigon).
**Status:** **Phase 6 Core Acceptance Closed.**
**Purpose:** Track Text-to-SQL implementation and Gemini evaluation separately from the Q1–Q15 warehouse reconciliation in [the business checkpoint](checkpoint-q1-q15-reconciliation.md).

## Final Phase 6 status

- **Warehouse baselines (Q01–Q15):** 15/15 passed against local DuckDB warehouse snapshot.
- **Gemini canonical Vietnamese cases (Q01–Q15):** **15/15 PASSED** live with `gemini-3.5-flash-lite`. Both direct single-table Gold queries and restricted customer-level policy templates (`q08_vip_risk_summary`, `q13_region_behavior_summary`, `q14_rfm_population_summary`) routed cleanly without exposing customer PII or raw customer grain.
- **Deterministic guardrails:** **14/14 passed offline** (7 safety/clarification scenarios tested in both Vietnamese and English) with zero Gemini requests.
- **Paraphrase testing:** Full 15/15 corpus is non-empty and unique. Pilot paraphrase test on `q02` passed live (`PASS q02 paraphrase_vi [answered]`), verifying semantic mapping from alternative user phrasings.
- **Model-dependent basket guardrail (`no_supported_basket_pairs`):** Verified live with Gemini. Core safety behaviors achieved: correctly routed to `mart_market_basket_associations`, returned 0 qualifying rows at 0.5% support, generated zero hallucinated co-purchase pairs, and produced the requisite business caveat (*"không có cặp sản phẩm nào đạt support tối thiểu 0,5%"*). The evaluator's note on column projection divergence against Q15 golden contract is documented as an expected result when free-form natural language does not explicitly request association metric columns.
- **Local browser UI & Charting:** Web app (`text2sql/web_app.py`) and deterministic chart suggestion (`text2sql/charting.py`) operational with table output, validated SQL view, KPI cards, interactive bar/line charts, and an offline Q02 demo path.
- **Test suite integrity:** 35/35 unit tests pass; `compileall` and offline checks pass.

## Phase 6 Acceptance Checklist

- [x] Local browser UI and offline Q02 demo path verified.
- [x] Gemini canonical Q01–Q15 reports verified pass (all 15 business questions).
- [x] Paraphrase pilot verified pass with 15/15 unique inventory.
- [x] Basket NL guardrail evaluated live; zero hallucination and safe 0-row behavior confirmed.
- [x] 14/14 offline guardrails and 35/35 Python unit tests passing.
- [x] Business caveats preserved (unconfirmed currency/sales units, 2024-01-01 historical snapshot, inactivity heuristic, non-causal discount comparison).
- [x] Phase 6 formally accepted; Phase 7 runtime acceptance is recorded in [the orchestration checkpoint](phase-07-airflow-cosmos.md).

## Next project phase — repository polish

Phase 7 orchestration is complete according to the owner-confirmed acceptance in
[`phase-07-airflow-cosmos.md`](phase-07-airflow-cosmos.md). The active work is
Phase 8: repository layout, local/generated-file hygiene, reproducible commands,
setup/runbooks, CI, and a project walkthrough. See the [Phase 8 plan](phase-08-polish-and-release.md).

## Reproducible commands

Show a result as a table (default):

```powershell
uv run --active python -m text2sql.cli "Top 10 best-selling products"
```

Request JSON or export a result to a new CSV file:

```powershell
uv run --active python -m text2sql.cli --output-format json "Top 10 best-selling products"
uv run --active python -m text2sql.cli --export-csv reports\text2sql-evaluation\top-products.csv "Top 10 best-selling products"
```

Optional live regression example: rerun only a case affected by a prompt, model,
or routing change. Phase 6 canonical acceptance is closed; this is not a pending
case. Check current AI Studio quota before sending a request:

```powershell
uv run --active python -m text2sql.evaluation.run_nl_evaluation --case-id q11 --language vi --variant canonical --output reports\text2sql-evaluation\q11-vi-regression.json
```

Run deterministic guardrails and paraphrase-corpus checks without a Gemini request:

```powershell
uv run --active python -m text2sql.evaluation.run_offline_checks
```

Start the interactive local question-and-chart interface:

```powershell
uv run --active python -m text2sql.web_app
```

Press `Ctrl+C` in the terminal to stop the server.
