# Phase 8 — Hoàn thiện kiến trúc repository và chuẩn bị bàn giao

Ngày cập nhật: **2026-10-25**. Trạng thái: **8.1–8.6 đã được triển khai; 8.5 chờ lần chạy đầu tiên trên GitHub Actions, 8.7 Git review còn lại.**

Điều kiện đầu vào: Phase 7 đã được chủ dự án xác nhận pass build/parse, container checks, hai DAG runs, idempotency và failure recovery. [Checkpoint Phase 7](phase-07-airflow-cosmos.md)

## 1. Mục tiêu bàn giao

Người clone repo hiểu được luồng dữ liệu, cấu hình đúng môi trường, chạy kiểm tra offline trước, rồi chạy batch pipeline hoặc giao diện Text-to-SQL theo runbook. Source, local configuration, dữ liệu và output có quy tắc quản lý rõ ràng.

Kiến trúc đề xuất là modular monorepo với các module hiện có. Giữ các đường dẫn module đang được nghiệm thu; tổ chức lại tài liệu, entry points, CI và quản lý artifacts trước. Các module đang dùng imports, relative paths, Docker COPY và source-staging allowlist; mỗi lần di chuyển cần cập nhật và kiểm chứng toàn bộ các phụ thuộc đó.

Xem [ba sơ đồ kiến trúc và các hợp đồng môi trường](architecture.md).

## 2. Những điểm đã tìm thấy trong repo

| Điểm hiện tại | Tác động thực tế | Công việc |
|---|---|---|
| DUCKDB_PATH tương đối hoạt động ở Python nhưng dbt CLI trong thư mục ecom_analytics từng tìm sai file | Cùng cấu hình nhưng lệnh chạy ở vị trí khác cho kết quả khác | Chuẩn hóa path resolution và wrapper dbt |
| README dbt có ký tự escape ở heading, bullet và model name | Markdown render sai, khó đọc | Viết lại từ model/code hiện tại |
| ecom_analytics/.user.yml đang untracked, chứa metadata user của dbt | Có thể lọt vào commit cùng source | Ignore file metadata sau khi xác nhận phạm vi |
| Source staging copy .yml nhưng chưa loại riêng .user.yml | Metadata local có thể bị copy vào runtime stage | Bổ sung exclusion và kiểm tra staging bằng fixture tạm |
| Root .gitignore còn dbt_model/ từ tên thư mục cũ | Quy tắc ignore khó hiểu | Đối chiếu refs rồi bỏ entry lỗi thời, gom quy tắc |
| SKILL_PLAN có các mục Phase 6/7 lịch sử chưa cùng trạng thái với checkpoint mới | Model tiếp theo dễ hiểu sai tiến độ | Giữ checkpoint làm nguồn trạng thái; chú thích lịch sử, giảm lặp |
| vi-canonical.json là báo cáo lịch sử; confirmation mới nằm ở docs/chat | Có thể diễn giải báo cáo cũ là kết quả mới nhất | Thêm index reports, ngày/model/status và nguồn bằng chứng |
| Ban đầu chưa có .github/workflows | Thay đổi có thể được chia sẻ mà chưa qua kiểm tra tự động | Đã bổ sung CI offline + dbt parse + Astro import/contracts trong 8.5 |
| Ban đầu, offline guardrails khởi tạo executor và phụ thuộc warehouse | Fresh clone chưa có data không thể chạy kiểm tra xác định | 8.3 chuyển executor sang lazy initialization; offline checks hiện chạy không cần warehouse/Gemini |
| Cây module chính đã có ranh giới rõ | Có thể hoàn thiện với ít thay đổi đường dẫn | Giữ ingestion/, text2sql/, ecom_analytics/, orchestration/ |

Các nhận xét trên đến từ đọc source/config, git status và các lỗi đã gặp trong phiên triển khai. Kế hoạch này chưa khẳng định các job CI đã chạy.

## 3. Cây thư mục đích

Ký hiệu (+) là thành phần dự kiến thêm trong Phase 8. Các phần không có (+) đã tồn tại; cây được rút gọn.

