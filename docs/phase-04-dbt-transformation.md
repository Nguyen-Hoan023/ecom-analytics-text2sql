# Giai đoạn 4 — Transform dữ liệu với dbt

**Trạng thái:** Hoàn tất Silver, Intermediate và 12 Gold marts, ánh xạ tới bộ 15 câu hỏi nghiệp vụ. Full `dbt build` đã pass.

## Luồng dữ liệu

SQL Server → DLT → DuckDB Bronze → dbt Silver → Intermediate → Gold

## Các tầng model

- **Bronze:** Bốn bảng nguồn được DLT nạp vào DuckDB.
- **Silver:** stg_customers, stg_ecom_sales, stg_products, stg_regions.
- **Intermediate:** int_sales_enriched, ghép giao dịch với customer, product và region.
- **Gold:** Các marts phục vụ phân tích nghiệp vụ.

## Gold marts hiện có

| Model | Câu hỏi | Nội dung |
|---|---|---|
| mart_sales_by_segment | Q1, Q2 | Sales và profit theo segment; tổng toàn bộ có thể đối soát bằng cách cộng các segment. |
| mart_product_performance | Q3, Q12 | Sản phẩm bán chạy theo quantity và sản phẩm profit cao theo category. |
| mart_customer_profile_by_gender_occupation | Q4 | Số customer theo gender và occupation. |
| mart_discount_profitability | Q5 | Profitability theo discount band và category. |
| mart_profitability_by_market | Q6 | Sales, profit và margin theo market. |
| mart_loss_making_orders_by_segment | Q7 | Đơn lỗ theo segment. |
| mart_customer_rfm | Q8, Q14 | RFM, VIP và tín hiệu churn heuristic. |
| mart_category_sales_mix_by_segment | Q9 | Category sales mix theo segment; tỷ trọng được tính từ `total_sales`, không khẳng định hành vi mua kèm. |
| mart_top_countries_by_sales | Q10 | Xếp hạng country theo sales. |
| mart_monthly_sales | Q11 | Kết quả theo tháng và YoY. |
| mart_customer_region_behavior | Q13 | Hành vi customer theo số region đã mua. |
| mart_market_basket_associations | Q15 | Các cặp product_code xuất hiện chung trong đơn và association theo ngưỡng support. |

## Kết quả kiểm tra đã xác nhận

- Source tests: 8/8 pass.
- stg_customers: 2/2 tests pass.
- stg_ecom_sales: 2/2 tests pass.
- int_sales_enriched: 3/3 tests pass.
- mart_sales_by_segment: 7/7 tests pass.
- Các mart ban đầu đã được chạy riêng và kết quả được xem lại bằng dbt show.
- Cấu hình mẫu `models.ecom_analytics.example` đã được gỡ khỏi `dbt_project.yml`; `dbt parse` chạy sạch.
- Full `dbt build` chạy thành công; toàn bộ model và test trong DAG đã pass.

## Kết quả Q15 — Market basket

- Có 25.728 đơn hợp lệ; 12.778 đơn chứa từ hai product_code khác nhau trở lên.
- Cặp product_code xuất hiện nhiều nhất chỉ có trong 3 đơn.
- Không có cặp nào đạt support 0,5% (tối thiểu 129 đơn), 0,1% (26 đơn) hoặc 0,05% (13 đơn).
- Ở mức 0,01% có 12 cặp, mỗi cặp chỉ xuất hiện trong 3 đơn.
- Giữ ngưỡng 0,5% cho mart chính. Với snapshot hiện tại, không có association product-level đủ tần suất ở ngưỡng này.
- Các cặp ở mức 0,01% chỉ nên xem là kết quả thăm dò; 3 đơn chưa đủ bằng chứng để đưa ra đề xuất kinh doanh.

## Lưu ý về dữ liệu và metric

- ecom_sales có 51.290 dòng; grain là một dòng trên mỗi row_id.
- Có 3 dòng giao dịch duy nhất thiếu product/region match; giữ chúng để đối soát, không tự đoán mã dimension thay thế.
- Category/subcategory nguồn có một số dấu hiệu không nhất quán. Giữ nguyên taxonomy nguồn và thận trọng khi diễn giải kết quả theo category.
- Ý nghĩa gross/net của sales chưa được nguồn xác nhận.
- Churn là heuristic theo snapshot lịch sử, không phải nhãn churn thực tế.

## Cách chạy dbt

Chạy từ thư mục ecom_analytics sau khi activate môi trường ảo:

    uv run --active dbt parse
    uv run --active dbt run --select mart_sales_by_segment
    uv run --active dbt test --select mart_sales_by_segment
    uv run --active dbt show --select mart_sales_by_segment

