# Warehouse reconciliation report

**Result:** Owner-shared output confirmed 15/15 warehouse baseline cases passed for the recorded snapshot. The cases and expected assertions are maintained in the golden set v1 and can be rerun with the baseline runner.
**Ngày tổng hợp checkpoint:** 2026-10-18.
**Mốc source profile:** 2026-10-10 14:25 UTC.
**Evidence:** Query outputs and dbt previews were shared during implementation. The original ad-hoc SQL Server reconciliation queries were not retained. This report is snapshot-specific; rerun the maintained baseline suite after source or model changes.

## Phạm vi và quy tắc đánh giá

- So sánh kết quả Gold marts với query baseline/source outputs đã chia sẻ, theo cùng grain và metric contract v1.
- `Đạt` nghĩa là các giá trị được đối chiếu khớp theo output đã gửi; không có nghĩa là giả định nghiệp vụ chưa xác nhận đã trở thành sự thật.
- Query output và `dbt show` chỉ là bằng chứng tại snapshot đang dùng. Muốn kiểm tra lại tự động, cần lưu lại SQL baseline và kết quả chuẩn trong bộ evaluation/test.
- Nguồn chưa xác nhận đơn vị tiền tệ hoặc `sales` là gross/net. Tài liệu vì vậy dùng `total_sales` và ghi nguyên đơn vị nguồn.

## Kết quả Q1–Q15

| Q | Kết quả đối soát | Trạng thái và cách hiểu |
|---:|---|---|
| 1 | 51.290 dòng bán hàng; 25.728 đơn; `total_sales` 6.517.674; `total_profit` 1.065.413,58; profit margin khoảng 16,35%. Kiểm tra đơn thuộc nhiều segment trả 0. | **Đạt.** Tổng bốn năm, không phải doanh thu một năm. |
| 2 | Mart theo segment: Consumer 26.518 dòng / 13.291 đơn / sales 2.146.780 / profit 365.377,50; Corporate 15.429 / 7.724 / 3.840.707 / 608.523,36; Self-Employed 9.343 / 4.713 / 530.187 / 91.512,72. Tổng khớp Q1. | **Đạt.** Corporate dẫn đầu về sales và profit tuyệt đối; Self-Employed có margin cao nhất (~17,26%), nhưng sales thấp nhất. Không suy ra nên phân bổ ngân sách thế nào chỉ từ margin. |
| 3 | Top 10 theo units sold giữa source và mart khớp thứ hạng, units và sales: P000116 (1.780; 67.640), P000619 (1.195; 15.535), P000512 (518; 16.058), P000114 (476; 2.380), P001501 (462; 5.082), P000473 (460; 4.140), P000976 (455; 3.185), P000375 (438; 3.504), P000779 (425; 5.100), P000126 (408; 2.040). | **Đạt.** “Bán chạy” được định nghĩa theo units, sales là số đo phụ. Giữ nguyên taxonomy product nguồn dù một số tên và category không khớp nhau. |
| 4 | Cả 15 nhóm gender × occupation khớp giữa source và mart; tổng customer là 17.415. Các nhóm `Unknown` được giữ lại. | **Đạt.** Không loại customer thiếu phân loại khỏi population. |
| 5 | Sáu category, gồm `Unknown`, được đối chiếu theo sales-line count, discount-line count, average discount, sales và profit; mọi mismatch count đều bằng 0. Tổng 51.290 dòng. | **Đạt.** Average discount là trung bình theo dòng hàng, giữ discount bằng 0. Taxonomy category nguồn có vấn đề đã ghi nhận nên diễn giải category cần thận trọng. |
| 6 | Có 6 nhóm market trong kết quả; các kiểm tra source–mart về số dòng, sales, profit và margin đều có mismatch bằng 0. | **Đạt.** Nhóm `Unknown` được giữ cho region orphan; không tự gán market thay thế. |
| 7 | Đơn lỗ theo segment khớp source–mart: Consumer 2.864/13.291; Corporate 1.667/7.724; Self-Employed 965/4.713. | **Đạt.** Đơn lỗ được xác định bằng tổng profit của các dòng trong đơn `< 0`, không phải chỉ cần một dòng lỗ. |
| 8 | Snapshot 2024-01-01: 17.415 customer được chấm; 3.483 VIP. Risk/VIP-at-risk: 15.339/2.901 ở 60 ngày; 14.660/2.732 ở 90 ngày; 12.584/2.255 ở 180 ngày. Source–mart không lệch population, recency hoặc monetary score. | **Đạt.** Đây là churn-risk heuristic trên snapshot lịch sử, không phải churn label hay trạng thái hiện tại. |
| 9 | 17 cặp segment × category; line count, order count, sales, profit, tỷ trọng và tổng segment đều khớp. Tổng sales/profit: 6.517.674 / 1.065.413,58. | **Đạt theo phạm vi v1.** Đây là category sales mix theo segment, không chứng minh các sản phẩm được mua kèm hoặc hiệu quả cross-sell. |
| 10 | Top 15 country khớp về key, rank, line count, order count, sales, profit và margin; tất cả mismatch bằng 0. Có 1 nhóm country `Unknown` với 2 sales lines, 1 order, sales 486 và profit 243. | **Đạt.** Thứ hạng theo sales; giữ `Unknown`, không xếp vào danh sách country đã nhận diện. |
| 11 | Đủ 48 tháng từ 2020-01 đến 2023-12, không thiếu tháng. Line count, order count, sales, profit, margin, prior-year sales và YoY growth đều không mismatch; tổng sales/profit khớp Q1. | **Đạt.** YoY chỉ có thể được tính khi có tháng cùng kỳ năm trước. |
| 12 | Top 3 theo profit trong mỗi category có 15 dòng; product key, rank, line count, order count, units, sales và profit đều không mismatch. Có 2 sản phẩm orphan `Unknown`; số sản phẩm `Unknown` được xếp hạng là 0. | **Đạt theo quyết định v1.** Giữ sản phẩm orphan trong mart để đối soát nhưng loại `Unknown` khỏi business ranking theo category vì nó không phải category nghiệp vụ. |
| 13 | Population 17.415 customer; 5.087 khách có nhiều region khớp dimension; 1 khách có giao dịch region orphan. Hai dòng orphan có sales 486 và profit 243. Các kiểm tra line count, matched-region, orphan, sales và profit đều mismatch bằng 0. | **Đạt.** Có tối đa 9 region khớp trên một customer. Orphan được đánh dấu riêng, không coi là region hợp lệ đã nhận diện. |
| 14 | 17.415 customer; snapshot 2024-01-01. Các kiểm tra last order date, recency days/score, frequency orders/score, monetary sales/score và RFM status đều mismatch bằng 0. | **Đạt theo công thức v1.** Kết quả là R/F/M quintile scores; `rfm_status` chỉ phân biệt `scored`/`no_purchase_history`, chưa gán nhãn lifecycle marketing như “Champions”. |
| 15 | 25.728 đơn hợp lệ; 12.778 đơn có từ hai product_code khác nhau trở lên; pair lớn nhất xuất hiện trong 3 đơn. Có 51.188 cặp order–product sau dedupe, thấp hơn 51.290 dòng fact 102 dòng. Ngưỡng support tối thiểu: 129 đơn ở 0,5%, 26 ở 0,1%, 13 ở 0,05%; số cặp đạt lần lượt 0, 0, 0. Ở 0,01% có 12 cặp (3 đơn/cặp). Mart chính ở 0,5% trả 0 association, đúng theo dữ liệu. | **Đạt.** Dedupe `(order_id, product_code)` là quy tắc basket, không phải xóa dòng fact. 12 cặp ở 0,01% chỉ là thăm dò, chưa đủ bằng chứng đề xuất cross-sell SKU. |

