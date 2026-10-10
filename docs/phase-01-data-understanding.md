# Giai đoạn 1 — Hiểu nguồn dữ liệu và chốt data contract

**Trạng thái:** đã chuẩn bị tài liệu và SQL profile; chưa chạy truy vấn trên SQL Server thật.

## 1. Mục tiêu và phạm vi

Trước khi viết DLT hoặc dbt, cần xác nhận ý nghĩa và chất lượng của các bảng nguồn: mỗi dòng đại diện cho điều gì, khóa nào có thể dùng, các bảng nối với nhau ra sao, giá trị có hợp lệ không và dữ liệu bao phủ khoảng thời gian nào.

Đầu ra giai đoạn này là:

1. Danh mục bảng/cột nguồn đã đối chiếu.
2. Grain, khóa ứng viên và quan hệ join được kiểm chứng.
3. Baseline chất lượng dữ liệu: null, trùng khóa, orphan join, miền giá trị và thời gian.
4. Từ điển KPI và các giả định cần giữ nhất quán ở dbt/Gold.
5. Danh sách rủi ro, quyết định và câu hỏi còn bỏ ngỏ.

Luồng công nghệ vẫn theo reference: SQL Server → DLT → DuckDB → dbt Bronze/Silver/Gold → phân tích/Text-to-SQL; Airflow/Cosmos sẽ được thêm sau khi từng phần chạy độc lập. Giai đoạn này chưa thay đổi stack.

## 2. Những gì schema công bố

Trang Xóm Dataset hiện liệt kê 4 bảng, tổng 100.889 dòng và 34 cột. Số dòng từng bảng trên trang được làm tròn, chỉ dùng để định hướng chứ không dùng làm tiêu chí đối soát tuyệt đối.

| Bảng | Số dòng công bố | Số cột | Grain / khóa ứng viên cần kiểm tra |
|---|---:|---:|---|
| e_commerce.customer | khoảng 17,4K | 11 | Một dòng trên mỗi customer_id |
| e_commerce.ecom_sales | khoảng 51,3K | 11 | Một dòng trên mỗi row_id; có thể là dòng hàng trong đơn, không phải một đơn |
| e_commerce.product | khoảng 28,4K | 4 | Một dòng trên mỗi product_code |
| e_commerce.region | khoảng 3,8K | 8 | Một dòng trên mỗi region_code |

Schema đánh dấu customer_id, row_id, product_code và region_code là NOT NULL, nhưng không khai báo foreign key trực tiếp. Vì vậy, tính duy nhất của khóa, grain của bảng giao dịch và các quan hệ bên dưới vẫn là giả thuyết cho đến khi chạy profile.

### Danh mục cột

- customer: customer_id, first_name, last_name, birth_date, marital_status, gender, email_address, annual_income, education_level, occupation, home_owner.
- ecom_sales: row_id, order_id, order_date, customer_id, segment, region_code, product_code, quantity, sales, discount, profit.
- product: product_code, product, category, subcategory.
- region: region_code, city, state, country, country_latitude, country_longitude, region, market.

## 3. Các điểm lệch cần giải quyết trước khi modeling

1. context.md của repo tham khảo mô tả segment/địa chỉ như thuộc tính customer, nhưng schema customer được công bố không có hai thông tin đó. Segment nằm trên ecom_sales; địa lý được thể hiện qua region và region_code của giao dịch. Không tự tạo hoặc gán ngược thuộc tính customer.
2. Trang schema ghi product có khoảng 28,4K dòng, trong khi business context nói khoảng 1.900 SKU. Số dòng không đồng nghĩa số mã sản phẩm duy nhất. Cần so sánh COUNT(*) với COUNT(DISTINCT product_code), kiểm tra khóa trùng và xác định đây là dimension nhiều bản ghi, snapshot khác nhau hay tài liệu chưa đồng bộ.
3. Các log và tổng doanh thu/lợi nhuận trong README reference là kết quả của một lần chạy cụ thể, không phải baseline hiện tại. Ghi lại ngày profile, số dòng chính xác và tổng số đo từ chính tài khoản dữ liệu của dự án này.
4. Business context nói có discount cao và đơn âm lợi nhuận. Đây là giả thuyết cần đo, không phải kết quả để sao chép vào phân tích cuối.

## 4. Sơ đồ quan hệ tạm thời

```text
ecom_sales.customer_id  → customer.customer_id
ecom_sales.product_code → product.product_code
ecom_sales.region_code  → region.region_code
```

Với từng quan hệ, cần ghi lại: (a) số dòng fact có khóa null, (b) số khóa khác null nhưng không tìm thấy dimension tương ứng, (c) số khóa dimension bị trùng và (d) số dòng sau join có giữ nguyên so với fact hay không. Không xây join cuối cùng nếu khóa dimension chưa duy nhất, trừ khi đã xác định quy tắc xử lý trùng.

## 5. Định nghĩa nghiệp vụ tạm thời

Đây là hợp đồng ban đầu. Cần đối chiếu ý nghĩa dữ liệu sau khi profile và ghi lại mọi thay đổi trước khi triển khai trong Gold.

