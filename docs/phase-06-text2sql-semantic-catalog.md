# Phase 6 — Semantic catalog và access policy v1

**Trạng thái:** Phase 6 đã đóng core acceptance. Q01–Q15 warehouse baselines đạt 15/15; canonical tiếng Việt đạt 15/15 theo [checkpoint Phase 6](phase-06-progress-checkpoint.md). Deterministic guardrails đạt 14/14 offline; paraphrase Q02 và basket safety case đã được nghiệm thu theo checkpoint. CLI, browser UI local và chart theo kết quả query đã được triển khai. File [`vi-canonical.json`](../reports/text2sql-evaluation/vi-canonical.json) là run lịch sử 1/15 ngày 2026-10-21, không phải kết quả mới nhất; xem [index reports](../reports/README.md) để biết phạm vi và thời điểm các artifact. Tài liệu này mô tả catalog/policy và giới hạn truy cập, không phải bảng tiến độ hiện hành.

## Mục tiêu

Định nghĩa dữ liệu nào Text-to-SQL được phép nhìn thấy, mỗi Gold mart có grain và ý nghĩa gì, metric cần tính ra sao, và trường hợp nào cần hỏi lại hoặc từ chối. Catalog không thay đổi pipeline SQL Server → DLT → DuckDB → dbt Gold.

## Các file đặc tả

