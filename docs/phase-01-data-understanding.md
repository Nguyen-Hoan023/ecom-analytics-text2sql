# Giai đoạn 1 — Hiểu nguồn dữ liệu và chốt data contract

**Trạng thái:** đã đo profile nguồn, join exceptions và các domain category/segment/market. Ngày chạy profile chưa được ghi; metric contract và một số giả định nghiệp vụ vẫn cần chốt trước khi đóng M1.

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

### Baseline đã đo từ lần profile đầu

Ngày chạy chưa được ghi lại trong kết quả gửi qua chat; cần bổ sung trước khi coi đây là snapshot có thể đối chiếu lâu dài.

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

Chi tiết orphan từ query 9a: product_code PPR000002 có 1 dòng (2021-09-01, sales 20, profit 10); product_code PPR000010 có 1 dòng (2020-04-04, sales 70, profit 35); region_code RRR0001 có 2 dòng (2020-04-04, sales 486, profit 243). Có 1 dòng vừa thiếu product vừa thiếu region, nên tổng ảnh hưởng duy nhất là 3 dòng, sales 506, profit 253. Không có cơ sở để suy đoán mã dimension thay thế.

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
| Discount trung bình | AVG(discount) trên các dòng hợp lệ, nhóm theo category | Lần profile thấy range 0–0,85 và avg 0,142883; diễn giải theo tỷ lệ 0–1, tức khoảng 0–85% và trung bình 14,29%. |
| Dòng hàng lỗ | Dòng có profit < 0 | Tách riêng với đơn hàng lỗ. |
| Đơn hàng lỗ | Tổng profit các dòng cùng order_id < 0 | Lần profile thấy 5.496 đơn lỗ; gom theo order trước, sau đó mới đếm theo segment. |
| Segment | ecom_sales.segment tại từng dòng giao dịch | Không coi đây là thuộc tính cố định của customer; lần profile không thấy order nào có nhiều segment. |
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
3. Mở file ../sql/phase_01_profile.sql và chạy nguyên trạng trước. File chỉ đọc dữ liệu (SELECT, cùng SET NOCOUNT ON), không tạo hoặc sửa object ở nguồn.
4. Ghi lại số dòng chính xác, số khóa trùng, null, khoảng ngày, khoảng discount, tỷ lệ join và phân bố các giá trị.
5. Không đưa credentials, tên/email khách hàng hoặc trích xuất dòng dữ liệu thô vào Git. Chỉ ghi kết quả tổng hợp cần thiết.
6. Đối chiếu checklist bên dưới, cập nhật quyết định và bằng chứng. Chỉ đánh dấu hoàn tất sau khi có kết quả thật.

Trang schema có thể đọc công khai, nhưng truy vấn SQL Server thật cần credentials do Xóm cấp. Credentials không được lưu trong repo và cũng không cần gửi vào cuộc chat này.

## 7. Checklist và decision log

Chỉ điền cột Quan sát sau khi chạy SQL profile. “Đang chờ” không có nghĩa là giá trị bằng 0.

| Kiểm tra | Tiêu chí / quyết định | Quan sát |
|---|---|---|
| Schema thực tế | Tên cột/nullability khớp; decimal(10,2), tọa độ decimal(10,6) | Đạt; cần bổ sung ngày profile |
| Số dòng | customer 17.415; sales 51.290; product 28.356; region 3.828; tổng 100.889 | Đạt; ngày profile chưa ghi |
| Khóa ứng viên | 4 khóa có non-null = distinct = row count; duplicate queries rỗng | Đạt theo output đã gửi |
| Grain ecom_sales | 51.290 dòng, 25.728 đơn, 12.793 đơn nhiều dòng, tối đa 14 dòng/đơn | Đạt cho grain; row_id được xác nhận duy nhất |
| Referential integrity | Biết null/orphan cho 3 quan hệ | Đã đo: customer 0/0; product 0/2; region 0/2 (null/orphan); orphan union 3 dòng, sales 506, profit 253 |
| Cột đo lường | Các cột fact profile không null; quantity/sales không âm hoặc bằng 0; profit âm có tồn tại | Đạt theo output đã gửi |
| Đơn vị discount | Range 0–0,85, avg 0,142883; 29.470/51.290 dòng có discount = 0 | Đạt; báo cáo theo phần trăm cần nhân 100 |
| Độ phủ ngày | 2020-01-01 đến 2023-12-31, có đủ 48 tháng | Đạt cho độ phủ tháng; đủ dữ liệu YoY |
| Miền category/segment/market | Category mỹ phẩm/chăm sóc cá nhân; segment Consumer/Corporate/Self-Employed; 5 market, 23 region, tổng 3.828 region_code | Đã đo; taxonomy market live khác các nhãn trong context tham khảo, không tự chuẩn hóa |
| Metric contract | Đã đo doanh thu/lợi nhuận và đơn lỗ; RFM/churn heuristic còn cần chốt ngưỡng | Một phần |
| Lệch so với reference | Customer attributes, categories/SKU, segment khác context; tổng theo segment khớp README | Đã ghi lệch; cần xác nhận tài liệu mô tả cũ hay khác phiên bản |

### Decision log

| Ngày | Câu hỏi / phát hiện | Bằng chứng | Quyết định / tác động |
|---|---|---|---|
| Chưa ghi ngày | Profile lần đầu: có 3 dòng fact duy nhất thiếu dimension match | Query 9a: product PPR000002/PPR000010; region RRR0001; 1 dòng trùng ở cả hai nhóm; sales ảnh hưởng 506, profit 253 | Không tự map mã; giữ fact và khóa nguồn, dùng left join/nhãn unmatched ở Silver/Gold để tránh mất số liệu. |
| Chưa ghi ngày | Domain market/region của nguồn live đã được gửi | 23 cặp market-region; Africa 321, Asia Pacific 931, Europe 1.281, LATAM 645, USCA 650; tổng 3.828; mỗi cặp không có trùng region_code | Giữ nhãn và cấp địa lý đúng như nguồn; chỉ tạo mapping sang context/reference nếu xác minh được quy tắc nghiệp vụ. |

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
