# Sales marts

This domain contains four aggregate views for revenue/profit trends, discount behavior, and order-level loss.

| Model | Grain | Main use |
|---|---|---|
| <code>mart_sales_by_segment</code> | One row per segment | Compare sales, profit, order count, and margin by segment. |
| <code>mart_monthly_sales</code> | One row per calendar month | Trend sales/profit and year-over-year sales growth. |
| <code>mart_discount_profitability</code> | Category × discount band | Compare line/order counts, average discount, sales, profit, and loss-line rate. |
| <code>mart_loss_making_orders_by_segment</code> | One row per segment | Count orders whose aggregated line profit is negative. |

## Definitions to preserve

A loss-making order is based on total profit summed across its sales lines, not whether any individual line is negative. The discount band is derived from the source discount fraction; keep boundary semantics stable when editing band labels. Profit margin is aggregated profit divided by aggregated sales.

A negative aggregate in a high-discount band is an association in the observed snapshot, not evidence that discount caused the loss. Before a decision, segment the result by product/category and validate policy changes with a controlled experiment.

Inspect model SQL and YAML in this directory. Use the parent [Gold marts guide](../README.md) for shared metric rules and tests.
