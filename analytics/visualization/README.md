# Gold visualizations

This module generates a reproducible set of static charts from the Gold marts in DuckDB. It never connects to SQL Server and opens the warehouse in read-only mode.

## Run

Run from the repository root after DLT ingestion and a successful dbt build:

```powershell
uv run --active python analytics/visualization/generate_charts.py
```

The script checks that its required Gold marts exist and reconciles sales-line counts, total sales, and total profit across the segment, discount, and monthly marts before creating images.

## Output

Charts are written to `docs/assets/charts/`:

| File | Source mart(s) | What it shows |
|---|---|---|
| `01_executive_overview.png` | Sales by segment, monthly sales, customer RFM | Total sales, profit, margin, orders, sales lines, customers and reporting period |
| `02_discount_profitability.png` | Discount profitability | Total profit and loss-making line rate by discount band |
| `03_segment_profitability.png` | Sales by segment | Total sales, total profit and profit margin as separate measures |
| `04_monthly_performance.png` | Monthly sales | Sales, profit and YoY sales growth |
| `05_category_mix_by_segment.png` | Category sales mix by segment | Share of each category within its segment |
| `06_product_performance.png` | Product performance | Top products by units sold and total profit |
| `07_geography_performance.png` | Market profitability, top countries | Market profit margin and top 10 countries by sales |
| `08_rfm_risk_sensitivity.png` | Customer RFM | Inactivity-risk counts at 60, 90 and 180 days, including VIPs |
| `09_customer_region_behavior.png` | Customer region behavior | Customers by number of matched region codes in transaction history |
| `10_customer_profile.png` | Gender and occupation profile | Aggregate customer counts by gender and occupation |

## Interpretation notes

- Monetary values retain the source unit; no currency symbol is inferred.
- Discount charts compare observed transaction groups and do not establish causality.
- RFM inactivity risk is a heuristic evaluated at the `2024-01-01` snapshot, not a churn label.
- Unknown geography and products are kept visible in mart-level reconciliation and excluded from ranked known-market/product comparisons where applicable.
- Category labels follow the source taxonomy, which has known quality concerns documented in `docs/phase-01-data-understanding.md`.
- The market-basket mart is intentionally not charted as a recommendation: current SKU pair counts are too sparse at the reviewed support thresholds.
