# Giai đoạn 2 — Môi trường và cấu hình project

**Trạng thái:** scaffold project và `uv.lock` đã tạo; dependency đã được đồng bộ vào venv hiện có của workspace (Python 3.11.9). Chưa điền credentials và chưa kết nối nguồn.

## Mục tiêu

Tạo một môi trường Python có thể tái lập, lưu cấu hình kết nối ngoài code và dùng chung một vị trí DuckDB. Giai đoạn này chuẩn bị nền; DLT sẽ được triển khai và kết nối tới SQL Server ở Giai đoạn 3.

## Lựa chọn hiện tại

- Python 3.11; `.python-version` khai báo phiên bản chính và `pyproject.toml` giới hạn môi trường vào Python 3.11.
- `uv.lock` lưu bộ phiên bản dependency đã phân giải; `uv sync` đồng bộ môi trường theo lockfile.
- `dlt[duckdb,sql_database]` cho source SQL database và DuckDB destination; `pymssql` là driver cho kết nối nguồn SQL Server.
- `dbt-duckdb` là adapter dbt cho warehouse DuckDB.
- `python-dotenv` nạp cấu hình local từ `.env`; file mẫu là `.env.example`.
- `.env`, credentials, file DuckDB và artifact sinh ra đều không được commit.
- Airflow/Cosmos và Gemini chưa được cài ở giai đoạn này; chúng thuộc orchestration và Text-to-SQL.

## Cấu hình

`ingestion/config.py` nạp `.env` nằm ở root repo và tạo một `Settings` bất biến. Nó kiểm tra host, database, username, password, port và schema; lỗi chỉ liệt kê tên biến thiếu, không in giá trị bí mật. Đường dẫn DuckDB tương đối được phân giải từ root repo để ingestion, dbt và các chương trình sau này dùng cùng file.

Thiết lập local:

1. Sao chép `.env.example` thành `.env` trong root repo.
2. Điền host, database, username và password do Xóm cấp. Giữ schema là `e_commerce` nếu nguồn không yêu cầu khác.
3. Không gửi `.env` lên GitHub hoặc trong chat. `.env.example` chỉ chứa tên biến và được commit.

Không cần tạo lại venv nếu đã có môi trường riêng. Hãy activate môi trường đó trước khi đồng bộ dependency.

## Cài đặt trên PowerShell

Khi clone repo mới, có thể tạo một venv tại repo:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
uv sync --active
Copy-Item .env.example .env
```

Với venv hiện có ở vị trí khác, activate đúng file `Activate.ps1` của môi trường rồi chạy:

```powershell
uv sync --active
```

`--active` yêu cầu uv đồng bộ môi trường đang activate thay vì tự tạo `.venv` mới trong repo. Nếu chưa khai báo credentials, config sẽ báo tên trường cần điền khi được gọi; giai đoạn setup không cần kết nối nguồn.

## Phạm vi chưa làm trong giai đoạn này

- Chưa đọc transaction từ SQL Server hay tạo warehouse có dữ liệu.
- Chưa transform Bronze/Silver/Gold.
- Chưa cài Airflow/Cosmos hoặc Gemini.
- Chưa chọn incremental load; chiến lược snapshot/full-refresh sẽ được chốt và giải thích ở Giai đoạn 3.

## Điều kiện hoàn tất

- Venv hiện có được đồng bộ theo `uv.lock` mà không tạo môi trường thứ hai.
- `.env.example` mô tả đủ cấu hình nguồn và đích; `.env` thật nằm ngoài Git.
- Config kiểm tra thiếu giá trị và port sai trước khi pipeline dùng credentials.
- DuckDB path có một cấu hình duy nhất, tương đối với repo hoặc được override bằng biến môi trường.
- README hướng dẫn được cách cài lại môi trường và chuẩn bị `.env`.
