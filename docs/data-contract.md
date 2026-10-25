# Source and metric contract

This document records the analytical contract for the current source snapshot. It separates observed source facts from business assumptions so downstream models, charts, and Text-to-SQL do not silently redefine a metric.

## Source relations and grain

The configured SQL Server schema provides four relations:

| Relation | Observed rows | Key used by the pipeline | Analytical role |
|---|---:|---|---|
| <code>customer</code> | 17,415 | <code>customer_id</code> | Customer attributes; no names/email in the dbt staging output. |
| <code>ecom_sales</code> | 51,290 | <code>row_id</code> → <code>sales_line_id</code> | Transaction-line fact. |
| <code>product</code> | 28,356 | <code>product_code</code> | Product attributes and category taxonomy. |
| <code>region</code> | 3,828 | <code>region_code</code> | Country, market, and region attributes. |

The fact grain is one row per source sales line. The observed period is 2020-01-01 through 2023-12-31, with 25,728 distinct orders. A transaction line is not an order; aggregate order measures by distinct <code>order_id</code>.

## Join coverage and preservation

Customer keys matched in the profiled snapshot. Product and region each had two unmatched fact references; one sales line was unmatched in both dimensions. The union was three distinct affected fact rows, representing total sales 506 and profit 253 in source units.

The intermediate fact uses left joins and preserves original keys. Unknown/unmatched dimensions remain visible so joins do not silently remove sales. Do not invent replacement dimension keys without source-owner confirmation.

## Metric definitions

| Metric | Contract |
|---|---|
| <code>sales_line_count</code> | Count of sales fact rows at the model grain. |
| <code>order_count</code> | Count of distinct non-null order IDs. |
| <code>units_sold</code> | Sum of source quantity; do not multiply sales by quantity. |
| <code>total_sales</code> | Sum of source <code>sales</code>, retaining source units. |
| <code>total_profit</code> | Sum of source <code>profit</code>, retaining source units. |
| <code>profit_margin</code> | Aggregate profit divided by aggregate sales. Do not average row-level margins. |
| <code>average_discount</code> | Arithmetic mean of the source discount fraction over the included sales lines. |
| Loss-making line | A sales line whose source profit is below zero. |
| Loss-making order | An order whose summed profit across all its lines is below zero. One negative line does not make an order loss-making if order-level profit remains positive. |
| Segment | Taken from the sales fact row; it is not treated as a permanent customer attribute. |
| Sales share by category | Category sales divided by total sales for the same segment; shares should reconcile within each segment. |

### Discount bands

The source stores discount as a fraction from 0 to 1. The current mart uses the following mutually exclusive groups: <code>0%</code>, <code>(0, 20%]</code>, <code>(20%, 40%]</code>, <code>(40%, 60%]</code>, <code>&gt;60%</code>, and an explicit unknown bucket when needed. Keep boundary rules stable across SQL, charts, and the semantic catalog.

## Customer and product definitions

- RFM is a historical snapshot dated <code>2024-01-01</code>.
- Recency is days from snapshot date to last order date; frequency is distinct orders; monetary value is summed source sales.
- Scores are quintiles in the eligible snapshot population with stable tie-breaking. VIP is the top monetary score group.
- 90-day churn risk is an inactivity threshold heuristic. It is not a labeled churn outcome or a future prediction.
- Market-basket support is the fraction of valid orders containing a distinct unordered product pair. Pair counts are sparse: at 0.5% support the minimum required count is 129 while the observed maximum pair count is 3. Lowering support creates exploratory pairs, not validated recommendations.

## Snapshot profile

The profiled snapshot contains 51,290 fact lines, total sales 6,517,674.00, and total profit 1,065,413.58. There were 11,041 negative-profit lines and 5,496 orders with negative total profit. Discount ranged from 0 to 0.85, with mean 0.142883; 29,470 lines had zero discount.

## Unconfirmed assumptions and change control

- Source currency is unknown. Monetary values must not be labeled with a currency symbol.
- It is unconfirmed whether source sales is gross or net of discounts/taxes.
- Discount/profit relationships are observational and do not establish causality.
- Source category labels have quality/inconsistency concerns; preserve the source taxonomy until it is reconciled with the data owner.
- The source snapshot ends in 2023; customer risk must not be described as current.

If source schema, key coverage, grain, or business definitions change, update this contract, dbt model/YAML tests, the semantic catalog, and affected golden evaluation cases together. The diagnostic SQL is in [sql/source_profile.sql](../sql/source_profile.sql).
