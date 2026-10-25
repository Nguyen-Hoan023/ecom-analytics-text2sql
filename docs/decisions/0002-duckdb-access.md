# ADR 0002: Vận hành DuckDB file theo cửa sổ refresh và serving

- **Trạng thái:** Accepted
- **Ngày:** 2026-10-25
- **Phạm vi:** Phase 8.4 — setup và operations

## Bối cảnh

Project dùng một DuckDB warehouse dạng file cho Bronze, Silver và Gold. Host Windows và Astro container cùng truy cập file qua bind mount. DLT thay snapshot Bronze; dbt ghi các model Gold; quality gate, biểu đồ và Text-to-SQL đọc warehouse. Airflow metadata nằm ở PostgreSQL riêng, không phải warehouse phân tích.

DuckDB là embedded database, không phải server điều phối reader/writer giữa các máy. Theo concurrency contract của DuckDB 1.5.x đang pin, nhiều process có thể cùng mở file read-only; không process nào được ghi trong lúc các reader đó đang hoạt động. Path logic ở host và container phải trỏ tới cùng file vật lý; refresh cần được phối hợp với các client khác đang mở file. Xem [DuckDB 1.5 concurrency](https://duckdb.org/docs/1.5/connect/concurrency).

## Quyết định

1. Giữ DuckDB file và kiến trúc hiện tại; không thay storage engine trong Phase 8.
2. Chuẩn hóa host path qua `ingestion.config.resolve_warehouse_path()`. Path tương đối neo vào repo root; precedence: explicit argument → process environment → root `.env` → mặc định `duckdb_warehouse/warehouse.duckdb`.
3. Container nhận path Linux tuyệt đối `/usr/local/airflow/duckdb_warehouse/warehouse.duckdb` qua `orchestration/.env`. Compose bind-mount thư mục host `duckdb_warehouse/` vào path đó. Không dùng path Windows trong container.
4. DLT ingestion, dbt transform/tests và quality gate chạy tuần tự trong DAG. DAG giới hạn một active run/task, trigger thủ công và không retry tự động.
5. Tạo cửa sổ refresh: đóng UI, charts, dbt và query host đang truy cập warehouse trước trigger; chỉ phục vụ sau khi DAG và quality gate hoàn tất.
6. Lệnh local dùng `scripts/project.py` để thống nhất resolver, absolute warehouse path và profile dbt tạm. Container dùng profile sinh từ template.
7. Không xóa/đổi tên warehouse hoặc WAL/lock để vượt lỗi mở file. Dừng tiến trình đang giữ file, điều tra DAG và mở lại bằng đúng path.

## Hệ quả

- Không có refresh liên tục trong lúc Text-to-SQL serving và charts luôn mở; đây là giới hạn vận hành được chấp nhận cho project batch hiện tại.
- DLT `replace` thay snapshot Bronze; downstream phải được dựng lại và quality gate phải pass trước khi coi kết quả là current.
- Source snapshot đổi có thể làm row counts/revenue/profit khác checkpoint. Chênh lệch cần điều tra, không tự động ghi đè expected outputs.
- DuckDB phù hợp cho local development/demo. Nếu cần nhiều writers, nhiều host hoặc serving liên tục trong refresh, cần ADR mới về snapshot publication hoặc warehouse server; không khắc phục bằng chia sẻ file qua network drive.

## Bằng chứng và liên kết

- [Sơ đồ kiến trúc và runtime boundary](../architecture.md)
- [Hướng dẫn setup](../setup.md)
- [Operations runbook](../operations.md)
- [Phase 7 runtime acceptance](../phase-07-airflow-cosmos.md)
- [DuckDB 1.5 concurrency documentation](https://duckdb.org/docs/1.5/connect/concurrency)
