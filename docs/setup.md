# Hướng dẫn thiết lập project

Project chạy batch trên Windows: SQL Server → DLT → DuckDB → dbt → phân tích/Text-to-SQL, với Astro/Airflow/Cosmos tùy chọn để điều phối. DuckDB là warehouse dạng file; không cần cài database server cho nó.

> Không đưa mật khẩu SQL Server, Gemini API key, nội dung `.env` hoặc dữ liệu khách hàng vào Git, ảnh chụp màn hình hay log chia sẻ.

## Chọn chế độ chạy

| Chế độ | Cần credentials? | Cần warehouse? | Kết quả |
|---|---:|---:|---|
| Offline sau khi clone | Không | Không | Guardrails xác định và dbt project graph |
| Phân tích local | SQL Server để nạp dữ liệu | Có; DLT tạo | Gold marts, baselines, biểu đồ, CLI/UI |
| Airflow/Cosmos | SQL Server trong `orchestration/.env` | DLT ghi vào warehouse được mount | DAG chạy ingestion → dbt → quality gate |
| NL hỏi Gemini | `GEMINI_API_KEY` trong root `.env` | Có | Sinh câu trả lời/SQL; validator và policy vẫn bắt buộc |

Offline checks không gọi Gemini hay SQL Server. DAG Airflow cũng không gọi Gemini; quality gate là 15 baseline cases chạy offline.

## 1. Clone và cài Python environment