~~~text
ecom-analytics-text2sql/
├── README.md                         # Tổng quan, quick start, kiến trúc, trạng thái
├── SKILL_PLAN.md                     # Handoff gọn, link tới kế hoạch/checkpoint
├── pyproject.toml
├── uv.lock
├── .python-version
├── .env.example                     # Template host
├── .gitignore
├── .github/ (+)
│   └── workflows/
│       ├── offline.yml              # Python tests, policy/catalog, dbt parse
│       └── orchestration.yml        # Astro image/import/contracts trên Linux
├── scripts/
│   └── project.py                   # CLI hỗ trợ, gọi lại các module đã có
├── ingestion/
│   ├── config.py                    # Settings; warehouse path helper dùng lại
│   ├── sqlserver.py
│   ├── check_source_connection.py
│   ├── profile_source_tables.py
│   └── run_pipeline.py
├── ecom_analytics/
│   ├── README.md                    # Hướng dẫn dbt đã sửa Markdown/path
│   ├── dbt_project.yml
│   ├── profiles.yml.example
│   ├── models/
│   │   ├── sources.yml
│   │   ├── staging/
│   │   ├── intermediate/
│   │   └── marts/
│   │       ├── sales/
│   │       ├── products/
│   │       ├── customers/
│   │       └── geography/
│   ├── tests/                       # Singular SQL data tests
│   └── macros/, analyses/, seeds/, snapshots/  # Giữ đúng config khi còn trống
├── text2sql/
│   ├── semantic_catalog.yml         # Định nghĩa semantic dùng lúc chạy
│   ├── access_policy.yml            # Quyền, templates và execution limits
│   ├── catalog.py, validator.py, executor.py
│   ├── service.py, nl_service.py, gemini.py
│   ├── cli.py, web_app.py, output.py, charting.py
│   └── evaluation/                  # Golden set + evaluation runners
├── analytics/
│   └── visualization/              # Script và README sinh 10 biểu đồ
├── orchestration/
│   ├── README.md
│   ├── Dockerfile, requirements.txt, packages.txt
│   ├── .env.example
│   ├── .astro/config.yaml
│   ├── docker-compose.override.yml
│   ├── dags/
│   ├── scripts/prepare_runtime.py
│   ├── tests/dags/                  # DagBag/Cosmos contracts
│   └── include/runtime/             # GENERATED, IGNORED
├── tests/                           # Python tests với mocks/temp fixtures
├── sql/phase_01_profile.sql          # Tái lập profiling nguồn; ngoài dbt runtime
├── docs/
│   ├── architecture.md              # Sơ đồ và ranh giới trách nhiệm
│   ├── phase-01...phase-08...md      # Giữ đường dẫn phase docs hiện tại
│   ├── checkpoint-q1-q15-reconciliation.md
│   ├── setup.md                     # Fresh clone, local data và Astro setup (8.4)
│   ├── operations.md                # Refresh, serving, lỗi và recovery (8.4)
│   ├── project-walkthrough.md (+)   # Bài trình bày/demo project
│   ├── decisions/                   # ADR 0001 layout; ADR 0002 DuckDB access (8.4)
│   └── assets/charts/               # 10 PNG tổng hợp đã review
├── reports/
│   ├── README.md (+)                # Index bằng chứng, historical/current
│   ├── text2sql-evaluation/          # Sanitized JSON có giá trị nghiệm thu
│   └── orchestration/ (+)           # Acceptance summaries, không raw logs
├── .venv/                           # LOCAL, IGNORED
├── .env                             # LOCAL, IGNORED
├── duckdb_warehouse/                 # LOCAL, IGNORED
└── logs/, .cache/                    # GENERATED, IGNORED
~~~

Đây là application project với tool.uv.package=false. Packaging thành thư viện và chuyển sang src/ là một quyết định kiến trúc riêng nếu sau này cần phân phối package.

## 4. Quy tắc sắp xếp và cleanup

