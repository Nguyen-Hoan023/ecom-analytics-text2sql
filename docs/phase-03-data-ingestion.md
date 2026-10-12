# Giai đoạn 3 — SQL Server sang DuckDB bằng DLT

**Trạng thái:** hoàn tất kết nối nguồn và lần nạp snapshot đầu tiên. Số dòng trong DuckDB khớp với SQL Server ở cả bốn bảng.

## Thông tin nguồn

- Host: `db.xomdata.com`, port `1433`
- Database: `xomdata_dataset`
- Schema: `e_commerce`
- Authentication: SQL Server Authentication
- Trust server certificate: `Yes` theo thông tin kết nối người dùng cung cấp

Username/password được giữ trong `.env` local; file này và DuckDB warehouse bị Git ignore.

## Kiểm tra nguồn và đối chiếu

- DNS phân giải được; TCP tới cổng `1433` thành công.
- `ingestion.check_source_connection` kết nối được và chạy `SELECT DB_NAME(), 1`.
- `ingestion.profile_source_tables` xác nhận schema, quyền đọc và row counts; profile nguồn ghi lúc `2026-10-12 13:12:25 UTC`.

| Bảng | SQL Server | DuckDB Bronze | Kết quả |
|---|---:|---:|---|
| `customer` | 17,415 | 17,415 | Khớp |
| `ecom_sales` | 51,290 | 51,290 | Khớp |
| `product` | 28,356 | 28,356 | Khớp |
| `region` | 3,828 | 3,828 | Khớp |

## Pipeline DLT

Entry point: `python -m ingestion.run_pipeline`.

- DLT `sql_database` dùng SQLAlchemy và driver `pymssql`; pipeline chỉ chọn bốn bảng đã xác nhận.
- Destination: `duckdb_warehouse/warehouse.duckdb`.
- Dataset/schema: `bronze`; tên bảng giữ theo source.
- Mỗi lần chạy là full snapshot với `write_disposition="replace"`, tránh cộng dồn bản sao khi chạy lại.
- Batch size: 10,000 dòng. Source engine yêu cầu mã hóa và đặt read-only intent.
- DLT metadata: `_dlt_id`, `_dlt_load_id`, cùng các bảng hệ thống `_dlt_*`.
- Kiểu dữ liệu quan trọng được giữ: `sales`, `discount`, `profit` là `DECIMAL(10,2)`; tọa độ là `DECIMAL(10,6)`; ngày là `DATE`.

Sau khi load, script so sánh số dòng mỗi bảng ở SQL Server và DuckDB; cả bốn bảng đều khớp. Dữ liệu chi tiết được nạp vào file local, chưa được commit hoặc push.

`Trust server certificate = Yes` giữ kết nối được mã hóa nhưng bỏ qua xác thực danh tính chứng chỉ. FreeTDS/pymssql điều khiển xác minh qua CA file; khi không cấu hình CA, FreeTDS chấp nhận chứng chỉ server. Với production nên xác thực chứng chỉ từ CA tin cậy.

## Chạy lại các bước

Kích hoạt venv `D:\E-Commerce project\.venv`, chuyển tới thư mục repo rồi chạy:

```powershell
uv run --active python -m ingestion.check_source_connection
uv run --active python -m ingestion.profile_source_tables
uv run --active python -m ingestion.run_pipeline
```

## Tiếp theo: giai đoạn dbt

1. Khai báo bốn bảng Bronze là sources trong dbt.
2. Xây Silver models để chuẩn hóa tên cột và kiểu dữ liệu; thêm tests `not_null`, `unique`, relationships.
3. Giữ các sales rows có product/region không khớp để xử lý theo metric contract.
4. Sau khi so sánh Silver với profile nguồn, xây Gold marts cho 15 câu hỏi business.

Chưa chọn incremental load: nguồn chưa có `updated_at` đáng tin cậy để nhận diện bản ghi bị sửa.
