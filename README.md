# E-Commerce Analytics & Text-to-SQL

A learning project to rebuild an end-to-end analytics pipeline from the Xóm E-Com dataset, following the reference flow while documenting design choices and validating each layer.

## Project goals

- Answer the 15 business questions in the Xóm E-Com context with traceable, tested data models.
- Build the flow incrementally: SQL Server source → DLT ingestion → DuckDB → dbt Bronze/Silver/Gold → analytics and Text-to-SQL.
- Keep Apache Airflow/Cosmos in the planned architecture, then add orchestration after the data pipeline works locally.
- Treat the reference repository as a design reference; verify assumptions against the live source and explain changes.

## Current status

## Current status

- **Phase 1 — Data understanding:** Hoàn tất source profile và metric contract v1. Đã ghi nhận các giả định nghiệp vụ, orphan keys và vấn đề taxonomy.
- **Phase 2 — Project setup:** Hoàn tất môi trường Python, dependency lockfile và cấu hình secrets qua `.env`.
- **Phase 3 — Ingestion:** DLT đã nạp snapshot từ SQL Server vào DuckDB Bronze. Row count của cả bốn bảng khớp nguồn.
- **Phase 4 — dbt transformation:** Đã xây Silver, Intermediate và sáu Gold marts. Đang hoàn thiện validation, tài liệu và các câu hỏi phân tích còn thiếu.
- **Phase 5 — Business analysis:** Đã kiểm tra một phần kết quả marts; chưa hoàn thành đủ 15 câu hỏi.
- **Phase 6 — Text-to-SQL:** Chưa triển khai.
- **Phase 7 — Airflow/Cosmos:** Chưa triển khai; sẽ thực hiện sau khi pipeline chạy ổn định độc lập.
## Planned stages

| Stage | Outcome | Status |
|---|---|---|
| 1. Understand the source | Verified source profile and metric contract | Complete |
| 2. Set up the project | Reproducible Python environment and configuration | Complete |
| 3. Ingest with DLT | SQL Server snapshot loaded into DuckDB Bronze | Complete |
| 4. Transform with dbt | Silver, Intermediate and Gold models | In progress |
| 5. Answer business questions | Complete and validate all 15 questions | In progress |
| 6. Add Text-to-SQL | Constrained generation, validation and evaluation | Not started |
| 7. Orchestrate with Airflow/Cosmos | Schedule and monitor the working pipeline | Not started |
| 8. Polish and publish | Documentation, CI and project walkthrough | Not started |
## Security and data handling

- Never commit .env files, API keys, source credentials, local database files, or source extracts.
- Phase 1 profiling is read-only and avoids selecting names, emails, or other customer-level PII.
- Share only aggregate profiling results in issues or documentation.

## Reference material

- [Xóm E-Com schema and business context](https://dataset.xomdata.com/datasets/schema/e_commerce)
- [Reference implementation](https://github.com/tunguyenn99/a-simple-t2s-flow)
- [Reference business context and 15 questions](https://github.com/tunguyenn99/a-simple-t2s-flow/blob/main/context.md)
