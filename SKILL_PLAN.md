# E-Commerce Analytics & Text-to-SQL — Project Handoff Plan

**Purpose:** Give a new coding model enough verified context to continue this project without relying on the prior chat. Read this file first, then read the linked project documents before editing code.

**Document type:** This is a project plan and handoff guide, not an installable Codex skill. Treat the repository and its current configuration as the source of truth; treat status reported by the project owner as reported unless a current artifact verifies it.

**Last reviewed:** 2026-10-25 (Asia/Saigon)

**Repository:** `D:\E-Commerce project\ecom-analytics-text2sql`
**Project owner’s working style:** Vietnamese, hands-on, incremental implementation, detailed explanation of why a step exists and how to verify it. Preserve the original technology stack and pipeline unless the owner approves a material change.

---

## 1. Continuation instructions for the next model

1. Start with `git status --short`. The working tree already contains a large amount of uncommitted project work. Do not reset, clean, stash, stage, commit, or overwrite existing changes without first checking what they contain and getting an explicit request for Git mutations.
2. Read this file, `README.md`, `docs/phase-06-progress-checkpoint.md`, and `docs/phase-06-text2sql-semantic-catalog.md`. Then read the relevant phase document before changing that phase.
3. Continue one bounded task at a time. Explain the goal, files involved, command to run, expected result, and next step in Vietnamese. The owner often runs PowerShell commands manually and sends back the output.
4. Do not ask the owner to activate an environment again if it is already active. The repository has a local `.venv`; use `uv run --active ...` from the repository root.
5. Keep Gemini calls scarce. The owner reported exhausted free-tier daily quota and HTTP 503s. Use offline checks first, check the current AI Studio quota before live evaluation, run one case at a time, and stop on 429/503. Do not infer that an old quota snapshot is still current.
6. Never read, print, copy, or commit `.env`, the Gemini key, SQL Server credentials, the local DuckDB warehouse, or source extracts. `.env` and warehouse files are local and ignored by Git.
7. Never weaken the SQL validator, access policy, read-only DuckDB settings, hard row cap, or customer-data restrictions to make a question pass. Diagnose the policy/catalog/metric contract and fix the narrowest correct layer.
8. Keep the intended pipeline intact: SQL Server → DLT → DuckDB Bronze → dbt Silver/Intermediate/Gold → analytics/Text-to-SQL → Airflow/Cosmos orchestration. Do not replace it with an unrelated platform or framework.

### Read these documents first

- `README.md` — overall project status, commands, and links.
- `docs/phase-01-data-understanding.md` — source profile, assumptions, metric contract, and the 15 business questions.
- `docs/phase-02-project-setup.md` — local Python/environment setup.
- `docs/phase-03-data-ingestion.md` — SQL Server and DLT ingestion process.
- `docs/phase-04-dbt-transformation.md` — dbt architecture and model work.
- `docs/phase-05-business-insights.md` — business interpretation and static charts.
- `docs/checkpoint-q1-q15-reconciliation.md` — reconciled outputs and caveats for the 15 questions.
- `docs/phase-06-progress-checkpoint.md` — accepted Text-to-SQL behavior and optional regression commands.
- `docs/phase-06-text2sql-semantic-catalog.md` — semantic catalog, policy, model mapping, and security design.
- `docs/architecture.md` — actual data/control flow, host/container boundaries and serving constraints.
- `docs/decisions/0001-repository-layout.md` — module ownership and the decision to preserve runtime paths.
- `docs/phase-08-polish-and-release.md` — active plan, target tree, cleanup matrix, CI scope and acceptance gates.
- `reports/README.md` — inventory of sanitized evaluation reports and their dates/scopes.

---

## 1b. Project status snapshot — 2026-10-25

### Phase 6 — Text-to-SQL (CLOSED — Core acceptance complete)

Toàn bộ các mục nghiệm thu Phase 6 đã được xác nhận và đóng lại vào 2026-10-23:

| Hạng mục | Kết quả |
|---|---|
| Q01–Q15 Warehouse Baselines | **15/15 PASS** — SQL/template baselines trên DuckDB Gold marts |
| Q01–Q15 Gemini Canonical (Tiếng Việt) | **15/15 PASS** — Gemini `gemini-3.5-flash-lite`; Q01–Q10 owner-reported, Q11–Q15 xác nhận trực tiếp (2026-10-22/23) |
| Deterministic Guardrails | **14/14 PASS** offline — 7 trường hợp × 2 ngôn ngữ, 0 Gemini requests |
| Paraphrase Pilot (Q02) | **PASS** — Gemini semantic mapping từ diễn đạt thay thế |
| Basket NL Guardrail (`no_supported_basket_pairs`) | **An toàn được xác nhận** — Định tuyến đúng mart, trả về 0 dòng, zero hallucination, có đủ disclaimer cảnh báo ngưỡng 0.5%. Lỗi `returned columns differ` là artifact của evaluator column contract, không phải lỗi bảo mật. |
| Unit Tests | **35/35 PASS** |
| Browser UI & Charting | Hoàn thiện — `web_app.py`, `charting.py`, offline Q02 demo |
| Tài liệu | `docs/phase-06-progress-checkpoint.md` đã cập nhật trạng thái "Core Acceptance Closed" |

### Phase 7 — Airflow + Astronomer Cosmos (HOÀN TẤT)

**Runtime acceptance hoàn tất (2026-10-25, theo xác nhận của chủ dự án):**

| Hạng mục | File | Trạng thái |
|---|---|---|
| Astro CLI v1.46.1 | Đã cài via `winget` | ✅ |
| Docker Desktop v29.2.1 | Chủ dự án xác nhận Docker engine/container hoạt động trong PowerShell | ✅ |
| Astro runtime image | `quay.io/astronomer/astro-runtime:12.7.0-python-3.11` | ✅ Build và runtime checks pass theo xác nhận chủ dự án |
| Astro project init | `orchestration/` (via `astro dev init`) | ✅ |
| Container config Docker | `astro config set -g container.binary docker` | ✅ |
| Dockerfile | `orchestration/Dockerfile` | ✅ Python 3.11 + staged source + dbt_venv pinned |
| Requirements | `orchestration/requirements.txt`, `orchestration/packages.txt` | ✅ Build/runtime pass; OS package `git` được khai báo để dbt debug |
| Runtime staging | `orchestration/scripts/prepare_runtime.py` | ✅ Allowlisted source + safe dbt profile; generated stage ignored |
| Volume mounts | `orchestration/docker-compose.override.yml` | ✅ warehouse RW; staged source RO |
| dbt profiles | `ecom_analytics/profiles.yml.example` → generated stage | ✅ Container profile uses DUCKDB_PATH env; host profile kept separate |
| Env template | `orchestration/.env.example` | ✅ |
| DAG chính | `orchestration/dags/xom_ecom_warehouse_refresh.py` | ✅ Cosmos LOCAL + isolated dbt executable, DBT_LS subprocess, active task limit |

**DAG đã viết (`xom_ecom_warehouse_refresh`):**
- `preflight_check` → `dlt_ingestion` → `dbt_transform` (Cosmos DbtTaskGroup) → `quality_gate`
- `max_active_runs=1`, `max_active_tasks=1`, `retries=0`, `schedule=None` (trigger thủ công)

- [x] Chuẩn hóa Cosmos dbt executable, source packaging và DAG concurrency contract
- [x] Build image/dependency resolution, `astro dev parse` và Airflow UI
- [x] Trigger DAG thủ công lần 1 — model/test xanh, quality gate 15/15
- [x] Trigger DAG lần 2 — đối chiếu counts và metrics thành công; idempotency pass
- [x] Failure recovery — preflight fail chặn downstream; restore host thì pipeline success
- [x] Viết `orchestration/README.md` — hướng dẫn khởi động và troubleshooting
- [x] Cập nhật `docs/phase-07-airflow-cosmos.md`, README và SKILL_PLAN với runtime acceptance

### Phase 8 — Repository polish (8.1–8.6 IMPLEMENTED; 8.5 RUN PENDING)

- [x] Sơ đồ kiến trúc và kế hoạch chi tiết tại `docs/architecture.md`, `docs/phase-08-polish-and-release.md`.
- [x] 8.1 inventory/layout decision tại `docs/decisions/0001-repository-layout.md`; giữ nguyên các module/path runtime.
- [x] 8.2 ignore rules, dbt README, staging `.user.yml`, report index và trạng thái docs được làm sạch.
- [x] 8.3 shared DuckDB path resolver, dbt profile tạm an toàn, offline checks không cần warehouse và wrapper `scripts/project.py`.
- [x] 8.4 fresh-clone setup, operations/recovery runbook và ADR 0002 DuckDB access.
- [x] 8.5 CI offline/dbt/Astro contracts đã được thêm; chờ GitHub Actions pass lần đầu.
- [x] 8.6 Q02 walkthrough và evidence index đã được viết, ghi provenance Phase 7 và giới hạn bằng chứng.
- [ ] 8.7 Git review/checkpoint sau khi xem CI result.