| Đối tượng | Hành động Phase 8 | Kiểm tra bắt buộc |
|---|---|---|
| Source trong 5 module chính | Giữ đường dẫn, làm rõ trách nhiệm | Imports, lệnh entry point và staging vẫn đúng |
| profiles.yml local, .env, warehouse | Giữ local, ignore | Git status/ls-files, templates an toàn |
| .user.yml và caches/generated artifacts | Bổ sung ignore đúng phạm vi; bỏ khỏi staged set nếu có | Không bỏ nhầm source hoặc artifact nghiệm thu |
| dbt target/logs/packages | Sinh lại khi chạy, ignore | Parse/build không phụ thuộc artifact cũ |
| include/runtime/ | Sinh bằng prepare_runtime.py, không sửa tay | Kiểm tra marker, allowlist, profile template |
| reports JSON lịch sử | Giữ nguyên nội dung/ngày, thêm index | Link và nguồn bằng chứng rõ; không ghi đè lịch sử |
| CSV xuất kết quả local | Dùng reports/exports/ có ignore mặc định | Không lọt dữ liệu khi commit |
| PNG trong docs/assets/charts | Giữ 10 biểu đồ đã review để README render được | Script tái sinh được, ghi snapshot nguồn |
| sql/phase_01_profile.sql | Giữ làm script profiling tái lập | Tài liệu phân biệt source profiling và dbt models |
| Placeholder dbt directories | Giữ nếu dbt_project.yml còn khai báo | Chỉ bỏ khi đồng thời sửa config/refs |
| Thư mục dữ liệu, Docker volumes, logs đang dùng | Kiểm kê; cleanup nội dung chỉ ở tác vụ riêng | Xác minh absolute path, runtime đã dừng và có nhu cầu xóa |

Mỗi lần đổi tên/chuyển file cần tìm refs trong Python, SQL/YAML, docs, Dockerfile, Compose, staging helper và tests trước; kiểm chứng xong mới chuyển nhóm tiếp theo.

## 5. Các bước triển khai và đầu ra

### 8.1 — Chốt inventory và quyết định layout

**Đã làm:** kiểm kê ownership của các module và local/generated/evidence paths; kiểm tra references của dbt project, Python imports, Dockerfile/Compose, DAG và staging helper; chốt giữ modular monorepo và không di chuyển các module đang chạy.

**Artifact:** [architecture.md](architecture.md), [ADR 0001 — repository layout](decisions/0001-repository-layout.md), bảng inventory trong architecture. Không ghi credentials, raw rows hoặc nội dung warehouse vào inventory.

**Kết quả:** mỗi thư mục chính có trách nhiệm và quy tắc Git; chưa có kế hoạch đổi đường dẫn source vì runtime đang tham chiếu trực tiếp. ADR nêu rõ điều kiện cần kiểm tra nếu tương lai có migration. Đặc biệt, batch refresh và serving hiện vẫn dùng chung DuckDB file nên cần vận hành theo cửa sổ tuần tự.

### 8.2 — Dọn repository và tài liệu hiện có

**Đã làm:** bỏ ignore entries `dbt_model/` cũ sau khi search không thấy thư mục/reference runtime; thêm ignore cho dbt `.user.yml` và local `reports/exports/`; staging helper loại `.user.yml` và fail nếu metadata local lọt vào stage; thêm fixture tests cho hai nhánh bảo vệ; sửa README dbt bị escape; thêm index báo cáo; đồng bộ trạng thái Phase 6/8 trong README, SKILL_PLAN và checkpoint/tài liệu Phase 6.

**File:** `.gitignore`, `ecom_analytics/.gitignore`, `orchestration/scripts/prepare_runtime.py`, `ecom_analytics/README.md`, `tests/test_prepare_runtime.py`, `SKILL_PLAN.md`, docs Phase 6/8, `README.md` và `reports/README.md`.

**Đạt khi:** `git check-ignore` nhận diện local metadata/export; staging allowlist bỏ qua và validation từ chối `.user.yml`; README dbt render như Markdown; link nội bộ hợp lệ; report cũ vẫn giữ nguyên và được ghi nhãn lịch sử. Kiểm tra này không xóa file local, warehouse, report hoặc thư mục runtime.

### 8.3 — Chuẩn hóa cấu hình và lệnh chạy

**Đã làm:** thêm `ingestion.config.resolve_warehouse_path()` không cần SQL Server credentials. Thứ tự ưu tiên là đối số tường minh → process environment → `DUCKDB_PATH` trong root `.env` → mặc định `duckdb_warehouse/warehouse.duckdb`. Mọi path tương đối được neo vào repo root; path tuyệt đối của Windows/container được giữ nguyên. Resolver không tạo database hoặc thư mục.

`Settings.from_env`, `DuckDBExecutor` và static chart generator dùng cùng resolver. `NaturalLanguageQueryService` tạo DuckDB executor khi thật sự cần chạy query; deterministic router checks nhờ vậy không mở warehouse. Real executor vẫn fail nếu file warehouse chưa tồn tại.

