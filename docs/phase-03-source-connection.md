# Giai đoạn 3 — kết nối nguồn SQL Server

**Trạng thái:** đã cấu hình các giá trị không bí mật trong `.env` local và xác nhận DNS/TCP; chưa xác thực SQL vì password chưa được điền.

## Thông tin nguồn

- Host: `db.xomdata.com`
- Port: `1433`
- Database: `xomdata_dataset`
- Schema chứa dữ liệu: `e_commerce`
- Authentication: SQL Server Authentication
- Trust server certificate: `Yes` theo thông tin kết nối người dùng cung cấp

Không ghi username/password vào tài liệu hoặc Git. `.env` trong repo bị Git ignore; password phải được điền trực tiếp vào file đó trên máy local.

## Kiểm tra đã thực hiện

- DNS `db.xomdata.com` phân giải tới `45.124.94.158`.
- TCP tới `db.xomdata.com:1433` thành công.
- Chưa gửi thông tin đăng nhập hay câu lệnh SQL tới server.

## Chạy kiểm tra đăng nhập

1. Mở `.env` ở thư mục gốc repo và điền `XOM_SQLSERVER_PASSWORD` bằng password thật. Không gửi password qua chat, không commit file này.
2. Kích hoạt venv riêng hiện có ở `D:\E-Commerce project\.venv` nếu shell chưa dùng nó.
3. Từ thư mục repo, chạy:

```powershell
uv run --active python -m ingestion.check_source_connection
```

Script dùng `pymssql`, yêu cầu mã hóa kết nối (`encryption="require"`) và chỉ chạy `SELECT DB_NAME(), 1`. Nó không ghi dữ liệu, không tải bảng và che username/password nếu driver đưa chúng vào thông báo lỗi.

`Trust server certificate = Yes` giữ kết nối được mã hóa nhưng bỏ qua việc xác thực danh tính chứng chỉ. Với FreeTDS/pymssql, hành vi chứng chỉ được cấu hình qua CA file; khi chưa cấu hình CA, FreeTDS chấp nhận chứng chỉ server. Đây là cách tương ứng với môi trường học tập hiện tại; với hệ thống production nên xác thực chứng chỉ do CA tin cậy cấp.

## Sau khi đăng nhập thành công

1. Kiểm tra quyền `SELECT` trên `customer`, `ecom_sales`, `product`, `region`.
2. Ghi nhận số dòng và cấu trúc nguồn trước khi load.
3. Xây DLT pipeline snapshot đầu tiên vào DuckDB; so sánh row counts sau load với source profile.
4. Giữ nguyên các sales rows có product/region không khớp để downstream có thể quan sát và xử lý theo metric contract.

Chưa chọn incremental load: nguồn chưa có cột `updated_at` đáng tin cậy để nhận diện bản ghi bị sửa.