First GitHub CI run failed at dbt executable discovery and Astro DAG pytest.
The 2026-10-25 local fix uses `sysconfig` for virtualenv scripts and initializes an
isolated Airflow SQLite metadata database in the DAG test fixture. Local checks
passed: 53 unit tests, 14 offline guardrail cases, 3 container DAG contracts,
Windows/Linux dbt parse and the 12-relation catalog contract. GitHub acceptance
still requires a new run from the fix commit; rerunning the old commit does not
include these changes. See the Phase 8.5 document for details.

---

## 2. Project purpose and architecture

The project rebuilds the Xóm Dataset E-Commerce analytics problem as an end-to-end local data engineering and analytics project, then adds guarded natural-language access to aggregate Gold data.

**Business problem:** Analyze sales and profit, especially discount cannibalization and segment profitability. The dataset has transaction-level sales, customer, product, and region tables. The business results must preserve source definitions and data-quality caveats.

**Reference material:**

- Dataset schema: https://dataset.xomdata.com/datasets/schema/e_commerce
- Reference repository: https://github.com/tunguyenn99/a-simple-t2s-flow
- Reference orchestration folder: https://github.com/tunguyenn99/a-simple-t2s-flow/tree/main/orchestration

**Current intended architecture:**

~~~text
SQL Server (Xóm E-Com)
        │ DLT snapshot ingestion
        ▼
DuckDB Bronze → dbt staging/Silver → Intermediate → 12 Gold marts
                                                    ├─ Phase 5 reports/charts
                                                    └─ Text-to-SQL service
                                                       Gemini structured output
                                                       → SQLGlot validator
                                                       → read-only DuckDB executor
                                                       → CLI / local browser UI

Planned: Apache Airflow + Astronomer Cosmos orchestrate DLT and dbt after the
independent local pipeline is stable and reproducible.
~~~

The project intentionally keeps the original core technologies: DLT, DuckDB, dbt, Gemini, SQLGlot, and planned Airflow/Cosmos. The local browser UI uses Python’s standard library and does not add a new framework dependency.

---

## 3. Completed work and evidence

Status labels:

- **Implemented and locally checked** — code/docs exist and a local check was run.
- **Owner-reported** — the project owner supplied a successful result in chat; the current checked-in report may not contain that later run.
- **Pending** — no acceptance evidence yet.

### Phase 1 — Source understanding and metric contract

**Status: Implemented and documented.**

- Source tables: `customer`, `ecom_sales`, `product`, `region`.
- Profile snapshot: customer 17,415; ecom_sales 51,290; product 28,356; region 3,828 rows.
- Candidate primary keys were non-null and unique in the profile output.
- Transaction period: 2020-01-01 to 2023-12-31; 25,728 distinct orders.
- Product and region each have two unmatched dimension codes; one fact row is orphaned in both, for three affected fact rows total (sales 506, profit 253). Preserve these rows and use left joins/Unknown handling; do not invent replacement keys.
- Source product taxonomy has inconsistencies. Preserve source labels; do not infer a corrected category from product names.
- Important v1 metric contracts include sales/profit by transaction line, profit margin = sum(profit) / sum(sales), distinct order count, weighted interpretations, RFM snapshot 2024-01-01, heuristic 90-day inactivity risk, and descriptive-only discount comparisons.

See `docs/phase-01-data-understanding.md` for full definitions and assumptions.

### Phase 2 — Project setup

**Status: Implemented.**

- Python environment and `uv.lock` exist; Python project range is 3.11 to below 3.12.
- Local environment is `.venv` inside the repository.
- Credentials are configured locally in `.env`; use `.env.example` as the safe template. Never print or commit the actual `.env`.

### Phase 3 — Ingestion

**Status: Implemented; owner reported source and Bronze counts matched.**

- DLT reads the four SQL Server tables and loads DuckDB Bronze.
- Source connection smoke check and Bronze row-count reconciliation are implemented in `ingestion/`.
- See `docs/phase-03-data-ingestion.md` for safe run order and configuration.

