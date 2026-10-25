# E-Commerce Analytics & Text-to-SQL

A learning project to rebuild an end-to-end analytics pipeline from the Xóm E-Com dataset, following the reference flow while documenting design choices and validating each layer.

## Project goals

- Answer the 15 business questions in the Xóm E-Com context with traceable, tested data models.
- Build the flow incrementally: SQL Server source → DLT ingestion → DuckDB → dbt Bronze/Silver/Gold → analytics and Text-to-SQL.
- Keep Astro/Airflow/Cosmos as the orchestration layer after the local data pipeline is validated.
- Treat the reference repository as a design reference; verify assumptions against the live source and explain changes.

## Current status

- **Phase 1 — Data understanding:** Hoàn tất source profile và metric contract v1. Đã ghi nhận các giả định nghiệp vụ, orphan keys và vấn đề taxonomy.
- **Phase 2 — Project setup:** Hoàn tất môi trường Python, dependency lockfile và cấu hình secrets qua `.env`.
- **Phase 3 — Ingestion:** DLT đã nạp snapshot từ SQL Server vào DuckDB Bronze. Row count của cả bốn bảng khớp nguồn.
- **Phase 4 — dbt transformation:** Hoàn tất Silver, Intermediate và 12 Gold marts, ánh xạ tới 15 câu hỏi nghiệp vụ. Full `dbt build` và đối soát Q1–Q15 đã hoàn tất ([checkpoint](docs/checkpoint-q1-q15-reconciliation.md)).
- **Phase 5 — Business analysis:** Hoàn tất báo cáo insight, giới hạn nghiệp vụ và bộ 10 biểu đồ tĩnh được sinh lại từ Gold marts.
- **Phase 6 — Text-to-SQL:** Hoàn tất toàn bộ core acceptance. Catalog/policy, SQLGlot validator fail-closed, read-only DuckDB executor, aggregate templates, Gemini structured-output adapter, natural-language service, CLI local và NL evaluation runner đã hoạt động. Toàn bộ Q01–Q15 canonical tiếng Việt đã PASS 100% với Gemini; pilot paraphrase Q02 đã PASS; 14/14 deterministic guardrails đã pass offline; guardrail giỏ hàng đã kiểm chứng an toàn 0 dòng và không hallucination. CLI hỗ trợ bảng, JSON, CSV; giao diện browser localhost hiển thị kết quả và biểu đồ tương tác ([checkpoint Phase 6](docs/phase-06-progress-checkpoint.md)).
- **Phase 7 — Airflow/Cosmos:** Hoàn tất runtime acceptance theo xác nhận của chủ dự án: image build/parse, container connectivity, hai DAG runs với idempotency, quality gate 15/15 và failure recovery đều pass ([checkpoint Phase 7](docs/phase-07-airflow-cosmos.md)).
- **Phase 8 — Polish and publish:** Đã hoàn tất inventory/layout, cleanup, DuckDB path/wrapper, setup/operations, CI configuration và walkthrough/evidence docs (8.1–8.6). CI 8.5 vẫn chờ lần chạy clean runner đầu tiên trên GitHub Actions; tiếp theo là review Git (8.7). Xem [walkthrough](docs/project-walkthrough.md), [evidence index](reports/README.md), [setup](docs/setup.md), [operations](docs/operations.md), [kế hoạch](docs/phase-08-polish-and-release.md) và [architecture](docs/architecture.md).

## Planned stages

| Stage | Outcome | Status |
|---|---|---|
| 1. Understand the source | Verified source profile and metric contract | Complete |
| 2. Set up the project | Reproducible Python environment and configuration | Complete |
| 3. Ingest with DLT | SQL Server snapshot loaded into DuckDB Bronze | Complete |
| 4. Transform with dbt | Silver, Intermediate and 12 Gold marts covering 15 questions; full `dbt build` passes | Complete |
| 5. Analyze business results | Validated insight report and reproducible Gold visualizations | Complete |
| 6. Add Text-to-SQL | Policy-guarded NL routing, structured Gemini output, SQL validation, read-only execution, aggregate templates, result formatting, Q1–Q15 golden evaluation | Complete |
| 7. Orchestrate with Airflow/Cosmos | Run and validate the pipeline through Airflow/Cosmos, including idempotency and failure recovery | Complete |
| 8. Polish and publish | Repository layout, reproducible setup, CI and project walkthrough | In progress |

