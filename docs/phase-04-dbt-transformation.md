\# Giai đoạn 4 — Transform dữ liệu với dbt



\*\*Trạng thái:\*\* Đã triển khai Silver, Intermediate và sáu Gold marts. Tiếp tục hoàn thiện các câu hỏi nghiệp vụ còn lại.



\## Luồng dữ liệu



SQL Server → DLT → DuckDB Bronze → dbt Silver → Intermediate → Gold



\## Các tầng model



\- \*\*Bronze:\*\* Bốn bảng nguồn được DLT nạp vào DuckDB.

\- \*\*Silver:\*\* `stg\_customers`, `stg\_ecom\_sales`, `stg\_products`, `stg\_regions`.

\- \*\*Intermediate:\*\* `int\_sales\_enriched`, ghép giao dịch với customer, product và region.

\- \*\*Gold:\*\* Các marts phục vụ phân tích nghiệp vụ.



\## Gold marts hiện có



| Model | Nội dung |

|---|---|

| `mart\_sales\_by\_segment` | Sales và profit theo segment |

| `mart\_discount\_profitability` | Profitability theo discount band và category |

| `mart\_loss\_making\_orders\_by\_segment` | Đơn lỗ theo segment |

| `mart\_customer\_rfm` | RFM, VIP và tín hiệu churn heuristic |

| `mart\_monthly\_sales` | Kết quả theo tháng và YoY |

| `mart\_product\_performance` | Hiệu suất sản phẩm và xếp hạng profit theo category |



\## Kết quả kiểm tra đã xác nhận



\- `dbt parse` chạy thành công.

\- Source tests: 8/8 pass.

\- `stg\_customers`: 2/2 tests pass.

\- `stg\_ecom\_sales`: 2/2 tests pass.

\- `int\_sales\_enriched`: 3/3 tests pass.

\- Các Gold marts đã được chạy riêng và kết quả được xem lại bằng `dbt show`.



Chưa ghi rằng toàn bộ project đã qua `dbt build` nếu chưa chạy lệnh đó.



\## Lưu ý về dữ liệu và metric



\- `ecom\_sales` có 51.290 dòng; grain là một dòng trên mỗi `row\_id`.

\- Có 3 dòng giao dịch duy nhất thiếu product/region match; giữ chúng để đối soát, không tự đoán mã dimension thay thế.

\- Category/subcategory nguồn có một số dấu hiệu không nhất quán. Giữ nguyên taxonomy nguồn và thận trọng khi diễn giải kết quả theo category.

\- Ý nghĩa gross/net của `sales` chưa được nguồn xác nhận.

\- Churn là heuristic theo snapshot lịch sử, không phải nhãn churn thực tế.



\## Các câu hỏi còn cần triển khai



Customer profile (Q4), market/country (Q6, Q10), category mix theo segment (Q9), customer mua ở nhiều region (Q13) và market-basket (Q15).



\## Cách chạy dbt



Mở PowerShell tại thư mục `ecom\_analytics`, activate môi trường ảo như các lần chạy trước, sau đó dùng:



```powershell

uv run --active dbt parse

uv run --active dbt run --select mart\_sales\_by\_segment

uv run --active dbt show --select mart\_sales\_by\_segment