## Các quyết định được chốt tại checkpoint

1. Giữ `sales` và `profit` ở grain dòng hàng; không tự nhân `sales` với quantity.
2. Giữ fact orphan bằng left join và nhãn `Unknown`/unmatched để không mất sales hoặc profit.
3. Q9 được triển khai là category sales mix theo segment; nếu muốn trả lời co-purchase thật, cần phân tích basket riêng.
4. Q12 giữ product orphan để đối soát nhưng không xếp hạng `Unknown` trong top 3 theo category.
5. Q14 hiện là RFM quintile scoring theo customer; nhãn lifecycle marketing là phạm vi phát triển sau.
6. Q15 giữ minimum support 0,5% làm ngưỡng mart chính. Chưa dùng các cặp 0,01% làm đề xuất nghiệp vụ.

## Rủi ro chất lượng và phạm vi sử dụng

| Rủi ro | Bằng chứng | Mức độ và tác động |
|---|---|---|
| Orphan product/region keys | 3 dòng fact duy nhất trên 51.290 (~0,006%), sales 506 và profit 253; có 1 dòng nằm ở cả hai orphan groups. | **Thấp trong snapshot** vì ảnh hưởng tổng thể nhỏ; **cao hơn nếu dùng inner join**, vì khi đó mất các dòng này khỏi tổng. Left join và Unknown giữ nguyên số liệu. |
| Taxonomy product/category không nhất quán | Một số product name không khớp category/subcategory trong dimension. | **Trung bình** cho quyết định theo category; các phép tổng hợp khớp về số học nhưng có thể mang nhãn nghiệp vụ sai. Không tự sửa taxonomy. |
| Snapshot cũ cho churn/current state | Giao dịch kết thúc 2023-12-31; RFM snapshot là 2024-01-01. | **Cao nếu dùng để nhắm mục tiêu hiện tại**; phù hợp để tái tạo phân tích lịch sử. Cần dữ liệu mới và snapshot mới trước khi vận hành. |
| Định nghĩa số tiền chưa xác nhận | Chưa có xác nhận về currency hoặc sales gross/net. | **Trung bình** cho báo cáo tài chính hoặc so sánh liên nguồn; vẫn có thể so sánh nội bộ trong cùng snapshot nếu ghi là `total_sales` theo đơn vị nguồn. |
| SQL đối soát nguồn chưa được lưu | Output được chia sẻ nhưng không tìm thấy query ad-hoc gốc chạy trực tiếp trên SQL Server. Baseline SQL trên Gold marts đã được đóng gói, chưa chạy xác nhận toàn bộ. | **Trung bình** về khả năng tái lập source-to-mart; chạy và đối chiếu golden set trước khi dùng làm gate tự động. |

## Giới hạn còn mở

- Xác nhận với chủ dữ liệu đơn vị tiền tệ và `sales` là gross hay net.
- Xác minh hoặc nhận mapping taxonomy product/category đáng tin cậy; không tự sửa taxonomy trong pipeline.
- Nếu cần cross-sell thật, mở rộng Q9/Q15 bằng phân tích đồng mua theo order và thử ngưỡng trên thêm dữ liệu.
- Nếu dùng churn cho vận hành, cần nhãn kết quả mua lại/churn ở các snapshot tương lai và kiểm định khả năng dự báo.
- Đây là snapshot tĩnh; chưa chứng minh freshness hoặc khả năng đối soát tự động mỗi lần pipeline chạy.

## Revalidation

Rerun the baseline suite after changing the source snapshot, metric definitions, or Gold model logic. Review mismatches before changing expected values; do not update a golden contract merely to make a failing result pass. For Text-to-SQL suite commands, see the evaluation README.