## Architecture and delivery plan

The [architecture document](docs/architecture.md) maps the data flow, Windows/Docker runtime boundaries, and guarded Text-to-SQL path. Follow the [project walkthrough](docs/project-walkthrough.md) for an end-to-end Q02 demo and [evidence index](reports/README.md) for provenance/status. [Setup](docs/setup.md) covers a fresh clone; [operations](docs/operations.md) covers refresh and recovery. [ADR 0001](docs/decisions/0001-repository-layout.md) records module ownership; [ADR 0002](docs/decisions/0002-duckdb-access.md) records the DuckDB file access contract. The [Phase 8 plan](docs/phase-08-polish-and-release.md) tracks the pending clean CI run and Git review.

## Project commands

The wrapper resolves the repository root from its own file, so child tools use consistent paths regardless of the shell's current directory. From the repository root:

```powershell
uv run --active python scripts/project.py doctor
uv run --active python scripts/project.py dbt parse
uv run --active python scripts/project.py dbt build
uv run --active python scripts/project.py offline-checks
uv run --active python scripts/project.py baselines
uv run --active python scripts/project.py charts
uv run --active python scripts/project.py ui
uv run --active python scripts/project.py astro prepare
```

From another directory in PowerShell, set the clone path once and invoke the script by its absolute path:

```powershell
$repo = "D:\path\to\ecom-analytics-text2sql" # replace with your clone path
uv run --project $repo python "$repo\scripts\project.py" doctor
```

`doctor` does not print credentials or create a missing warehouse. `dbt parse` and `offline-checks` do not need a warehouse; data-running commands require the existing file. Stop Astro before `astro prepare`, which refreshes the generated source stage.

## Gold visualizations

Phase 5 includes ten reproducible static charts generated from DuckDB Gold marts. The script opens the warehouse read-only and reconciles core sales totals before writing PNGs.

Run from the repository root after DLT ingestion and `dbt build`:

```powershell
uv run --active python analytics/visualization/generate_charts.py
```

See the [visualization guide](analytics/visualization/README.md), the [business insights report](docs/phase-05-business-insights.md), and the generated charts in `docs/assets/charts/`.

## Text-to-SQL browser UI

The local browser interface routes questions through the same `NaturalLanguageQueryService` as the CLI. Deterministic safeguards can refuse or clarify locally; generated SQL is validated before the read-only DuckDB executor runs it. The UI displays the answer table, validated SQL on demand, KPI cards for single-row summaries, and an interactive bar or line chart when the bounded result shape supports one. The offline Q02 demo runs its golden baseline through the validator/executor without calling Gemini, so the chart UI can be previewed while API quota is unavailable. It listens on `127.0.0.1` only and does not save question or result history.

Start it from the repository root:

```powershell
uv run --active python -m text2sql.web_app
```

Stop the local server with `Ctrl+C`. See [Phase 6 progress](docs/phase-06-progress-checkpoint.md) for accepted behavior and optional regression commands.

The [Q1–Q15 reconciliation checkpoint](docs/checkpoint-q1-q15-reconciliation.md) records which business outputs were reconciled, the edge cases retained, and the assumptions to carry into Text-to-SQL evaluation.

![Executive overview](docs/assets/charts/01_executive_overview.png)

![Discount and profitability](docs/assets/charts/02_discount_profitability.png)

## Security and data handling

- Never commit .env files, API keys, source credentials, local database files, or source extracts.
- Phase 1 profiling is read-only and avoids selecting names, emails, or other customer-level PII.
- Share only aggregate profiling results in issues or documentation.

## Reference material

- [Xóm E-Com schema and business context](https://dataset.xomdata.com/datasets/schema/e_commerce)
- [Reference implementation](https://github.com/tunguyenn99/a-simple-t2s-flow)
- [Reference business context and 15 questions](https://github.com/tunguyenn99/a-simple-t2s-flow/blob/main/context.md)
