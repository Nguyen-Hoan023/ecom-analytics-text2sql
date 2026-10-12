# Giai đoạn 1 — Hiểu nguồn dữ liệu và chốt data contract

**Trạng thái:** source profile và metric contract v1 đã được ghi nhận. Mốc profile là `2026-10-10 14:25:29.4548071 UTC`. Các giả định về ý nghĩa `sales`, ngưỡng VIP/churn và một số câu hỏi phân tích đã được chốt làm mặc định v1, đồng thời được đánh dấu để kiểm chứng khi phân tích.

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

### Baseline profile

Mốc chạy profile được ghi nhận: **2026-10-10 14:25:29.4548071 UTC**. Các aggregate dưới đây là những kết quả đã được chia sẻ; nếu lần chạy có timestamp này cho kết quả khác, cập nhật các giá trị theo output mới để chúng cùng thuộc một snapshot.

| Bảng / phép đo | Kết quả quan sát |
|---|---|
| Row count | customer 17.415; ecom_sales 51.290; product 28.356; region 3.828. Tổng 100.889, khớp tổng số dòng công bố. |
| Schema | Tên cột và nullability khớp schema công bố. sales/discount/profit là decimal(10,2); tọa độ là decimal(10,6). |
| Candidate keys | Cả 4 khóa đều có non-null = distinct = row count; các query duplicate không trả dòng nào. |
| ecom_sales grain | 51.290 dòng; 25.728 order_id khác null; không null order_id/order_date. Có 12.935 đơn một dòng, 12.793 đơn nhiều dòng; tối đa 14 dòng/đơn. |
| Số đo giao dịch | quantity: 1–20; sales: 2–3.940; profit: -1.746 đến 1.820. Các cột quantity/sales/profit không có null; không có quantity hoặc sales bằng 0/âm. Có 11.041 dòng profit âm. |
| Discount | Không có null; min 0, max 0,85, avg 0,142883. Kết quả phù hợp với cách lưu theo tỷ lệ 0–1; trung bình tương đương khoảng 14,29%, tối đa 85%. Có 29.470 dòng discount bằng 0. |
| Segment | Consumer: 26.518 dòng, sales 2.146.780, profit 365.377,50; Corporate: 15.429, sales 3.840.707, profit 608.523,36; Self-Employed: 9.343, sales 530.187, profit 91.512,72. Số dòng cộng đúng 51.290; sales 6.517.674, profit 1.065.413,58. |
| Lỗ theo đơn | 5.496/25.728 đơn có tổng profit âm. Không có đơn thiếu profit hoặc thiếu segment; không có order chứa nhiều segment. |
| Thời gian | Từ 2020-01-01 đến 2023-12-31; kết quả có đủ 48 tháng liên tục. |
| customer.gender | Kết quả được gửi cho thấy 124/17.415 giá trị null (khoảng 0,71%). Cần xác nhận đây là cột duy nhất có null trong output đầy đủ. |
| Join coverage | Không có fact key null. Customer orphan 0; product orphan 2; region orphan 2. Hai tập trùng 1 dòng, tổng cộng 3 dòng fact duy nhất ảnh hưởng, sales 506 và profit 253. |
| Market / region | 23 cặp market-region; tổng 3.828 region rows và 3.828 region_code phân biệt. Africa 321; Asia Pacific 931; Europe 1.281; LATAM 645; USCA 650. Trong từng cặp, region_rows = distinct_region_codes. |

Product có 28.356 product_code duy nhất. Các danh mục quan sát là Body care, Face care, Hair care, Home and Accessories, Make up; đây không phải Office Supplies/Furniture/Technology như mô tả context.

Tổng product theo category từ kết quả 17 nhóm category/subcategory: Body care 11.548; Face care 1.885; Hair care 4.070; Home and Accessories 5.912; Make up 4.941. Tổng 28.356. Trong từng nhóm category/subcategory, product_rows bằng distinct_product_codes.

