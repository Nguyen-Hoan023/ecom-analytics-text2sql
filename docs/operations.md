# Vận hành và khắc phục sự cố

Runbook này mô tả cách vận hành pipeline batch hiện tại. Project dùng một DuckDB file được chia sẻ giữa host và Docker; không có database server đứng giữa để điều phối reader/writer. [ADR 0002](decisions/0002-duckdb-access.md) ghi quyết định về cách truy cập file này.

## Các bất biến vận hành

1. DAG `xom_ecom_warehouse_refresh` chạy thủ công (`schedule=None`), giới hạn một run và một task cùng lúc, `retries=0`.
2. DLT thay snapshot Bronze với `write_disposition="replace"`; dbt dựng lại Silver/Intermediate/Gold, sau đó quality gate chạy 15 baseline cases. DAG không gọi Gemini.
3. Host `.env` và `orchestration/.env` là hai cấu hình riêng. Container cần DuckDB path Linux `/usr/local/airflow/duckdb_warehouse/warehouse.duckdb`; path Windows không dùng được bên trong container.
4. Với DuckDB 1.5.x đang pin, nhiều process chỉ đọc có thể cùng đọc file, nhưng không được có writer đồng thời. Khi refresh, tắt UI/charts/baselines và query host; chỉ phục vụ lại sau khi DAG xong. [Quy tắc concurrency của DuckDB 1.5](https://duckdb.org/docs/1.5/connect/concurrency).
5. Không xóa warehouse, file WAL/lock hoặc generated runtime để chữa lỗi khóa. Dừng tiến trình sở hữu file trước và xác nhận không còn task đang chạy.
6. Giữ DAG manual-only. Không bật schedule/retries để tự động thử lại lỗi chưa rõ nguyên nhân.

## Refresh warehouse qua Airflow

### Trước khi trigger

- Xác nhận Docker Desktop Linux Engine đang chạy và Airflow healthy (`astro dev ps`).
- Xác nhận `orchestration/.env` có SQL Server variables và đúng DuckDB container path; không `echo`, `Get-Content` hoặc chụp file này.
- Đóng Text-to-SQL UI, lệnh dbt host, chart generation và các client khác có thể đang dùng DuckDB.
- Xác nhận không có DAG run khác ở trạng thái `running` hoặc `queued`.
- Nếu source/dbt vừa thay đổi: dừng stack, từ repo root chạy `uv run --active python scripts/project.py astro prepare`, rồi vào `orchestration/` chạy `astro dev parse` trước khi start lại. Không thay stage khi container còn mount nó.

### Chạy và chấp nhận

1. Mở `http://localhost:8080`, chọn `xom_ecom_warehouse_refresh` rồi bấm **Trigger DAG**. Không bật lịch định kỳ.
2. Theo dõi graph/grid theo thứ tự `preflight_check` → `dlt_ingestion` → `dbt_transform` → `quality_gate`.
3. Chỉ chấp nhận khi DAG `success`, DLT source/target reconciliation thành công, dbt model/test pass và quality gate báo 15/15.
4. Ghi `dag_run_id`, thời điểm chạy, task states và số liệu tổng hợp đã đối chiếu. Không lưu credentials hoặc raw customer rows vào báo cáo/log chia sẻ.
5. Sau khi run kết thúc thành công, mới chạy chart hoặc mở UI/CLI để đọc warehouse đã refresh.

Mốc của snapshot đã nghiệm thu:

| Metric | Giá trị tham chiếu |
|---|---:|
| Customer source rows | 17.415 |
| Sales source rows | 51.290 |
| Product source rows | 28.356 |
| Region source rows | 3.828 |
| Total sales | 6.517.674,00 |
| Total profit | 1.065.413,58 |
| Baseline cases | 15/15 |

Đây là mốc của snapshot đã kiểm tra, không phải cam kết cho mọi lần refresh. Nếu nguồn thay đổi, điều tra và đối chiếu metric contract/Q1–Q15 trước khi cập nhật golden expectations.

## Vận hành local sau refresh

Đảm bảo không còn task nào đang ghi warehouse. Từ repo root:

```powershell
uv run --active python scripts/project.py baselines
uv run --active python scripts/project.py charts
uv run --active python scripts/project.py ui
```

UI chạy tại `http://127.0.0.1:8765`; dừng bằng `Ctrl+C`. Trước lần refresh tiếp theo, dừng UI/chart/dbt clients. Các reader không được chồng lên cửa sổ DLT/dbt write.

## Xử lý lỗi theo trạng thái DAG

| Quan sát | Điều tra | Phục hồi |
|---|---|---|
| `queued` kéo dài | `astro dev ps`, log scheduler, Docker/worker và run khác | Khôi phục scheduler/worker; không trigger liên tục tạo nhiều run |
| `preflight_check` failed; downstream `upstream_failed` | Mở log preflight; xác định DNS/TCP, login, database name hoặc permission | Sửa config/network; kiểm tra read-only connection từ scheduler container; tạo DAG run mới. `upstream_failed` là hệ quả mong đợi |
| `dlt_ingestion` failed | Đọc log task; kiểm tra source access, quyền ghi/dung lượng và process khác đang giữ file | Không bật retry tự động. Xác định trạng thái Bronze; sau khi sửa nguyên nhân, chạy lại toàn pipeline bằng run mới |
| Cosmos/dbt model hoặc test failed | Tìm task dbt đầu tiên fail; kiểm tra log, profile/path và source stage | Không phục vụ mart có thể đang refresh dở. Nếu code đổi, stop stack → chạy `scripts/project.py astro prepare` từ repo root → parse/start lại từ `orchestration/`; sau đó chạy lại toàn pipeline bằng run mới |
| `quality_gate` failed | Xác định Q case; đối chiếu source counts, dbt tests, metric contract và source snapshot | Giữ failure evidence; không sửa expected value chỉ để làm xanh. Chỉ cập nhật baseline sau khi có giải thích và review nghiệp vụ |
| `upstream_failed` | Tìm task `failed` đầu tiên theo dependency graph | Sửa nguyên nhân gốc; không xử lý downstream state như lỗi độc lập |
| Import errors sau thay đổi code | `astro dev run dags list-import-errors`; kiểm tra freshness của source stage | Dừng stack, refresh stage bằng `uv run --active python scripts/project.py astro prepare` từ repo root, rồi `astro dev parse` và start lại |
| DuckDB lock/I/O error | Xác định process dùng file: DAG, dbt, UI, charts hoặc baselines | Dừng/đợi đúng process; không xóa `.duckdb`, `.wal` hoặc file lock để ép chạy tiếp |

Khi preflight fail do cấu hình nguồn và đã sửa xong, ưu tiên **tạo DAG run mới** để giữ run lỗi làm bằng chứng và chạy đủ preflight → ingestion → dbt → quality gate. Không đánh dấu task thành success thủ công. Chỉ Clear task instances sau khi xác định task nào cần chạy lại, ảnh hưởng upstream/downstream và trạng thái warehouse.

## Kiểm tra kết nối nguồn

Trên Windows host, dùng host đang cấu hình (không nhập username/password vào các lệnh):

```powershell
$sourceHost = "db.xomdata.com"
Resolve-DnsName $sourceHost
Test-NetConnection $sourceHost -Port 1433 -InformationLevel Quiet
```

DNS/TCP thành công chỉ xác nhận đường mạng. Kiểm tra login/database từ host:

```powershell
uv run --active python -m ingestion.check_source_connection
```

Và từ scheduler container:

```powershell
Set-Location orchestration
astro dev bash --scheduler
```

```bash
python -m ingestion.check_source_connection
exit
```

Host pass nhưng container fail thường do DNS/outbound network, biến chưa được inject hoặc driver/TLS khác nhau. Sau khi sửa `orchestration/.env`, restart Astro để container nhận cấu hình mới. Chỉ kiểm tra biến secrets có/thiếu, không in giá trị.

## Dừng và khởi động Astro

Từ thư mục `orchestration/`:

```powershell
astro dev stop
```

Trước lần chạy tiếp:

```powershell
astro dev start
astro dev ps
astro dev run db check
astro dev run dags list-import-errors
astro dev run dags list
```

Nếu đổi source code, dừng stack rồi refresh source stage theo [setup guide](setup.md). Không xóa Docker volumes hoặc Airflow PostgreSQL metadata để chữa lỗi DAG; thao tác đó có thể xóa lịch sử run mà không sửa nguyên nhân code/config.

## Ghi nhận và chia sẻ kết quả

Mỗi refresh nên ghi thời điểm, `dag_run_id`, trạng thái DAG, task đầu tiên fail (nếu có), bốn source row counts, total sales/profit và số baseline pass. Nếu gửi log chẩn đoán, chỉ trích phần liên quan sau khi redact credentials, tokens và định danh khách hàng.

Chi tiết runtime: [orchestration README](../orchestration/README.md) · [Phase 7 checkpoint](phase-07-airflow-cosmos.md) · [Q1–Q15 reconciliation](checkpoint-q1-q15-reconciliation.md).