`scripts/project.py` xác định repo root từ vị trí script, đặt `cwd` cho subprocess, ưu tiên dbt trong interpreter đang chạy, và truyền args dưới dạng list, không qua shell. Các lệnh dbt dùng `profiles.yml.example` trong thư mục tạm và truyền warehouse path tuyệt đối; profile Windows local không bị đọc hoặc ghi đè. `build`, `test`, `show`, baselines, charts và UI kiểm tra file warehouse trước khi chạy. `parse` không yêu cầu warehouse.

Các lệnh chính từ repo root:

~~~powershell
uv run --active python scripts/project.py doctor
uv run --active python scripts/project.py dbt parse
uv run --active python scripts/project.py dbt build
uv run --active python scripts/project.py offline-checks
uv run --active python scripts/project.py baselines
uv run --active python scripts/project.py charts
uv run --active python scripts/project.py ui
uv run --active python scripts/project.py astro prepare
~~~

Từ thư mục khác trong PowerShell, đặt biến `$repo` bằng đường dẫn clone rồi chạy `uv run --project $repo python "$repo\scripts\project.py" doctor`. `doctor` báo warehouse thiếu nhưng không tạo file. `offline-checks` không cần Gemini key hoặc warehouse. Trước `astro prepare`, dừng Astro stack để không thay generated source stage đang được container mount.

**Kiểm chứng:** 46/46 unit tests pass; có test chạy offline checks từ thư mục ngoài repo khi warehouse không tồn tại. `doctor` xác nhận root, Python, dbt executable trong `.venv`, profile template và warehouse. `dbt parse` pass qua wrapper khi được gọi từ thư mục Temp.

**File:** `scripts/project.py`, `ingestion/config.py`, `text2sql/executor.py`, `text2sql/nl_service.py`, `analytics/visualization/generate_charts.py`, cùng path/command tests.

**Kết quả:** resolver nhất quán và không phụ thuộc current working directory; dbt parse/offline checks chạy không cần SQL Server/Gemini credentials; lệnh cần dữ liệu báo thiếu warehouse mà không tạo DB rỗng; CLI modules cũ vẫn dùng được.

### 8.4 — Hoàn thiện setup và operations runbook

**Đã làm:** viết [`docs/setup.md`](setup.md) với quy trình fresh clone, Python 3.11/uv, ba chế độ offline/local/Astro, phân biệt root `.env` với `orchestration/.env`, nạp source, dbt, charts, UI và điều kiện Gemini. Hướng dẫn nói rõ trạng thái `doctor` khi fresh clone chưa có warehouse và giải thích `DEFER` trong offline checks.

[`docs/operations.md`](operations.md) ghi bất biến DAG/warehouse, cửa sổ refresh/serving, tiêu chí chấp nhận run, snapshot reference, xử lý queued/failed/upstream_failed, network checks và nguyên tắc recovery bằng run mới sau khi sửa nguyên nhân. [`ADR 0002`](decisions/0002-duckdb-access.md) chốt một DuckDB file, path host/container và giới hạn reader/writer.

README gốc và `orchestration/README.md` dẫn tới runbooks để tránh có hai hướng dẫn vận hành mâu thuẫn. Airflow mặc định dùng cổng 8080; Text-to-SQL UI bind `127.0.0.1:8765`.

**File:** `docs/setup.md`, `docs/operations.md`, `docs/decisions/0002-duckdb-access.md`, `README.md`, `docs/architecture.md`, `SKILL_PLAN.md`, `orchestration/README.md`.

**Đạt:** hướng dẫn phân biệt bước offline với bước cần credentials/warehouse, đặt expected output và giải thích cách dừng, phục hồi; wrapper 8.3 giữ path ổn định khi chạy từ cwd khác. Chưa chạy lại Airflow runtime vì 8.4 chỉ cập nhật tài liệu và ADR.

### 8.5 — CI đúng với từng lớp kiểm tra

| Job | Môi trường | Phạm vi | Cần warehouse/API thật? |
|---|---|---|---|
| Python offline | Python 3.11, Linux + Windows | unittest hiện có, policy/catalog/golden schema, deterministic routing, output/chart tests | Không; mocks và dữ liệu tổng hợp nhỏ |
| dbt static | Linux, root uv.lock + dummy profile/path tạm | dbt parse, graph inventory/catalog mapping | Không |
| Astro contract | Linux có Docker | prepare_runtime → build → DAG import và contract tests trong Astro | Không; không execute source tasks |
| Local acceptance | Máy chủ dự án | SQL Server/DLT/dbt build + 15 warehouse baselines + DAG/recovery | Có warehouse/source, không cần Gemini |
| Live NL evaluation | Người chạy chủ động | Canonical/paraphrase/model-dependent guardrail cần xác nhận mới | Có warehouse và Gemini quota |