Miền địa lý có 5 market (Africa, Asia Pacific, Europe, LATAM, USCA) và 23 region. Tổng theo market cộng đúng 3.828 region_code. Kết quả chỉ xác nhận miền giá trị và tính duy nhất của region_code theo từng cặp market-region; chưa xác nhận tính đúng đắn địa lý bên ngoài nguồn.

Chi tiết orphan từ query 9a: product_code PPP000002 có 1 dòng (2021-09-01, sales 20, profit 10); product_code PPP000010 có 1 dòng (2020-04-04, sales 70, profit 35); region_code RRR0001 có 2 dòng (2020-04-04, sales 486, profit 243). Có 1 dòng vừa thiếu product vừa thiếu region, nên tổng ảnh hưởng duy nhất là 3 dòng, sales 506, profit 253. Không có cơ sở để suy đoán mã dimension thay thế.

### Danh mục cột

- customer: customer_id, first_name, last_name, birth_date, marital_status, gender, email_address, annual_income, education_level, occupation, home_owner.
- ecom_sales: row_id, order_id, order_date, customer_id, segment, region_code, product_code, quantity, sales, discount, profit.
- product: product_code, product, category, subcategory.
- region: region_code, city, state, country, country_latitude, country_longitude, region, market.

## 3. Các điểm lệch cần giải quyết trước khi modeling

1. context.md của repo tham khảo mô tả segment/địa chỉ như thuộc tính customer, nhưng schema customer không có hai thông tin đó. Segment nằm trên ecom_sales; địa lý nằm ở region và region_code của giao dịch. Không tự tạo hoặc gán ngược thuộc tính customer.
2. Dataset live có 28.356 product_code duy nhất và các category thuộc nhóm chăm sóc cá nhân/mỹ phẩm; mô tả khoảng 1.900 SKU và Office/Furniture/Technology không khớp. Với pipeline này, dùng schema và giá trị quan sát từ nguồn đang kết nối làm căn cứ; ghi phần context web là chưa đồng bộ cho tới khi xác minh được snapshot/phiên bản.
3. Segment live có Consumer, Corporate, Self-Employed; context ghi Home Office. Giữ đúng giá trị nguồn, không đổi Self-Employed thành Home Office nếu chưa có mapping chính thức.
4. Sales/profit cộng theo segment là 6.517.674 và 1.065.413,58, khớp tổng trong README tham khảo. Dữ liệu bao phủ bốn năm; không diễn giải tổng này thành doanh thu một năm.
5. Discount live nằm trong 0–0,85 và có trung bình 0,142883; 11.041 dòng và 5.496 đơn có profit âm. Đây là baseline mô tả, chưa chứng minh discount gây ra lỗ.
6. Join coverage: customer khớp đủ; product và region mỗi quan hệ thiếu match cho 2 dòng fact, trong đó 1 dòng trùng ở cả hai nhóm. Nếu inner join cả hai dimension thì mất 3 dòng, sales 506 và profit 253. Giữ nguyên fact và mã nguồn; khi cần enrich hãy dùng left join, đánh dấu unmatched, và không tự suy đoán dimension.
7. Taxonomy địa lý live có 5 market và 23 region; các nhãn market quan sát được là Africa, Asia Pacific, Europe, LATAM và USCA. Không gộp/đổi tên nhãn theo context tham khảo khi chưa có mapping chính thức; dùng taxonomy live làm dữ liệu đầu vào cho modeling và ghi rõ phạm vi so sánh.
8. Taxonomy sản phẩm có dấu hiệu không nhất quán: truy vấn đối chiếu `stg_products` cho thấy một số mã có tên sản phẩm và category/subcategory không ăn khớp, ví dụ P000115 (Body care / hand creams), P000222 (Make up / Eye shadows and pencils), P002156 (Face care / face moisturizing products), P002215 (Hair care / hair colors and toners). Đây là giá trị lấy từ dimension nguồn. Giữ nguyên nhãn nguồn, không tự sửa category dựa trên tên sản phẩm. Vì vậy, các phân tích gộp theo category cần được xem là tạm thời cho tới khi có mapping đáng tin cậy. Trong `mart_product_performance`, giữ sản phẩm `Unknown` để đối soát nhưng không xếp hạng chúng trong Top sản phẩm theo category.
## 4. Sơ đồ quan hệ tạm thời