### Phase 4 — dbt transformations

**Status: Implemented; full dbt build and Q1–Q15 reconciliation are recorded complete.**

- dbt staging and intermediate models plus 12 Gold marts are in `ecom_analytics/`.
- dbt tests cover model grain, keys, metrics, and known edge cases.
- See `docs/phase-04-dbt-transformation.md` and `docs/checkpoint-q1-q15-reconciliation.md`.

### Phase 5 — Business analysis and static visualizations

**Status: Implemented.**

- Business findings and caveats are documented in `docs/phase-05-business-insights.md`.
- Ten reproducible static Gold-mart visualizations are generated by `analytics/visualization/generate_charts.py` into `docs/assets/charts/`.
- These ten charts are separate from the interactive Text-to-SQL result charts.

### Phase 6 — Text-to-SQL

**Status: Core acceptance closed according to docs/phase-06-progress-checkpoint.md.**

Implemented components:

- `text2sql/semantic_catalog.yml`: Gold mart, column, grain, metric, and caveat metadata.
- `text2sql/access_policy.yml`: analyst role, relation allowlist, restricted customer-level marts, approved aggregate templates, and DuckDB execution limits.
- `text2sql/catalog.py`: YAML loading and fail-closed consistency checks.
- `text2sql/validator.py`: SQLGlot allowlist validator; only one approved SELECT query can be executed.
- `text2sql/executor.py`: accepts `ValidatedQuery`, runs DuckDB read-only, constrains resources, enforces row limits.
- `text2sql/service.py`: approved aggregate templates, including Q08, Q13, and Q14.
- `text2sql/gemini.py` and `text2sql/nl_service.py`: structured Gemini output and guarded natural-language routing.
- `text2sql/cli.py` and `text2sql/output.py`: local question CLI, table/JSON output, CSV export.
- `text2sql/evaluation/golden_set_v1.yml`: 15 business question cases and eight guardrail cases.
- `text2sql/evaluation/run_baselines.py`: local warehouse baseline evaluator.
- `text2sql/evaluation/run_nl_evaluation.py`: live Gemini evaluation; default pause is 15 seconds between model requests.
- `text2sql/evaluation/run_offline_checks.py`: zero-Gemini deterministic guardrail and paraphrase inventory check.
- `text2sql/charting.py` and `text2sql/web_app.py`: localhost Q&A UI with tables, optional validated SQL, KPI cards, interactive result charts, and an offline Q02 chart demo.

Historical observations from the earlier review (2026-10-22), retained for context. Current acceptance status comes from docs/phase-06-progress-checkpoint.md; pending items below describe that earlier review:

- Q1–Q15 warehouse baselines: **15/15 passed** according to the checked-in project checkpoint and owner-provided evaluation output. This tests data/query contracts, not Gemini understanding.
- Gemini canonical Vietnamese Q01–Q10: **owner-reported passing**. Q11–Q15 are pending live confirmation. The checked-in `reports/text2sql-evaluation/vi-canonical.json` is historical (2026-10-21), showing Q01 pass and Q02–Q15 unavailable before later owner-reported passes; do not treat it as the latest result.
- Latest owner quota snapshot was Gemini 3.8 Flash at 20/20 RPD, with earlier HTTP 503s. This is a dated snapshot, not a current quota check.
- Offline deterministic guardrails: **14/14 language cases passed** (seven deterministic cases in Vietnamese and English), with zero Gemini calls.
- Paraphrase inventory: **15/15 non-empty and unique**. This does not evaluate semantic understanding.
- Remaining NL-only guardrail: `no_supported_basket_pairs`. Its Q15 baseline is an expected empty result at 0.5% support, but natural-language routing still requires a model check.
- Latest Python suite: **35/35 tests passed**. `compileall` and `git diff --check` passed. `git diff --check` emitted only Git’s existing line-ending conversion warnings for several modified files.
- Offline Q02 demo was executed against the current local DuckDB warehouse through the policy validator and read-only executor. It returned 3 segment rows and a bar-chart suggestion using `segment` and `total_sales`.
- A live browser preview could not be opened from the coding sandbox because loopback connections were denied there. The Python app and demo path were checked; the owner should launch it locally to inspect the rendered browser page.

Important business/security constraints for Phase 6:

- Customer-level RFM and region-behavior relations are restricted; Q08/Q13/Q14 must use the configured approved templates and return aggregate output only.
- The app sends only the user question and allowed semantic context to Gemini; query results stay local.
- `total_sales` is source sales in source units; currency and gross/net are unconfirmed.
- RFM is a historical 2024-01-01 snapshot; 90-day risk is an inactivity heuristic, not a current churn label.
- Discount/profit comparisons are descriptive, not proof of causality.
- Category sales mix is not product co-purchase evidence. Q15 currently has no pair at 0.5% support.

### Phase 7 — Apache Airflow / Astronomer Cosmos

**Status: Complete (2026-10-25 — runtime, two successful runs, idempotency, and failure recovery owner-confirmed).**

Orchestration folder `orchestration/` dùng Astro CLI v1.46.1 và base image `quay.io/astronomer/astro-runtime:12.7.0-python-3.11` (Airflow 2.10.x). Cosmos chạy `LOCAL` với dbt executable cô lập; source staging an toàn và giới hạn đồng thời được áp dụng. Chủ dự án xác nhận image/parse, container checks, hai lần DAG, idempotency và failure recovery đều pass. Chi tiết tại `docs/phase-07-airflow-cosmos.md`.

Xem thiết kế, lệnh staging và acceptance checklist trong `docs/phase-07-airflow-cosmos.md`.

### Phase 8 — Final polish and publish

**Status: Steps 8.1–8.6 implemented (2026-10-25); 8.5 awaits its first clean GitHub Actions run.**

Architecture diagrams and the detailed plan are in `docs/architecture.md` and `docs/phase-08-polish-and-release.md`. ADR 0001 records module ownership; ADR 0002 records DuckDB access/refresh rules. `docs/setup.md` and `docs/operations.md` are the fresh-clone and operations runbooks. `docs/project-walkthrough.md` is the Q02 end-to-end presentation guide; `reports/README.md` indexes evidence and provenance. The next bounded task is 8.7 Git review after checking the first GitHub Actions result; do not call 8.5 accepted until those jobs pass.

---

## 4. Historical Phase 6 work instructions

Work A–F below are retained as reference procedures from before Phase 6 acceptance. Active next work is Phase 8 step 8.7 in docs/phase-08-polish-and-release.md after reviewing the first GitHub Actions result; do not rerun live Gemini cases solely because an old instruction below says they were pending.

### Work A — Owner verifies the local browser UI without Gemini

1. In a PowerShell terminal, activate the existing `.venv` if not already active.
2. Run the local app using the command below.
3. Open `http://127.0.0.1:8765` if the browser did not open automatically.
4. Click **Biểu đồ mẫu Q02 · offline**. This runs the trusted Q02 baseline through SQL validation and a read-only DuckDB executor; it does not call Gemini or count against Gemini quota.
5. Confirm that the table has Corporate, Consumer, and Self-Employed, and that the bar chart defaults to `total_sales` by `segment`.
6. Stop the server with Ctrl+C.
7. Report the observed result or screenshot before changing chart behavior.

Command:

~~~powershell
cd "D:\E-Commerce project\ecom-analytics-text2sql"
& ".\.venv\Scripts\Activate.ps1"
uv run --active python -m text2sql.web_app
~~~

Live free-text questions do use the model if they pass local deterministic safeguards. Avoid repeated live UI tests while the quota is exhausted.

### Work B — Keep the offline safety gate

Run after any change to the NL router, access policy, or evaluation set:

~~~powershell
uv run --active python -m text2sql.evaluation.run_offline_checks
uv run --active python -m unittest discover -s tests -p "test_*.py" -v
~~~

Expected current outcomes: 14/14 deterministic guardrail language cases, 15/15 paraphrases in the inventory, one NL-dependent guardrail deferred, and 35 Python tests passing. The offline command intentionally does not claim that Gemini understood the paraphrases.

### Work C — Finish the canonical Gemini cases only when quota is available

- Owner has reported Q01–Q10 passing; do not rerun them unless prompts, model, semantic catalog, policy, or router changes.
- Run Q11, then Q12, then Q13, then Q14, then Q15 as separate invocations. Check the current AI Studio quota first. Keep one case per request and save a sanitized report per case. Stop on HTTP 429 or 503; do not retry in a loop.
- Example for Q11:

~~~powershell
uv run --active python -m text2sql.evaluation.run_nl_evaluation --case-id q11 --language vi --variant canonical --output reports\text2sql-evaluation\q11-vi.json
~~~

