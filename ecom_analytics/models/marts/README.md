# Gold analytics marts

Gold marts are the stable, documented query interface for dashboards and Text-to-SQL. Each model is aggregated to an explicit business grain except customer-level marts, whose direct access is restricted by the Text-to-SQL policy.

## Mart domains

| Folder | Models | Typical grain |
|---|---|---|
| <code>sales/</code> | Segment performance, monthly performance, discount bands, loss-making orders | Segment; month; category × discount band; segment |
| <code>products/</code> | Product performance, category mix by segment, market-basket pairs | Product; segment × category; unordered product pair |
| <code>customers/</code> | RFM, gender × occupation profile, region behavior | Customer snapshot; demographic group; customer |
| <code>geography/</code> | Market profitability, top countries | Market; ranked country plus explicit unknown bucket |

Open each folder README for model definitions, interpretation, and the grain contract.

## Shared metric conventions

- <code>sales_line_count</code> counts fact rows; <code>order_count</code> counts distinct order IDs.
- <code>total_sales</code> and <code>total_profit</code> are sums of source columns and preserve source units.
- <code>profit_margin</code> is total profit divided by total sales; never average row-level margins.
- Loss-making orders are classified by the summed profit of all lines in an order.
- Empty or unmatched dimensions remain visible as <code>Unknown</code> where the model defines that bucket.
- The RFM mart is a historical customer snapshot, not a continuously updated churn model.
- Market-basket support thresholds are intentionally conservative; sparse results must not be promoted to recommendations without validation.

## Contracts

Adjacent YAML files describe models and columns. Singular tests in <code>ecom_analytics/tests/</code> check selected grains, line preservation, and reconciliations. Run a full build and compare the semantic catalog contract before changing a Gold output consumed by Text-to-SQL.