```text
ecom_sales.customer_id  → customer.customer_id
ecom_sales.product_code → product.product_code
ecom_sales.region_code  → region.region_code
```

Với từng quan hệ, cần ghi lại: (a) số dòng fact có khóa null, (b) số khóa khác null nhưng không tìm thấy dimension tương ứng, (c) số khóa dimension bị trùng và (d) số dòng sau join có giữ nguyên so với fact hay không. Không xây join cuối cùng nếu khóa dimension chưa duy nhất, trừ khi đã xác định quy tắc xử lý trùng.

## 5. Metric contract v1 và giả định nghiệp vụ

Contract này là bộ quy tắc chung cho SQL phân tích, dbt Gold, dashboard và Text-to-SQL. “Grain” là đơn vị mà mỗi dòng dữ liệu đại diện. Quy tắc đã chốt cho v1 được áp dụng nhất quán; những điều chưa được tài liệu nguồn xác nhận được ghi là giả định và cần kiểm tra lại bằng phân tích độ nhạy.

| Metric / chủ đề | Grain | Quy tắc v1 | Trạng thái / giả định |
|---|---|---|---|
| Sales / Revenue | Dòng hàng (`row_id`) | `SUM(sales)`; không nhân thêm `quantity`; luôn ghi kỳ phân tích. | Quy ước v1. Coi `sales` là số tiền ở dòng hàng theo nguồn. Nguồn hiện chưa xác nhận đó là gross hay net; không gắn nhãn net revenue. |
| Profit | Dòng hàng (`row_id`) | `SUM(profit)`; giữ cả giá trị âm. | Đã chốt v1; không lọc bỏ dòng/đơn lỗ. |
| Profit margin | Nhóm báo cáo, ví dụ market-tháng | `SUM(profit) / NULLIF(SUM(sales), 0)`; định dạng phần trăm khi trình bày. | Đã chốt v1; đây là margin gia quyền theo sales, không phải trung bình margin từng dòng. |
| Units sold | Sản phẩm/kỳ | `SUM(quantity)`. | Đã chốt v1; dùng làm nghĩa “bán chạy” chính. Revenue có thể là chỉ số phụ với nhãn riêng. |
| Average discount | Category hoặc nhóm khác, trọng số dòng hàng | `AVG(discount)`; giữ discount bằng 0; nhân 100 khi trình bày %. | Giả định v1: mỗi dòng hàng có trọng số ngang nhau, không phải mỗi đơn. Nguồn lưu tỷ lệ 0–1; profile thấy avg 0,142883 và max 0,85. |
| Loss-making line | Dòng hàng | Dòng có `profit < 0`. | Đã chốt v1; tách biệt với đơn hàng lỗ. |
| Loss-making order | Đơn (`order_id`) | Cộng `profit` các dòng trong đơn; đơn lỗ khi tổng `< 0`; đếm mỗi đơn một lần. | Đã chốt v1; profile quan sát 5.496/25.728 đơn lỗ. |
| Order count | Nhóm báo cáo | `COUNT(DISTINCT order_id)`. | Đã chốt v1; không dùng số dòng hàng thay cho số đơn. |
| Segment attribution | Dòng giao dịch/đơn | Dùng `ecom_sales.segment` từ dòng giao dịch. | Đã chốt v1; không xem segment là thuộc tính cố định của customer. Profile không thấy đơn có nhiều segment. |
| Dimension join | Dòng fact | Dùng `LEFT JOIN`; giữ giao dịch không khớp và gắn `Unknown/Unmatched`. | Đã chốt v1; không tự ánh xạ product/region orphan và không làm mất doanh thu khi enrich. |
| RFM | Customer có giao dịch | Recency = số ngày từ lần mua gần nhất đến snapshot; Frequency = số `order_id` khác nhau; Monetary = `SUM(sales)`. | Đã chốt v1. Snapshot = `MAX(order_date) + 1 ngày` để tái lập; với dữ liệu hiện tại là 2024-01-01. Customer không có đơn được giữ trong population nhưng không chấm RFM. |
| RFM score / VIP | Customer có giao dịch | Chia Recency, Frequency, Monetary thành 5 nhóm (`NTILE(5)`); Recency thấp ngày được điểm cao, Frequency/Monetary lớn được điểm cao. VIP v1 = nhóm Monetary cao nhất (M=5). | Giả định v1; dùng `customer_id` làm tie-breaker ổn định. Các nhóm xấp xỉ quintile, không phải ngưỡng chi tiêu cố định. |
| Churn risk | Customer có giao dịch | Cờ rủi ro khi không có đơn trong ít nhất 90 ngày tính đến snapshot. VIP có rủi ro khi vừa là VIP vừa có cờ này. | Giả định v1, chỉ là heuristic vì dataset không có churn label. So sánh 60/90/180 ngày trước khi diễn giải. Snapshot 2024-01-01 nghĩa là đánh giá lịch sử, không phải churn hiện tại. |
| Discount impact | Dòng hàng / nhóm discount | So sánh sales, profit, margin và số đơn giữa các dải: 0%, (0–20%], (20–40%], (40–60%], >60%. | Phân tích mô tả. Không kết luận discount gây lỗ nếu không có thiết kế nhân quả/counterfactual. |
| Category mix theo segment | Category trong segment | `category_sales / segment_sales` để so sánh tỷ trọng sales category giữa Consumer và Corporate. | Giả định v1 cho câu hỏi cross-sell; đây là category mix, không chứng minh tác động cross-sell. |
| Market basket | Cặp sản phẩm trong đơn | Khử trùng về một cặp `(order_id, product_code)`; support = đơn chứa cả cặp / tổng đơn hợp lệ; confidence(A→B) = đơn chứa A và B / đơn chứa A; lift = confidence(A→B) / support(B). | Ngưỡng khám phá ban đầu: support ≥0,5% (khoảng 129/25.728 đơn theo baseline); tham số này cần sensitivity check. Giữ product_code nguồn nếu product orphan và gắn nhãn unmatched. |

