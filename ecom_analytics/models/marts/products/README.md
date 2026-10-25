# Product marts

| Model | Grain | Main use |
|---|---|---|
| <code>mart_product_performance</code> | One row per product code | Compare units sold, sales, profit, order counts, and product/category ranks. |
| <code>mart_category_sales_mix_by_segment</code> | Segment × category | Compare category sales and share within each segment; category shares reconcile to segment totals. |
| <code>mart_market_basket_associations</code> | One unordered product pair | Explore within-order co-occurrence, support, confidence, and lift. |

## Interpretation and limits

- Product rankings use deterministic tie-breaks in SQL; keep those order rules aligned with the documented rank.
- Unknown products are retained for reconciliation but should not be presented as known SKU recommendations.
- Basket pairs are built from distinct products per order, so duplicate lines of a product do not inflate pair counts.
- A basket association is co-occurrence, not causation or proof of recommendation effectiveness. Current counts are sparse at practical support thresholds; evaluate thresholds and stability before using this mart for merchandising.

The mart YAML files document exposed columns. Singular tests assert category-mix grain and basket pair uniqueness.