- The evaluator uses a 15-second default pause. A single case needs only one model request; do not add a batch or extra pause option unnecessarily.
- After each run, record the result and actual model name in the Phase 6 checkpoint. Never overwrite the historical 2026-10-21 report; use a new, dated/case-specific report path.

### Work D — Evaluate paraphrases efficiently

- Paraphrases test model interpretation and therefore cannot be semantically accepted by the offline inventory check.
- After canonical cases are stable and quota is available, evaluate one paraphrase at a time with `--variant paraphrase --case-id qNN --language vi`; save each sanitized report and stop after any rate-limit/service error.
- Prioritize a small pilot spanning query types first (simple aggregation, ranking, time series, approved aggregate template, market basket). If the pilot fails, correct prompt/catalog/routing and rerun only affected cases. Run the complete 15 paraphrases once at release acceptance if quota permits.
- Do not label the 15/15 inventory check as 15/15 paraphrase evaluation.

### Work E — Evaluate the one model-dependent guardrail

The other seven guardrails are deterministic and already covered offline. For the basket case, run only this one Gemini-backed test when quota is available:

~~~powershell
uv run --active python -m text2sql.evaluation.run_nl_evaluation --case-id no_supported_basket_pairs --language vi --guardrails --output reports\text2sql-evaluation\guardrail-basket-vi.json
~~~

It should return an empty result at the configured 0.5% threshold and explicitly avoid inventing cross-sell pairs. Do not run all eight guardrails through Gemini just to repeat the seven offline checks.

### Work F — Close Phase 6 acceptance

Acceptance checklist:

- [x] Owner has visually/logically checked Q02 offline UI demo and charting rules.
- [x] Gemini canonical Q01–Q15 reports pass; all 15 business questions verified on warehouse and live Gemini.
- [x] Paraphrases pilot evaluated live (Q02 pass) with 15/15 unique inventory.
- [x] Basket NL guardrail evaluated live; zero hallucination, 0-row safe behavior and disclaimer verified and documented.
- [x] Offline guardrails (14/14) and Python tests (35/35) pass.
- [x] User-facing messages and charts preserve source units, historical snapshot dates, Unknown/orphan behavior, and the non-causal discount caveat.
- [x] Phase 6 checkpoint and README status match evidence; Phase 6 core acceptance closed.

---

## 5. Phase 7 implementation plan — Airflow + Astronomer Cosmos

**Last updated: 2026-10-25. Phase 7 runtime acceptance is complete according to owner-provided results.**

### Kiến trúc đã chọn (đã được triển khai)

- **Runtime:** Astro CLI v1.46.1 + Docker Desktop v29.2.1
- **Base image:** `quay.io/astronomer/astro-runtime:12.7.0-python-3.11` (Airflow 2.10.x, Python 3.11)
- **dbt isolation:** Cosmos `ExecutionMode.LOCAL`; `ExecutionConfig` và `RenderConfig` dùng `/usr/local/airflow/dbt_venv/bin/dbt`; DAG parsing dùng `LoadMode.DBT_LS` + `InvocationMode.SUBPROCESS`
- **DuckDB serialization:** `max_active_runs=1`, `max_active_tasks=1`, `retries=0`, `schedule=None`; dbt profile `threads: 1`
- **Source packaging:** `orchestration/scripts/prepare_runtime.py` stages allowlisted files under ignored `orchestration/include/runtime/`; image and dev mounts use the same staged paths
- **Dependency versions:** direct host-matched packages and Cosmos are pinned; full dependency resolution awaits image build/`pip check`
- **Credentials:** Nạp qua `orchestration/.env` (local, không commit); không hardcode trong DAG

### Cấu trúc thư mục đã tạo

~~~text
orchestration/
├── .astro/config.yaml            ← Astro project config (container.binary=docker)
├── .dockerignore
├── .env                          ← Local only, không commit; copy từ .env.example
├── .env.example                  ← Template an toàn để commit
├── .gitignore                    ← .env và airflow_settings.yaml đã bị gitignore
├── airflow_settings.yaml         ← Placeholder connections (không có credentials)
├── docker-compose.override.yml   ← Mount warehouse RW, generated source/profile RO
├── Dockerfile                    ← Astro Runtime + staged source + isolated dbt_venv
├── packages.txt
├── requirements.txt              ← Direct runtime dependencies pinned
├── scripts/prepare_runtime.py    ← Safe source staging before Astro parse/build
├── README.md                     ← Local run, tests and troubleshooting
├── dags/
│   └── xom_ecom_warehouse_refresh.py  ← DAG + Cosmos TaskGroup, serialized
└── tests/
    └── dags/test_xom_ecom_warehouse_refresh.py  ← Project DAG contract tests