| Chỉ số | Định nghĩa đề xuất | Lưu ý |
|---|---|---|
| Revenue | SUM(sales) ở grain dòng hàng | Xác minh sales đã là doanh thu dòng hàng hay còn cần nhân quantity. |
| Profit | SUM(profit) ở grain dòng hàng | Giữ giá trị âm, không lọc bỏ dòng lỗ. |
| Profit margin | SUM(profit) / NULLIF(SUM(sales), 0) | Không lấy trung bình margin từng dòng; luôn ghi rõ mẫu số và kỳ phân tích. |
| Units | SUM(quantity) | Kiểm tra null, 0 và quantity âm trước. |
| Discount trung bình | AVG(discount) trên các dòng hợp lệ, nhóm theo category | Xác minh discount là tỷ lệ 0–1 hay điểm phần trăm 0–100 trước khi gắn nhãn %. |
| Dòng hàng lỗ | Dòng có profit < 0 | Tách riêng với đơn hàng lỗ. |
| Đơn hàng lỗ | Tổng profit các dòng cùng order_id < 0 | Gom theo order trước, sau đó mới đếm đơn theo segment ở cấp giao dịch. |
| Segment | ecom_sales.segment tại từng dòng giao dịch | Không coi đây là thuộc tính cố định của customer theo schema đã công bố. |
| Giá trị tiền tệ trong RFM | Tạm đề xuất tổng sales theo customer; cần cân nhắc sales hay profit | Frequency đếm order_id khác null, không đếm số dòng. Mốc snapshot tái lập được là MAX(order_date) + 1 ngày, trừ khi chọn ngày báo cáo khác. |
| VIP/churn risk | Heuristic được mô tả rõ, kết hợp giá trị khách hàng và thời gian không hoạt động | Dataset không có nhãn churn quan sát được; chỉ gọi là cờ rủi ro, không tuyên bố là dự đoán churn đã được kiểm chứng. |
| Tác động discount | So sánh mô tả giữa các nhóm discount, số đơn và margin | Dữ liệu quan sát không chứng minh discount gây ra thay đổi lợi nhuận nếu không có counterfactual/thử nghiệm phù hợp. |

Khi phân tích market basket, trước self-join cần đưa dữ liệu về duy nhất một cặp (order_id, product_code) để số dòng lặp không làm tăng giả tạo số cặp sản phẩm. Nên báo cáo support, confidence, lift và ngưỡng minimum support đã chọn.

### Bản đồ 15 câu hỏi → dữ liệu và điểm cần chốt

| Q | Câu hỏi | Bảng / grain chính | Điều cần quyết định hoặc kiểm chứng |
|---:|---|---|---|
| 1 | Tổng revenue và profit | ecom_sales, dòng hàng | Đối soát null, grain và cách cộng sales/profit. |
| 2 | Revenue theo segment | ecom_sales, dòng hàng | Xác nhận domain segment và segment có nhất quán trong cùng order hay không. |
| 3 | Top 10 sản phẩm bán chạy | ecom_sales + product | “Bán chạy” là theo units, số order hay revenue? Chọn và đặt tên chỉ số. |
| 4 | Số customer theo gender × occupation | customer, customer_id | Xác nhận customer_id duy nhất; xử lý unknown/null riêng. |
| 5 | Discount trung bình theo category | ecom_sales + product | Xác nhận scale discount và trung bình theo dòng hay theo order. |
| 6 | Profit margin theo market | ecom_sales + region | Dùng tổng profit chia tổng sales, không lấy trung bình margin từng dòng. |
| 7 | Số đơn lỗ theo segment | ecom_sales, gom theo order_id | Đơn lỗ khác dòng lỗ; kiểm tra order có nhiều segment không. |
| 8 | VIP có rủi ro churn | customer + ecom_sales | Chốt VIP, cửa sổ inactivity, snapshot date; đây là heuristic vì không có churn label. |
| 9 | Cross-sell Consumer vs Corporate | ecom_sales + product | Làm rõ so sánh danh mục/sản phẩm, mẫu số và cách tính share. |
| 10 | Top 15 quốc gia theo revenue | ecom_sales + region | Xử lý orphan region_code và cách chuẩn hóa tên country. |
| 11 | YoY revenue theo tháng | ecom_sales, order_date | Kiểm tra độ dài lịch sử, tháng thiếu và tháng có mẫu số năm trước bằng 0. |
| 12 | Top 3 sản phẩm profit cao nhất mỗi category | ecom_sales + product | Chốt tổng profit, cách xử lý tie và yêu cầu đủ 3 sản phẩm/category. |
| 13 | Customer mua tại nhiều region | ecom_sales, customer_id + region_code | Xác định region hay market là mức địa lý cần so sánh; mỗi key phải có ý nghĩa ổn định. |
| 14 | RFM segmentation | ecom_sales, customer/order | Chốt recency reference date, frequency theo order, monetary theo sales hay profit, và cách chấm điểm. |
| 15 | Sản phẩm thường được mua cùng nhau | ecom_sales, order_id + product_code | Khử trùng cặp trong order; báo support/confidence/lift và ngưỡng minimum support. |

