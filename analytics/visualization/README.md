# Static Gold visualizations

This package generates ten reproducible aggregate charts from DuckDB Gold marts. It opens the warehouse read-only and never connects to SQL Server.

## Run

Build the warehouse first by loading the source snapshot and running dbt. Then, from the repository root:

    uv run --project . python scripts/project.py charts

The command wrapper resolves the database path. The generator checks its required marts and reconciles key line-count, sales, and profit totals before creating charts. Output files are written to <code>docs/assets/charts/</code>.

## Chart inventory

| File | Mart inputs | Question |
|---|---|---|
| <code>01_executive_overview.png</code> | Sales by segment, monthly sales, customer RFM | What are the headline sales, profit, margin, orders, customers, and period? |
| <code>02_discount_profitability.png</code> | Discount profitability | How do profit and loss-line counts vary by discount band? |
| <code>03_segment_profitability.png</code> | Sales by segment | How do sales, profit, and margin compare by segment? |
| <code>04_monthly_performance.png</code> | Monthly sales | How do sales and profit trend over time and compare year over year? |
| <code>05_category_mix_by_segment.png</code> | Category sales mix | How does category share differ by segment? |
| <code>06_product_performance.png</code> | Product performance | Which products lead by units sold and total profit? |
| <code>07_geography_performance.png</code> | Market and country marts | How do markets compare and which countries rank by sales? |
| <code>08_rfm_risk_sensitivity.png</code> | Customer RFM | How sensitive are inactivity-risk counts to the 60/90/180-day thresholds? |
| <code>09_customer_region_behavior.png</code> | Customer region behavior | How many customers have sales across multiple matched regions? |
| <code>10_customer_profile.png</code> | Demographic profile | How is the customer population distributed by gender and occupation? |

See [chart assets](../../docs/assets/charts/README.md) for file-level notes.

## Interpretation and privacy

- Monetary values retain source units; the charts do not infer a currency symbol.
- Discount comparisons are descriptive and do not establish causality.
- RFM risk is a recency heuristic at the historical snapshot, not a labeled churn outcome.
- Unknown geography and product values remain visible when needed for reconciliation.
- The chart generator reads Gold aggregates and does not export customer-level identifiers.
- Market-basket pairs are not presented as recommendations because current product-pair support is sparse.