dbt parse xác thực project nhưng không kết nối warehouse; nó không thay thế dbt build hoặc data tests. [dbt parse documentation](https://docs.getdbt.com/reference/commands/parse)

GitHub workflow dùng uv sync --locked để fail nếu lockfile lệch; không tự nâng dependency khi chạy CI. [uv trong GitHub Actions](https://docs.astral.sh/uv/guides/integration/github/)

Astro CLI được pin ở **1.46.1**. `astro dev parse` và `astro dev pytest` kiểm tra DAG trong container, không cần khởi chạy Airflow webserver/scheduler; các lệnh này cần Docker. [Astro test project](https://www.astronomer.io/docs/astro/cli/test-your-astro-project-locally/), [Astro dev pytest](https://www.astronomer.io/docs/astro/cli/astro-dev-pytest)

**Đã triển khai trong repo:**

- [`.github/workflows/offline.yml`](../.github/workflows/offline.yml) chạy Python 3.11 unit tests và deterministic `offline-checks` trên Ubuntu + Windows. Job dbt riêng chạy wrapper `dbt parse`, sau đó gọi `python -m text2sql.dbt_contract` để đối chiếu toàn bộ Gold relation trong manifest với 12 relation của semantic catalog.
- [`text2sql/dbt_contract.py`](../text2sql/dbt_contract.py) fail nếu mart Gold bị thiếu, có model chưa đăng ký trong catalog, relation trùng hoặc model Gold đổi thành `ephemeral`. Kiểm tra này chỉ đọc manifest/catalog, không mở DuckDB.
- [`.github/workflows/orchestration.yml`](../.github/workflows/orchestration.yml) chạy khi thay đổi đường dẫn liên quan hoặc được gọi thủ công. Workflow tạo runtime stage bằng allowlist, build Docker image một lần, rồi tái sử dụng image để parse DAG và chạy tests trong `orchestration/tests/dags`.
- GitHub Actions được pin bằng full commit SHA; uv cài dependencies qua `uv sync --locked`; quyền giới hạn `contents: read`, có timeout và cancel run cũ trên cùng ref.

**Trigger và giới hạn:** offline/dbt chạy trên mọi push và pull request; Astro dùng path filters cho ingestion, Text-to-SQL, dbt, orchestration và dependency files, đồng thời có `workflow_dispatch`. CI không gọi SQL Server/Gemini, không cần `.env` hoặc warehouse, không sao chép dữ liệu thật hay tải artifact có credentials. `offline-checks` vẫn có thể báo `DEFER` cho semantic evaluation cần Gemini; đó không phải lỗi của deterministic checks.

**Trạng thái nghiệm thu:** workflow và contract đã được thêm; chưa có kết quả clean runner từ GitHub Actions trong phiên này. Sau khi push, cần kiểm tra cả hai workflow và chỉ chốt 8.5 sau khi job tương ứng pass. `dbt parse` không thay thế `dbt build`, data tests hoặc DAG acceptance với nguồn dữ liệu thật.

**Sửa lỗi CI lần đầu (2026-10-25):** wrapper tìm `dbt` bằng
`sysconfig.get_path("scripts")` để giữ đúng scripts directory của virtualenv trên
Linux, thay vì resolve symlink Python về interpreter gốc. DAG contracts có fixture
khởi tạo SQLite metadata tạm riêng cho Airflow/Cosmos; pytest không dùng lại metadata
của container `astro dev parse`. Các tests đọc DAG từ graph đã parse trong bộ nhớ.
Kiểm chứng local: 53/53 unit tests, 14/14 deterministic guardrail cases, 3/3 DAG
contracts trong container không mạng, dbt parse trên Windows và Linux virtualenv
symlink thật, catalog khớp 12 Gold relations. Linux probe dùng dependencies trong
image có sẵn; đây chưa phải xác nhận workflow trên GitHub runner. Cần push bản sửa
và kiểm tra run mới trước khi đóng 8.5.

`run_offline_checks` chạy không cần warehouse vì `NaturalLanguageQueryService` chỉ tạo executor khi cần thực thi query. Offline workflow được cấu hình để chạy deterministic checks trên clean runner không cần SQL Server hoặc Gemini; cần GitHub Actions run đầu tiên để nghiệm thu cấu hình này.

**Đạt khi:** fresh runner không có .env/warehouse vẫn pass các job offline; contract cố ý sai làm CI fail đúng; checks ghi tên đúng phạm vi, không báo đã test real data khi chỉ parse.

### 8.6 — Bằng chứng và walkthrough

**Đã triển khai:** [`docs/project-walkthrough.md`](project-walkthrough.md) trình bày đường đi source → DLT/Bronze → dbt/Silver/Gold → chart → Text-to-SQL, dùng Q02 làm câu chuyện chính. Walkthrough có lệnh chạy, kết quả segment đã đối soát, hai chart từ snapshot, demo Q02 offline không gọi Gemini, cùng giải thích luồng Gemini/SQLGlot/read-only và các caveat nghiệp vụ.

[`reports/README.md`](../reports/README.md) là evidence index theo ngày, suite và model; phân biệt checkpoint đã được xác nhận, artifact JSON lịch sử, chart snapshot và CI đang chờ clean runner. [`reports/orchestration/phase-07-acceptance.md`](../reports/orchestration/phase-07-acceptance.md) ghi rõ nguồn của xác nhận Phase 7, hai lần chạy, idempotency, 15/15 quality gate và failure recovery. File không giả lập run IDs hoặc trình bày owner confirmation như log export.

README dẫn tới walkthrough và evidence index. Không chạy lại ingestion, dbt build, chart generation, Gemini hay DAG trong bước viết tài liệu này; các hình và số liệu được dẫn từ snapshot/checkpoint đã có. Bằng chứng lịch sử không bị ghi đè hoặc tự nâng thành current run.

**Trạng thái:** walkthrough và evidence index đã được viết, dùng được để trình bày; trạng thái 8.5 vẫn chờ lần GitHub Actions đầu tiên. Bước tiếp theo sau CI là 8.7 Git review.

### 8.7 — Review Git và chuẩn bị chia sẻ

**Việc làm:** review toàn bộ tracked/modified/untracked files; nhóm file source, config templates, docs và evidence có chủ đích; kiểm tra attribution reference và lựa chọn license phù hợp trước khi thêm LICENSE; review staged set theo workflow của chủ dự án rồi tạo checkpoint commit.

**Đạt khi:** clone từ commit có đủ source/templates/docs; thiếu secrets không cản checks offline; warehouse/.env/runtime staging/generated user files không bị commit; README đúng với CI và runbook.

Publish public deployment là một quyết định tiếp theo nếu cần. Bàn giao Phase 8 tập trung vào repository có thể tái lập, giải thích và kiểm chứng.

## 6. Thứ tự triển khai và tiêu chí đóng Phase 8

Thực hiện **8.1 → 8.2 → 8.3 → 8.4 → 8.5 → 8.6 → 8.7**, mỗi lượt một nhóm thay đổi có thể review.

- [x] Lập kế hoạch Phase 8 và sơ đồ kiến trúc.
- [x] Chốt inventory, ownership và layout decision.
- [x] Hoàn tất ignore/Markdown/link/status cleanup.
- [x] Path resolution và command wrapper hoạt động trên Windows; dbt parse và offline checks chạy độc lập current working directory. Linux/Astro contract tiếp tục được xác nhận ở 8.5.
- [x] Setup/operations runbook, môi trường host/container riêng và quyết định DuckDB access cho fresh clone.
- [x] Thêm CI offline/dbt/Astro đúng phạm vi, kiểm tra catalog ↔ dbt graph; chờ workflow đầu tiên pass từ clean GitHub runner.
- [x] Walkthrough Q02 và evidence index được viết; Phase 7 provenance/giới hạn được ghi rõ.
- [ ] Review staged set và lưu Git checkpoint theo yêu cầu chủ dự án.

8.1–8.4 được chốt bằng ADR/inventory, path/CLI implementation, unit tests, dbt parse và runbooks khớp cấu hình hiện tại. 8.5 có workflow/contract code nhưng cần GitHub Actions output để xác nhận trên clean runner. 8.6 đã có walkthrough/evidence index; 8.7 còn lại là review Git và checkpoint theo yêu cầu chủ dự án.
