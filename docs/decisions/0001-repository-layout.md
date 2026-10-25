# ADR 0001: Giữ cấu trúc modular monorepo hiện tại

- **Trạng thái:** Accepted
- **Ngày:** 2026-10-25
- **Phạm vi:** Repository layout and module boundaries

## Bối cảnh

Project có nhiều vai trò nhưng quy mô vẫn phù hợp với một repository: nạp nguồn,
transform dbt, phân tích, Text-to-SQL và điều phối. Mục tiêu là làm rõ ownership,
giảm file local/generated lọt vào Git hoặc Docker, và giữ workflow hiện đã được
nghiệm thu có thể chạy lại.

## Quyết định

Giữ **modular monorepo** và giữ nguyên các đường dẫn module đang được gọi trực tiếp.
Không chuyển code sang `src/`, không tách repository và không đổi công nghệ trong
Phase 8.1–8.2.

| Đường dẫn | Trách nhiệm | Phân loại |
|---|---|---|
| `ingestion/` | Kết nối nguồn, profiling metadata, DLT pipeline và cấu hình nguồn | Source code |
| `ecom_analytics/` | dbt sources, staging, intermediate, Gold marts, tests và profile template | Source code + local dbt artifacts |
| `text2sql/` | Catalog/policy, validation, executor, Gemini adapter, CLI/UI và evaluation | Source code |
| `analytics/visualization/` | Đọc Gold marts và sinh bộ biểu đồ tĩnh | Source code |
| `orchestration/` | Astro project, DAG, Docker config, staging helper và DAG contract tests | Source/config; `include/runtime/` là generated |
| `tests/` | Unit/integration-style tests cho Python services | Test code |
| `sql/` | SQL profiling nguồn có thể chạy lại, không phải dbt model | Analysis source |
| `docs/` | Data and metric contracts, architecture, decisions, and operating guides | Documentation/evidence |
| `reports/text2sql-evaluation/` | JSON evaluation đã sanitize, có thể dùng làm evidence lịch sử | Checked-in evidence |
| `docs/assets/charts/` | Ảnh chart Gold được README và report nhúng | Checked-in generated artifact |
| `.venv/`, `.env`, `duckdb_warehouse/`, `logs/`, caches | Môi trường, secrets, database hoặc output runtime trên máy phát triển | Local/generated; ignored |

## Vì sao chưa di chuyển thư mục

Các vị trí hiện tại là một phần của runtime contract, không chỉ là cách sắp xếp:

- Lệnh và import hiện tại dùng `python -m ingestion...` và `python -m text2sql...`
  từ repository root.
- `ecom_analytics/dbt_project.yml` là điểm vào của dbt; Cosmos được cấu hình với
  project/profile trong cây runtime đã stage.
- `orchestration/scripts/prepare_runtime.py` xác định repo root theo vị trí file,
  staging allowlist ba module và dbt project, rồi sinh container profile.
- Dockerfile, Compose mounts và DAG cùng tham chiếu tới các đường dẫn stage và
  `/usr/local/airflow/...` cụ thể.
- `pyproject.toml` khai báo project ứng dụng với `tool.uv.package = false`; chưa có
  nhu cầu đóng gói các module thành một Python library.

Một lần chuyển path cần cập nhật đồng bộ imports/entry points, dbt project/profile,
Dockerfile, Compose, DAG, staging helper, tests và tài liệu. Tác vụ đó không tạo giá
trị đủ lớn ở thời điểm hiện tại để bù rủi ro làm hỏng pipeline đã chạy thành công.

## Hợp đồng tổ chức

1. Mỗi top-level module giữ một trách nhiệm nghiệp vụ/runtime như bảng ownership.
2. Không đặt `.env`, `profiles.yml` local, DuckDB warehouse, dbt target/logs, Astro
   staging hoặc logs trong source/evidence được commit.
3. Chỉ `profiles.yml.example` là template dbt container có thể chia sẻ; profile máy
   Windows và `.user.yml` là local metadata.
4. Runtime staging chỉ nhận file qua allowlist; tên file local-only cũng bị từ chối
   tại bước validation sau copy.
5. Chỉ xem xét chuyển thư mục khi có nhu cầu cụ thể và có bảng old path → new path,
   toàn bộ references cần sửa, và kiểm tra hồi quy cho host lẫn Astro container.

## Hệ quả

- Cây thư mục giữ ổn định, dễ tiếp tục học theo từng module và không cần cập nhật DAG.
- Cleanup tập trung vào metadata/generated files, tài liệu, lệnh khởi chạy và CI.
- Khi quy mô tăng, có thể bổ sung subdirectory bên trong module (ví dụ
  `text2sql/evaluation/`) mà không đổi root import contract.

## Bằng chứng và liên kết

- [Sơ đồ kiến trúc](../architecture.md)
- [Operating model and orchestration](../../orchestration/README.md)
- [Runtime acceptance evidence](../../reports/orchestration/workflow-acceptance.md)