Các câu hỏi này là scope nghiệp vụ cho Gold marts và Text-to-SQL evaluation sau này. Chưa nên viết SQL trả lời từng câu trước khi các điểm về grain, metric, join và mẫu số được chốt.

## 6. Cách chạy profile nguồn

1. Mở SSMS, DBeaver hoặc DataGrip và tự kết nối SQL Server Xóm bằng credentials của bạn.
2. Chọn database chứa schema e_commerce.
3. Mở file ../sql/phase_01_profile.sql và chạy nguyên trạng trước. File chỉ có SELECT, không tạo hoặc sửa object ở nguồn.
4. Ghi lại số dòng chính xác, số khóa trùng, null, khoảng ngày, khoảng discount, tỷ lệ join và phân bố các giá trị.
5. Không đưa credentials, tên/email khách hàng hoặc trích xuất dòng dữ liệu thô vào Git. Chỉ ghi kết quả tổng hợp cần thiết.
6. Đối chiếu checklist bên dưới, cập nhật quyết định và bằng chứng. Chỉ đánh dấu hoàn tất sau khi có kết quả thật.

Trang schema có thể đọc công khai, nhưng truy vấn SQL Server thật cần credentials do Xóm cấp. Credentials không được lưu trong repo và cũng không cần gửi vào cuộc chat này.

## 7. Checklist và decision log

Chỉ điền cột Quan sát sau khi chạy SQL profile. “Đang chờ” không có nghĩa là giá trị bằng 0.

| Kiểm tra | Tiêu chí / quyết định | Quan sát |
|---|---|---|
| Schema thực tế | Tên cột và kiểu dữ liệu khớp; giải thích cột thêm, mất hoặc đổi kiểu | Đang chờ |
| Số dòng | Ghi số chính xác của cả 4 bảng và thời điểm profile | Đang chờ |
| Khóa ứng viên | Khóa đề xuất không null và không có giá trị trùng | Đang chờ |
| Grain ecom_sales | row_id nhận diện một dòng; order_id lặp khi đơn có nhiều dòng hàng | Đang chờ |
| Referential integrity | Biết số dòng có khóa null và orphan cho cả 3 quan hệ | Đang chờ |
| Cột đo lường | Biết null, âm, 0 và range của quantity, sales, discount, profit | Đang chờ |
| Đơn vị discount | Xác minh tỷ lệ và range qua min/max cùng giá trị quan sát | Đang chờ |
| Độ phủ ngày | Biết ngày đầu/cuối, tháng thiếu và dữ liệu có đủ lịch sử để tính YoY | Đang chờ |
| Miền category/segment/market | Kiểm tra giá trị khác nhau, null, lỗi chính tả và khác biệt viết hoa | Đang chờ |
| Metric contract | Chốt revenue, profit, margin, đơn lỗ, RFM snapshot và churn heuristic | Đang chờ |
| Lệch so với reference | Đối soát thuộc tính customer, số dòng sản phẩm/SKU và log cũ; hoặc ghi rõ chưa giải quyết | Đang chờ |

### Decision log

| Ngày | Câu hỏi / phát hiện | Bằng chứng | Quyết định / tác động |
|---|---|---|---|
| Chưa chạy | Chưa có profile từ SQL Server thật | Workspace hiện chưa có credentials nguồn | Giữ mọi số đo và kết luận chất lượng ở trạng thái chờ; cần chạy script trước khi chốt thiết kế ingestion ở giai đoạn 2. |

## 8. Điều kiện hoàn thành giai đoạn 1

Chỉ chuyển sang giai đoạn 2 khi:

- đã ghi nhận schema thực tế và số dòng chính xác của bốn bảng;
- grain và trạng thái khóa ứng viên của từng bảng có bằng chứng;
- đã lượng hóa join coverage và nguy cơ fan-out;
- đã hiểu scale discount, khoảng ngày, null/âm của các cột đo và domain category/segment/market;
- đã thống nhất định nghĩa metric, ghi rõ giả định và câu hỏi còn mở;
- không có credentials, database cục bộ hay PII khách hàng trong commit.

## Nguồn tham khảo

- [Tổng quan dataset Xóm E-Com và 15 câu hỏi nghiệp vụ](https://dataset.xomdata.com/datasets/schema/e_commerce)
- [Schema customer](https://dataset.xomdata.com/datasets/e_commerce.customer)
- [Schema ecom_sales](https://dataset.xomdata.com/datasets/e_commerce.ecom_sales)
- [Schema product](https://dataset.xomdata.com/datasets/e_commerce.product)
- [Schema region](https://dataset.xomdata.com/datasets/e_commerce.region)
- [README repo tham khảo](https://github.com/tunguyenn99/a-simple-t2s-flow)
- [context.md của repo tham khảo](https://github.com/tunguyenn99/a-simple-t2s-flow/blob/main/context.md)