Các giả định chính của v1 là: ý nghĩa gross/net của `sales` chưa được nguồn xác nhận; “bán chạy” được hiểu là units; average discount tính theo dòng; VIP là nhóm Monetary cao nhất; churn risk dùng inactivity 90 ngày; cross-sell được đại diện bằng category revenue mix; minimum support bắt đầu ở 0,5%. Mọi đầu ra phải ghi tên metric và kỳ phân tích để người đọc hiểu đúng phạm vi.

### Bản đồ 15 câu hỏi → quy ước v1

| Q | Câu hỏi | Bảng / grain chính | Quy ước v1 / cách xử lý |
|---:|---|---|---|
| 1 | Tổng revenue và profit | ecom_sales, dòng hàng | `SUM(sales)`, `SUM(profit)`; ghi rõ kỳ; không diễn giải tổng 4 năm thành doanh thu năm. |
| 2 | Revenue theo segment | ecom_sales, dòng hàng | `SUM(sales)` theo `ecom_sales.segment`; giữ giá trị segment nguồn. |
| 3 | Top 10 sản phẩm bán chạy | ecom_sales + product | Xếp theo `SUM(quantity)` giảm dần; revenue là metric phụ; tie-break bằng product_code. |
| 4 | Số customer theo gender × occupation | customer, customer_id | `COUNT(DISTINCT customer_id)`; giữ nhóm NULL/Unknown thay vì loại. |
| 5 | Discount trung bình theo category | ecom_sales + product | `AVG(discount)` theo dòng hàng; giữ zero; hiển thị phần trăm; product orphan vào Unknown. |
| 6 | Profit margin theo market | ecom_sales + region | `SUM(profit)/SUM(sales)`; left join và giữ nhóm market Unknown cho orphan region. |
| 7 | Số đơn lỗ theo segment | ecom_sales, gom theo order_id | Gom profit theo đơn, tổng `<0` là lỗ; segment được lấy từ fact. |
| 8 | VIP có rủi ro churn | customer + ecom_sales | VIP = M score 5; risk = không mua ≥90 ngày; snapshot `MAX(order_date)+1`; báo là heuristic và so sánh 60/180 ngày. |
| 9 | Cross-sell Consumer vs Corporate | ecom_sales + product | V1 so sánh category revenue share trong tổng sales của từng segment; gọi rõ là category mix. |
| 10 | Top 15 quốc gia theo revenue | ecom_sales + region | `SUM(sales)` theo country nguồn; giữ Unknown/unmatched riêng; không tự chuẩn hóa tên. |
| 11 | YoY revenue theo tháng | ecom_sales, order_date | Tổng sales theo tháng lịch; growth = `(sales_tháng_này / sales_cùng_tháng_năm_trước) - 1`; growth null nếu năm trước bằng 0. |
| 12 | Top 3 sản phẩm profit cao nhất mỗi category | ecom_sales + product | `SUM(profit)` theo product/category; xếp giảm dần, tie-break product_code để trả đúng 3 sản phẩm; product orphan vào category Unknown. |
| 13 | Customer mua tại nhiều region | ecom_sales, customer_id + region_code | Đếm `COUNT(DISTINCT region_code)` khớp dimension theo customer; đánh dấu riêng giao dịch orphan region. |
| 14 | RFM segmentation | ecom_sales, customer/order | Dùng công thức, snapshot và quintile scoring nêu trong contract v1. |
| 15 | Sản phẩm thường được mua cùng nhau | ecom_sales, order_id + product_code | Dedupe order-product; tính support/confidence/lift; bắt đầu support 0,5% và kiểm tra độ nhạy. |