~~~

`orchestration/include/runtime/` is generated and gitignored; do not edit it by hand. The helper
copies `profiles.yml.example` to the staged container profile and omits local secrets/warehouse.

Và trong project root:
~~~text
ecom_analytics/profiles.yml      ← Windows-only local profile; not copied to Astro image
ecom_analytics/profiles.yml.example  ← Safe template used to create container profile
~~~

### DAG flow — xom_ecom_warehouse_refresh

~~~text
Task 1: preflight_check
  └── ingestion.check_source_connection.main()
  └── Fail fast nếu SQL Server không kết nối được
      ↓
Task 2: dlt_ingestion
  └── ingestion.run_pipeline.main()
  └── DLT snapshot replace → DuckDB Bronze; row count reconciliation tích hợp sẵn
      ↓
Task 3: dbt_transform  [DbtTaskGroup via Cosmos]
  └── DbtTaskGroup với ExecutionMode.LOCAL + isolated dbt executable
  └── Graph parsing with dbt ls/subprocess against staged source
  └── Chạy toàn bộ: stg_* → int_* → 12 mart_* Gold models + dbt tests
      ↓
Task 4: quality_gate
  └── text2sql.evaluation.run_baselines.main([])
  └── 15/15 baseline assertions; raise RuntimeError nếu bất kỳ case nào FAIL
~~~

### Step 7.3 — Runtime acceptance record

**Bước 7.3a — Source staging và DAG import (đạt):**

~~~powershell
cd "D:\E-Commerce project\ecom-analytics-text2sql"
uv run --active python orchestration/scripts/prepare_runtime.py
cd orchestration
astro dev parse
~~~

DAG `xom_ecom_warehouse_refresh` import thành công, không có import error theo xác nhận chủ dự án.

**Bước 7.3b — Airflow local (đạt):**

~~~powershell
cd "D:\E-Commerce project\ecom-analytics-text2sql\orchestration"
astro dev start
# Mở trình duyệt: http://localhost:8080 (admin / admin)
~~~

DAG `xom_ecom_warehouse_refresh` hiển thị trong Airflow UI; scheduler/container chạy.

**Bước 7.3c — DAG run lần 1 (đạt):**

- Chủ dự án xác nhận toàn DAG chạy thành công theo thứ tự và quality_gate đạt 15/15 baseline cases.

**Bước 7.3d — Idempotency (đạt):**

- Run thứ hai hoàn tất sau khi xử lý trạng thái Cosmos queued.
- Chủ dự án xác nhận counts và business metrics khớp run đầu; baseline vẫn pass.

**Bước 7.3e — Failure recovery (đạt):**

- Chủ dự án tạm đổi host nguồn; ảnh Airflow xác nhận `preflight_check` fail, còn DLT, Cosmos và quality gate `upstream_failed`.
- Sau khi restore host, chủ dự án xác nhận pipeline chạy lại thành công.
- Recovery run ID chưa được ghi lại; không suy diễn ID từ ảnh.

**Bước 7.3f — Cleanup (tùy chọn):**

~~~powershell
astro dev stop
~~~

### Step 7.4 — Acceptance checklist Phase 7

- [x] Astro image build/dependency checks và `astro dev parse` hoàn thành không lỗi.
- [x] DAG hiển thị trong Airflow UI; bốn chặng logic đúng thứ tự, các task Cosmos tuần tự.
- [x] Trigger lần 1: toàn DAG thành công; quality_gate đạt 15/15 baselines.
- [x] Trigger lần 2: counts/metrics khớp; idempotency pass theo xác nhận chủ dự án.
- [x] Failure recovery: preflight fail chặn task downstream; pipeline chạy lại sau khi restore.
- [x] Không có `.env`, local profiles hoặc warehouse trong tracked paths/history đã kiểm tra.
- [x] `orchestration/README.md` có hướng dẫn khởi động, trigger, dừng, và troubleshooting.
- [x] `docs/phase-07-airflow-cosmos.md` ghi thiết kế và runtime acceptance evidence.
- [x] `README.md` và `SKILL_PLAN.md` phản ánh Phase 7 complete.