Yêu cầu host: Git, Python **3.11.x**, và [uv](https://docs.astral.sh/uv/). Project khai báo Python `>=3.11,<3.12`. Docker Desktop với Linux Engine và Astro CLI chỉ cần cho Airflow; image project pin Astro Runtime `12.7.0` trong `orchestration/Dockerfile`.

Trong PowerShell:

```powershell
git clone https://github.com/Nguyen-Hoan023/ecom-analytics-text2sql.git
Set-Location ecom-analytics-text2sql
python --version
uv --version
uv sync --locked
```

Mặc định, `uv sync --locked` tạo/cập nhật `.venv` trong repo. Có thể chạy lệnh project bằng `uv run --project . ...` mà không cần activate. Nếu dùng virtual environment ở vị trí khác, activate đúng environment rồi dùng nhất quán `uv run --active ...`; wrapper dùng Python đang chạy để tìm dbt cùng environment đó.

Kiểm tra cơ bản:

```powershell
uv run --project . python scripts/project.py doctor
uv run --project . python scripts/project.py offline-checks
uv run --project . python scripts/project.py dbt parse
```

Fresh clone chưa nạp dữ liệu có thể khiến `doctor` báo `MISSING DuckDB warehouse` và trả exit code khác 0. Đây là trạng thái bình thường khi chưa có warehouse. `offline-checks` vẫn phải chạy được; `dbt parse` chỉ kiểm tra cấu trúc project, không kết nối warehouse. Offline runner dự kiến 14/14 kiểm tra xác định pass; ca cần Gemini hoặc natural-language routing được ghi `DEFER`.

## 2. Cấu hình host để đọc nguồn

Chỉ cần khi muốn kết nối SQL Server hoặc chạy DLT. Tạo `.env` từ template nếu file chưa có; không ghi đè file local hiện hữu:

```powershell
if (-not (Test-Path .env)) {
    Copy-Item -LiteralPath .env.example -Destination .env
}
notepad .env
```

Điền local các biến `XOM_SQLSERVER_HOST`, `XOM_SQLSERVER_PORT`, `XOM_SQLSERVER_DATABASE`, `XOM_SQLSERVER_SCHEMA`, `XOM_SQLSERVER_USERNAME`, `XOM_SQLSERVER_PASSWORD`. Với dataset hiện tại, host/database/schema lần lượt là `db.xomdata.com`, `xomdata_dataset`, `e_commerce`; port là `1433`. Host và port là hai biến riêng. Warehouse mặc định là `duckdb_warehouse/warehouse.duckdb`; path tương đối được neo vào repo root. Có thể đặt `DUCKDB_PATH` ở `.env` hoặc process environment để chọn path khác.

Xác nhận `.env` bị Git ignore mà không in giá trị:

```powershell
git check-ignore .env
```

Kiểm tra kết nối read-only:

```powershell
uv run --project . python -m ingestion.check_source_connection
```

Kỳ vọng: kết nối được database đã cấu hình và smoke query trả `1`. DNS/TCP, login và quyền database là các lớp lỗi khác nhau; xem [operations runbook](operations.md). Không gửi mật khẩu để chẩn đoán.

## 3. Nạp và dựng warehouse local

Đóng UI, chart process và lệnh dbt đang dùng cùng warehouse trước khi refresh. DLT chạy snapshot `write_disposition="replace"`; sau khi nạp, dựng dbt và chạy baseline theo thứ tự:

```powershell
uv run --project . python -m ingestion.run_pipeline
uv run --project . python scripts/project.py dbt build
uv run --project . python scripts/project.py baselines
```

Khi Gold đã được kiểm tra, có thể sinh lại 10 biểu đồ:

```powershell
uv run --project . python scripts/project.py charts
```

`dbt build` dùng `profiles.yml.example` làm profile tạm và path tuyệt đối do wrapper truyền vào; không cần ghi đè `ecom_analytics/profiles.yml` local. `baselines` cần warehouse hiện hữu và không gọi Gemini. Mốc snapshot đã nghiệm thu: sales lines 51.290, total sales `6,517,674.00`, total profit `1,065,413.58`. Nếu nguồn đổi, hãy đối chiếu source, models và metric contract trước khi sửa expected outputs.

## 4. Text-to-SQL local

Offline guardrails không cần API key. Câu hỏi có thể xử lý/clarify cục bộ vẫn hoạt động; câu cần Gemini mới cần `GEMINI_API_KEY` trong **root `.env`**. Không đặt key này trong `orchestration/.env`.

Sau khi có warehouse và quality checks pass:

```powershell
uv run --project . python scripts/project.py ui
```

Mở `http://127.0.0.1:8765`; dừng server bằng `Ctrl+C`. UI bind localhost và chưa có đăng nhập/phân quyền đa người dùng; không publish cổng này ra Internet. Không chạy UI trong lúc DAG refresh warehouse.

## 5. Astro/Airflow/Cosmos (tùy chọn)

Phần này cần Docker Desktop dùng Linux Engine, Astro CLI và SQL Server có thể truy cập từ container. Các lệnh host ở trên không cần Docker.

Từ repo root xác nhận Docker:

```powershell
astro version
docker version
docker info --format '{{.OSType}}'
```

`docker version` cần có Client và Server; `OSType` cần là `linux`. Tạo `orchestration/.env` từ template nếu chưa có, không ghi đè file hiện hữu:

```powershell
if (-not (Test-Path orchestration/.env)) {
    Copy-Item -LiteralPath orchestration/.env.example -Destination orchestration/.env
}
notepad orchestration/.env
```

Điền SQL Server variables theo cấu hình máy (dataset hiện tại: host `db.xomdata.com`, port `1433`, database `xomdata_dataset`, schema `e_commerce`). Trong container, `DUCKDB_PATH` phải là `/usr/local/airflow/duckdb_warehouse/warehouse.duckdb` và `PYTHONPATH` là `/usr/local/airflow`. Không copy root `.env` nguyên trạng sang đây: container dùng path Linux và Compose inject file riêng. Code hiện dùng environment variables, không cần tạo Airflow Connection. Không cần Gemini key cho DAG.

Chuẩn bị generated source stage rồi parse/start:

```powershell
uv run --project . python scripts/project.py astro prepare
Set-Location orchestration
astro dev parse
astro dev start
astro dev ps
astro dev run db check
astro dev run dags list-import-errors
astro dev run dags list
```

Kỳ vọng không có import errors và DAG `xom_ecom_warehouse_refresh` xuất hiện. Mở `http://localhost:8080`; dùng thông tin đăng nhập do Astro CLI hiển thị. DAG chỉ chạy thủ công. Xem [operations runbook](operations.md) để trigger và kiểm tra. Hướng dẫn container diagnostics chi tiết hơn có trong [orchestration README](../orchestration/README.md) và [Phase 7 checkpoint](phase-07-airflow-cosmos.md).

Sau khi đổi source/dbt, dừng Astro trước khi cập nhật generated stage:

```powershell
astro dev stop
Set-Location ..
uv run --project . python scripts/project.py astro prepare
Set-Location orchestration
astro dev parse
astro dev start
```

## Runtime files cần giữ local

- Root `.env` và `orchestration/.env`: cấu hình/credentials máy local.
- `duckdb_warehouse/`: warehouse.
- `orchestration/include/runtime/`: stage do helper sinh.
- `.venv/`, dbt `target/`, logs và Docker volumes: runtime/build artifacts.

Chỉ các file template `.env.example` và `orchestration/.env.example` được chia sẻ. Trước khi commit, kiểm tra ignore mà không in nội dung secrets:

```powershell
git check-ignore .env orchestration/.env duckdb_warehouse/warehouse.duckdb orchestration/include/runtime
```

Tiếp theo: [operations](operations.md) · [architecture](architecture.md) · [Phase 8](phase-08-polish-and-release.md).