- [`text2sql/semantic_catalog.yml`](../text2sql/semantic_catalog.yml): metadata nghiệp vụ cho 12 Gold marts, tất cả cột đầu ra, grain, metric, từ đồng nghĩa, caveat và phân loại dữ liệu.
- [`text2sql/access_policy.yml`](../text2sql/access_policy.yml): role mặc định, relation allowlist, mart hạn chế, truy vấn aggregate được phê duyệt, schema đầu ra theo thứ tự cho từng template, SQL policy và cấu hình phòng thủ dự kiến cho DuckDB.
- [Metric contract v1](phase-01-data-understanding.md#5-metric-contract-v1-và-giả-định-nghiệp-vụ): nguồn định nghĩa metric chính thức.
- [Checkpoint Q1–Q15](checkpoint-q1-q15-reconciliation.md): kết quả đối soát và giới hạn dùng làm baseline cho evaluation.

## Quy tắc dữ liệu đã đưa vào catalog

1. Chỉ query các Gold mart trong `analytics_gold`; Bronze, Silver, Intermediate và bảng nguồn không nằm trong quyền truy cập Text-to-SQL v1.
2. `total_sales` có thể được tìm bằng từ “revenue/doanh thu”, nhưng câu trả lời phải dùng tên `total_sales` vì nguồn chưa xác nhận gross/net hoặc currency.
3. `order_count` là distinct order trong grain của từng mart và không được cộng tùy tiện qua category, product, country hoặc market. Riêng snapshot này, tổng `order_count` theo tháng và theo segment đều đã đối soát với 25.728 distinct source orders.
4. `profit_margin` phải tính từ tổng profit chia tổng sales; không được average margin của nhóm.
5. `average_discount` là trung bình theo dòng, gồm cả discount bằng 0. Khi roll up mart discount qua các band, dùng trọng số `sales_line_count`.
6. “Best-selling” mặc định là `units_sold`; nếu người hỏi dùng “most profitable” mà không nói total profit hay margin, hệ thống phải hỏi lại.
7. Category sales mix Q9 không được gọi là phân tích sản phẩm mua kèm. Market basket Q15 hiện không có cặp đạt ngưỡng mặc định 0,5%.
8. Snapshot RFM là 2024-01-01. `churn_risk_90d` là inactivity heuristic, không phải nhãn churn hoặc trạng thái hiện tại.
9. Product taxonomy nguồn có inconsistency; giữ nguyên giá trị, không tự suy đoán category dựa trên tên sản phẩm.
10. Nhóm `Unknown` được giữ để đối soát; không diễn giải nó như segment, country, market hoặc category đã được nhận diện.

## Phân quyền cho 12 mart

Mười mart tổng hợp hoặc tổng hợp theo sản phẩm được cho phép truy vấn trực tiếp. Hai mart `mart_customer_rfm` và `mart_customer_region_behavior` có grain từng customer nên không mở cho truy vấn SQL tự do. Q8, Q13 và Q14 được mô tả thành các aggregate template; không trả `customer_id` hay số liệu riêng của từng customer.

Mọi truy cập bị giới hạn ở tầng ứng dụng. DuckDB embedded không cung cấp ranh giới quyền cho người dùng không tin cậy bên trong engine. Loader kiểm tra cấu trúc YAML và tính nhất quán giữa catalog/policy. Validator dùng SQLGlot AST, chỉ nhận một câu `SELECT`, một Gold mart allowlist, cột/hàm đã biết và không có join/CTE/subquery; Q8/Q13/Q14 chỉ chạy khi khớp chính xác SQL template. Riêng mart demographic bắt buộc có điều kiện `customer_count >= 10` và chỉ được chọn các cột gốc, để các nhóm nhỏ không lọt qua câu SQL. Các kiểm soát `read_only`, file/network/extension và giới hạn tài nguyên vẫn phải được cấu hình ở executor trước khi chạy SQL.

## Bản đồ câu hỏi → mart

| Câu hỏi | Mart / cách truy cập | Giới hạn cần giữ |
|---:|---|---|
| Q1 | `mart_sales_by_segment` hoặc `mart_monthly_sales`, tổng hợp về một dòng | Trả `sales_line_count`, `order_count`, `total_sales`, `total_profit`, `profit_margin`; order-count rollup đã đối soát ở cả hai mart. Đây là tổng toàn kỳ 2020–2023, không gọi là doanh thu năm. |
| Q2 | `mart_sales_by_segment` | Segment lấy từ fact. |
| Q3 | `mart_product_performance` | Xếp theo units; taxonomy có caveat. |
| Q4 | `mart_customer_profile_by_gender_occupation` | Ẩn nhóm có dưới 10 customer khi serving. |
| Q5 | `mart_discount_profitability` | Tính average discount tổng theo trọng số dòng. |
| Q6 | `mart_profitability_by_market` | Unknown riêng; margin tính từ tổng. |
| Q7 | `mart_loss_making_orders_by_segment` | Đơn lỗ khi tổng profit của đơn < 0. |
| Q8 | Aggregate template `q08_vip_risk_summary` trên `mart_customer_rfm` | Không xuất customer-level rows/IDs; risk là heuristic lịch sử. |
| Q9 | `mart_category_sales_mix_by_segment` | Category mix, không phải co-purchase. |
| Q10 | `mart_top_countries_by_sales` | Chỉ top 15 country và Unknown, không phải full population. |
| Q11 | `mart_monthly_sales` | 48 tháng; YoY cần prior-year sales. |
| Q12 | `mart_product_performance` | Top 3 theo profit/category; Unknown không được rank như category nghiệp vụ. |
| Q13 | Aggregate template `q13_region_behavior_summary` trên `mart_customer_region_behavior` | Không xuất customer-level rows/IDs. |
| Q14 | Aggregate template `q14_rfm_population_summary` trên `mart_customer_rfm` | Quintile scores, chưa phải lifecycle labels. |
| Q15 | `mart_market_basket_associations` | Kết quả mart rỗng ở support 0,5%; không thổi phồng các cặp xuất hiện 3 đơn. |

## Loader và SQL validator

- [`text2sql/catalog.py`](../text2sql/catalog.py) nạp YAML bằng `yaml.safe_load`, kiểm tra schema phiên bản, marts, cột, allowlist, role và template references. Mỗi template khai báo `output_columns`; loader parse SQL policy và fail-closed nếu tên/thứ tự cột khai báo không khớp projection thực tế.
- [`text2sql/validator.py`](../text2sql/validator.py) parse SQL bằng SQLGlot ở dialect DuckDB, fail-closed khi gặp cú pháp hoặc node AST ngoài tập cho phép, rồi trả về `ValidatedQuery` để executor có thể dùng.
- [`text2sql/executor.py`](../text2sql/executor.py) chỉ nhận đúng kiểu `ValidatedQuery`, xác thực lại SQL/metadata theo policy hiện hành, mở đúng warehouse bằng connection read-only, tắt external access và extension autoload/autoinstall/community extensions, khóa cấu hình DuckDB sau setup, và áp thread/memory/temp/runtime limits. Nếu SQL không có `LIMIT`, executor trả tối đa `default_result_rows`; mọi trường hợp đều bị chặn ở hard cap. Kết quả có `columns`, `rows`, `row_count`, `row_limit`, `truncated` và `duration_ms`.
- [`text2sql/service.py`](../text2sql/service.py) cung cấp `QueryService.list_approved_templates()` và `QueryService.execute_template(template_id)`. Service chỉ lấy SQL từ policy, kiểm tra template có được role tin cậy cho phép, gọi validator rồi executor; không nhận SQL tùy ý và không trả phần SQL template cho client.
- [`text2sql/evaluation/golden_set_v1.yml`](../text2sql/evaluation/golden_set_v1.yml) đóng gói 15 câu hỏi chuẩn với câu gốc, câu phục vụ theo phạm vi v1, paraphrase, mart/template, baseline SQL hoặc template id, cột/kết quả kỳ vọng và caveat. Bộ này cũng có ca hỏi lại/từ chối riêng. Baseline Q1–Q15 đã pass trên warehouse.
- [`text2sql/evaluation/run_baselines.py`](../text2sql/evaluation/run_baselines.py) trước mỗi lần đánh giá kiểm tra sẵn q01–q15, câu hỏi/paraphrase, metric contract, relation, template và expected columns có nhất quán với catalog/policy/baseline hay không. Sau đó runner chạy 15 baseline qua validator và DuckDB executor, rồi đối chiếu schema, row count, các giá trị tham chiếu và giới hạn dòng. Đây là kiểm tra SQL/template và kết quả kho dữ liệu; chưa thay thế đánh giá hiểu ngôn ngữ tự nhiên.
- [`text2sql/gemini.py`](../text2sql/gemini.py) là adapter Gemini dùng structured JSON output. Key chỉ được đọc từ môi trường hoặc `.env` cục bộ và không xuất ra log.
- [`text2sql/nl_service.py`](../text2sql/nl_service.py) định tuyến câu hỏi sang một trong bốn quyết định: SQL, template đã duyệt, hỏi lại, hoặc từ chối. SQL tự sinh phải qua validator rồi mới đến executor; template chỉ nhận đúng ID mà role được phép.
- [`text2sql/cli.py`](../text2sql/cli.py) cho phép xem prompt cục bộ hoặc gửi câu hỏi qua pipeline khi người dùng đã cấu hình Gemini.
- [`text2sql/evaluation/run_nl_evaluation.py`](../text2sql/evaluation/run_nl_evaluation.py) chạy câu chuẩn, paraphrase và 8 guardrail cases qua service thật; so sánh schema, kết quả, template ID, caveat và giới hạn dòng với golden set. Báo cáo tùy chọn chỉ lưu case ID, trạng thái và pass/fail; không lưu prompt, SQL, API key hay query rows.
- NL evaluator mặc định nghỉ 15 giây giữa request, dừng gửi các case còn lại khi Gemini trả `unavailable`, và ghi số case chưa gửi. Mã HTTP/API status được hiển thị an toàn, không kèm raw response body. Khoảng nghỉ giúp giảm tốc độ gửi request, nhưng không bảo đảm hết quota hay ngăn lỗi dịch vụ. Kiểm tra giới hạn đang áp dụng trong Google AI Studio trước khi chạy live.
- [`tests/test_text2sql_guardrails.py`](../tests/test_text2sql_guardrails.py) kiểm tra loader, allowlist, cột/hàm, SQL structure, giới hạn nhóm demographic và các template customer-level.
- Ví dụ sử dụng:

```python
from text2sql.catalog import load_config
from text2sql.validator import validate_sql

config = load_config()
query = validate_sql(
    "SELECT segment, total_sales FROM analytics_gold.mart_sales_by_segment",
    config,
)
print(query.sql)
```

- Truy vấn bị từ chối bằng `SQLValidationError`; lỗi cấu hình bị từ chối bằng `CatalogConfigError`. Executor phát sinh `InvalidValidatedQueryError` cho object giả/sai policy, `QueryTimeoutError` khi quá thời gian, và `QueryExecutionError` cho lỗi thực thi. Lỗi DuckDB không kèm nguyên văn SQL trong thông báo lỗi.
- Customer-level marts không chấp nhận SQL tùy ý. Caller phải truyền đúng `template_id` cùng SQL tương ứng; validator so canonical SQL sau parse với template policy.
- Ví dụ thực thi sau khi đã validate:

```python
from text2sql import DuckDBExecutor, load_config, validate_sql

config = load_config()
validated = validate_sql(
    "SELECT segment, total_sales FROM analytics_gold.mart_sales_by_segment",
    config,
)
result = DuckDBExecutor(config=config).execute(validated)
print(result.columns)
print(result.rows)
```

- Ví dụ chạy một template bị hạn chế bằng service:

```python
from text2sql import QueryService

service = QueryService()
print(service.list_approved_templates())
result = service.execute_template("q08_vip_risk_summary")
print(result.columns)
print(result.rows)
```

- `role` của `QueryService` mặc định lấy từ policy. Nếu truyền `role` vào, caller phải lấy nó từ cấu hình ứng dụng hoặc danh tính đã xác thực, không lấy từ prompt/câu hỏi của người dùng.

- Executor trả dữ liệu bảng cho lớp ứng dụng; nó chưa tạo chart. Câu query không có `LIMIT` mặc định chỉ trả tối đa 50 dòng; giới hạn tuyệt đối của policy là 500 dòng.
- Chạy bộ kiểm tra trên Windows từ thư mục repo:

```powershell
uv run --active python -m unittest discover -s tests -p "test_*.py" -v
```

## Gemini và đường đi của dữ liệu

`NaturalLanguageQueryService` gửi đến Gemini duy nhất câu hỏi người dùng và metadata đã lọc từ semantic catalog: Gold marts được role cho phép, tên/kiểu/ý nghĩa cột, grain, metric contract, caveat và mô tả aggregate template được duyệt. Với template, prompt có cả danh sách cột kết quả theo thứ tự; SQL nội bộ của template vẫn không được đưa cho model. Không gửi DuckDB path, credentials, kết quả query, raw rows hoặc metadata cột bị hạn chế. Các yêu cầu nhận diện khách hàng bị từ chối trước khi gọi model.

Phản hồi model không được thực thi trực tiếp. `sql` phải qua SQLGlot validator và allowlist hiện tại; `template` phải trùng ID được policy cấp cho role; `clarify` và `refuse` dừng trước executor. Executor vẫn mở DuckDB read-only, áp hard row cap và giới hạn tài nguyên. Lỗi model, JSON sai định dạng hoặc SQL không hợp lệ đều dừng an toàn.

SDK hiện tại là `google-genai`; adapter dùng structured output JSON thay vì parse SQL từ văn bản tự do. Model mặc định cấu hình trong `.env.example` là `gemini-3.8-flash`, có thể đổi bằng `GEMINI_MODEL`. Google ghi nhận `gemini-2.5-flash` còn tồn tại nhưng quyền dùng cho project mới bị giới hạn; nếu tài khoản có quyền, có thể đặt model đó trong `.env`.

Tài liệu tham khảo chính thức: [Gemini API quickstart](https://ai.google.dev/gemini-api/docs/get-started), [structured outputs](https://ai.google.dev/gemini-api/docs/structured-output), [model deprecations](https://ai.google.dev/gemini-api/docs/deprecations/), và [Python SDK releases](https://github.com/googleapis/python-genai/releases).

Xem prompt đã lọc mà không gọi Gemini hoặc cần API key:

```powershell
uv run --active python -m text2sql.cli --show-prompt "Top 10 sản phẩm bán nhiều nhất"
```

Khi gọi Gemini, key chỉ được lưu trong `.env` cục bộ (không commit). CLI hiện hiển thị kết quả dạng bảng; có thể chọn JSON hoặc xuất CSV:

```powershell
uv run --active python -m text2sql.cli "Top 10 sản phẩm bán nhiều nhất"
uv run --active python -m text2sql.cli --output-format json "Top 10 sản phẩm bán nhiều nhất"
uv run --active python -m text2sql.cli --export-csv reports\text2sql-evaluation\top-products.csv "Top 10 sản phẩm bán nhiều nhất"
```

CSV chỉ ghi vào file mới; lệnh sẽ từ chối ghi đè file đã tồn tại. Ô văn bản bắt đầu bằng ký tự có thể kích hoạt công thức bảng tính được escape bằng dấu nháy đơn. CLI trả kết quả bảng/JSON/CSV; browser UI local có thể hiển thị KPI và chart từ kết quả query. Chưa bật service cho người dùng từ xa vì project đang dùng role local single-user.

Chạy riêng một câu tiếng Việt; kiểm tra quota trong AI Studio trước mỗi request:

```powershell
uv run --active python -m text2sql.evaluation.run_nl_evaluation --case-id q01 --language vi --variant canonical
```

Chạy toàn bộ câu chuẩn và paraphrase tiếng Việt cùng guardrails:

```powershell
uv run --active python -m text2sql.evaluation.run_nl_evaluation --language vi --variant all --guardrails --output reports/text2sql-evaluation/vi.json
```

Đánh giá câu chuẩn tiếng Anh riêng:

```powershell
uv run --active python -m text2sql.evaluation.run_nl_evaluation --language en --variant canonical --guardrails
```

Các lệnh live này cần `GEMINI_API_KEY` trong `.env` cục bộ và warehouse đã build. Để xem context mà không gọi API, dùng `python -m text2sql.cli --show-prompt "Top 10 sản phẩm bán nhiều nhất"`. Trạng thái Q01–Q15 live và các case còn lại được theo dõi trong [checkpoint Phase 6](phase-06-progress-checkpoint.md).

Chạy đối chiếu baseline từ thư mục gốc sau khi đã nạp dữ liệu và build Gold marts:

```powershell
uv run --active python -m text2sql.evaluation.run_baselines
```

Lệnh này không gọi Gemini và không cần API key. Q1–Q15 đã pass; đó là baseline cho kết quả kho dữ liệu, không phải bằng chứng rằng Gemini hiểu đúng mọi câu hỏi/paraphrase.

**Ghi chú phạm vi ban đầu (lịch sử):** Phase 6 được bắt đầu với CLI local, không xây web API từ xa. Airflow/Cosmos được triển khai ở Phase 7 và Text-to-SQL vẫn là serving path độc lập, không chạy bên trong DAG.