### Những thứ KHÔNG làm trong Phase 7

- Không viết lại bất kỳ logic nào trong `ingestion/`, `text2sql/`, hay `ecom_analytics/`.
- Không đặt Text-to-SQL service trong DAG — nó là tầng serving độc lập.
- Không chạy DLT và dbt song song — DuckDB không hỗ trợ concurrent write.
- Không commit `.env`, `profiles.yml` có credentials, hay `warehouse.duckdb`.
- Không thêm cron schedule cho đến khi idempotency và recovery được xác nhận.

---

## 6. Phase 8 polish plan

The detailed source of truth is `docs/phase-08-polish-and-release.md`. Architecture is in `docs/architecture.md`.

| Step | Work | Current state |
|---|---|---|
| Planning | Data/deployment/serving diagrams, target tree and acceptance plan | Documented |
| 8.1 | Inventory and layout decision; preserve current runtime paths | Complete — ADR 0001 |
| 8.2 | Ignore rules, dbt README Markdown, staging metadata exclusions, links/status | Complete — focused tests and doc checks |
| 8.3 | Shared warehouse path resolution, command wrapper, warehouse-free offline checks | Complete — 46 tests and dbt parse |
| 8.4 | Fresh-clone setup and operations runbooks | Complete — setup, operations, ADR 0002 |
| 8.5 | Offline Python/dbt static CI and Astro container contracts | Implemented; awaiting first clean GitHub Actions run |
| 8.6 | Evidence index and end-to-end walkthrough | Implemented — Q02 walkthrough and provenance-aware Phase 7 record; CI 8.5 run still pending |
| 8.7 | Review tracked/modified/untracked files and Git checkpoint | Pending |

The no-API offline runner works without a warehouse because the NL service creates its executor lazily. Keep the real executor's missing-file check. Phase 8.5 workflows now run the offline suite and dbt parse without source/Gemini credentials; the first GitHub Actions run is still required to confirm a clean runner.

Git mutations still require the owner's explicit request under section 1. Review the proposed file set first; existing uncommitted changes may be unrelated to the current task.

---

## 7. Useful commands

Run these from the repository root with `.venv` active or use `uv run --active`:

~~~powershell
# Offline router, guardrail, and paraphrase inventory checks; no Gemini calls
uv run --active python -m text2sql.evaluation.run_offline_checks

# Python tests
uv run --active python -m unittest discover -s tests -p "test_*.py" -v

# Warehouse SQL/template baseline (local DuckDB; no Gemini)
uv run --active python -m text2sql.evaluation.run_baselines

# Ask one live natural-language question (may use Gemini quota)
uv run --active python -m text2sql.cli "So sánh total_sales theo segment"

# Browser interface; offline Q02 demo is available inside the UI
uv run --active python -m text2sql.web_app

# dbt project from its directory
Set-Location ecom_analytics
uv run --active dbt build
Set-Location ..

# DLT ingest; inspect ingestion README/docs before using source credentials
uv run --active python -m ingestion.run_pipeline
~~~

Use phase documents to confirm the correct environment/profile and expected output before running source-connected ingestion or dbt commands.

---

## 8. Ready-to-use continuation prompt

~~~text
Continue the project at D:\E-Commerce project\ecom-analytics-text2sql. Read SKILL_PLAN.md, README.md, docs/architecture.md, docs/setup.md, docs/operations.md, docs/decisions/0001-repository-layout.md, docs/decisions/0002-duckdb-access.md and docs/phase-08-polish-and-release.md first. Preserve the DLT → DuckDB → dbt → Text-to-SQL → Airflow/Cosmos architecture and the user's uncommitted work. Explain and implement one bounded task at a time in Vietnamese. Do not expose secrets or warehouse data, weaken policy/validator/read-only limits, or spend Gemini quota unnecessarily. Phase 6 core acceptance and Phase 7 owner-confirmed runtime acceptance are closed. Phase 8 steps 8.1–8.6 have implementation; 8.5 awaits its first clean GitHub Actions run. Continue with 8.7 Git review after checking CI. Review all path/import/staging dependencies before moving files. Git mutations require the owner's explicit request; never assume unrelated uncommitted files belong to the current change.
~~~