Các câu hỏi này là scope nghiệp vụ cho Gold marts và Text-to-SQL evaluation sau này. Quy ước v1 ở trên là hợp đồng để bắt đầu modeling; khi phát hiện kết quả bất thường, cập nhật decision log và phiên bản contract trước khi đổi logic.

## 6. Cách chạy profile nguồn

1. Mở SSMS, DBeaver hoặc DataGrip và tự kết nối SQL Server Xóm bằng credentials của bạn.
2. Chọn database chứa schema e_commerce.
3. Mở file ../sql/phase_01_profile.sql và chạy nguyên trạng trước. File chỉ đọc dữ liệu (SELECT, cùng SET NOCOUNT ON), không tạo hoặc sửa object ở nguồn.
4. Ghi lại số dòng chính xác, số khóa trùng, null, khoảng ngày, khoảng discount, tỷ lệ join và phân bố các giá trị.
5. Không đưa credentials, tên/email khách hàng hoặc trích xuất dòng dữ liệu thô vào Git. Chỉ ghi kết quả tổng hợp cần thiết.
6. Đối chiếu checklist bên dưới, cập nhật quyết định và bằng chứng. Chỉ đánh dấu hoàn tất sau khi có kết quả thật.

Trang schema có thể đọc công khai, nhưng truy vấn SQL Server thật cần credentials do Xóm cấp. Credentials không được lưu trong repo và cũng không cần gửi vào cuộc chat này.

## 7. Checklist và decision log

Chỉ điền cột Quan sát sau khi chạy SQL profile. “Đang chờ” không có nghĩa là giá trị bằng 0.

