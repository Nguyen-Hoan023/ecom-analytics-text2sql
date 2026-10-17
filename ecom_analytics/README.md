\# E-Commerce Analytics dbt project



Project này dùng dbt để transform dữ liệu Bronze trong DuckDB thành các tầng Silver, Intermediate và Gold.



\## Model layers



\- \*\*Sources:\*\* Bốn bảng Bronze được DLT nạp từ SQL Server.

\- \*\*Staging:\*\* `stg\_customers`, `stg\_ecom\_sales`, `stg\_products`, `stg\_regions`.

\- \*\*Intermediate:\*\* `int\_sales\_enriched`, kết hợp giao dịch với customer, product và region.

\- \*\*Marts:\*\* Các model Gold phục vụ phân tích doanh số, discount, đơn lỗ, RFM, theo tháng và hiệu suất sản phẩm.



\## Chạy dbt



Activate môi trường ảo trước, sau đó chạy các lệnh từ thư mục này:



```powershell

uv run --active dbt parse

uv run --active dbt run

uv run --active dbt test

uv run --active dbt show --select mart\_sales\_by\_segment