| Kiểm tra | Tiêu chí / quyết định | Quan sát |
|---|---|---|
| Schema thực tế | Tên cột/nullability khớp; decimal(10,2), tọa độ decimal(10,6) | Đạt; mốc profile 2026-10-10 14:25 UTC |
| Số dòng | customer 17.415; sales 51.290; product 28.356; region 3.828; tổng 100.889 | Đạt theo output đã chia sẻ; mốc profile 2026-10-10 14:25 UTC |
| Khóa ứng viên | 4 khóa có non-null = distinct = row count; duplicate queries rỗng | Đạt theo output đã gửi |
| Grain ecom_sales | 51.290 dòng, 25.728 đơn, 12.793 đơn nhiều dòng, tối đa 14 dòng/đơn | Đạt cho grain; row_id được xác nhận duy nhất |
| Referential integrity | Biết null/orphan cho 3 quan hệ | Đã đo: customer 0/0; product 0/2; region 0/2 (null/orphan); orphan union 3 dòng, sales 506, profit 253 |
| Cột đo lường | Các cột fact profile không null; quantity/sales không âm hoặc bằng 0; profit âm có tồn tại | Đạt theo output đã gửi |
| Đơn vị discount | Range 0–0,85, avg 0,142883; 29.470/51.290 dòng có discount = 0 | Đạt; báo cáo theo phần trăm cần nhân 100 |
| Độ phủ ngày | 2020-01-01 đến 2023-12-31, có đủ 48 tháng | Đạt cho độ phủ tháng; đủ dữ liệu YoY |
| Miền category/segment/market | Category mỹ phẩm/chăm sóc cá nhân; segment Consumer/Corporate/Self-Employed; 5 market, 23 region, tổng 3.828 region_code | Đã đo; taxonomy market live khác các nhãn trong context tham khảo, không tự chuẩn hóa |
| Metric contract | Công thức, grain, join, ngưỡng VIP/churn, RFM, cross-sell và basket được ghi thành quy ước v1 | Đã chốt v1; ý nghĩa gross/net của sales và các ngưỡng heuristic cần kiểm chứng/sensitivity check |
| Lệch so với reference | Customer attributes, categories/SKU, segment khác context; tổng theo segment khớp README | Đã ghi lệch; cần xác nhận tài liệu mô tả cũ hay khác phiên bản |

### Decision log

| Ngày | Câu hỏi / phát hiện | Bằng chứng | Quyết định / tác động |
|---|---|---|---|
| 2026-10-10 | Profile ghi nhận 3 dòng fact duy nhất thiếu dimension match | Query 9a: product PPR000002/PPR000010; region RRR0001; 1 dòng trùng ở cả hai nhóm; sales ảnh hưởng 506, profit 253 | Không tự map mã; giữ fact và khóa nguồn, dùng left join/nhãn unmatched ở Silver/Gold để tránh mất số liệu. |
| 2026-10-10 | Domain market/region của nguồn live đã được gửi | 23 cặp market-region; Africa 321, Asia Pacific 931, Europe 1.281, LATAM 645, USCA 650; tổng 3.828; mỗi cặp không có trùng region_code | Giữ nhãn và cấp địa lý đúng như nguồn; chỉ tạo mapping sang context/reference nếu xác minh được quy tắc nghiệp vụ. |
| 2026-10-10 | Chốt metric contract v1 theo bộ quy ước đề xuất | Quy ước grain/công thức, left join, RFM, VIP M=5, inactivity 90 ngày, category revenue mix và market basket support 0,5% | Áp dụng thống nhất trong dbt Gold và Text-to-SQL; công khai giả định sales gross/net chưa rõ và kiểm tra sensitivity cho các ngưỡng. |
| 2026-10-12 | Phát hiện category/subcategory sản phẩm có dấu hiệu không khớp tên sản phẩm | Truy vấn `stg_products` trả về các ví dụ P000115, P000222, P002156, P002215; truy vấn mart xác nhận nhóm `Unknown` vẫn được giữ nhưng không được xếp hạng | Giữ nguyên taxonomy nguồn; không tự suy đoán mapping. Ghi chú hạn chế khi diễn giải kết quả theo category. |

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
