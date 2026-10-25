# Business Analytics Query Results

## Snapshot and interpretation

This page presents the business outputs for the 15 approved analytical questions. Values come from the reconciled 2020-01-01 through 2023-12-31 snapshot and the Gold marts. The warehouse baseline suite has a recorded result of 15/15 cases passed. This is historical evidence for the stated snapshot, not a guarantee that a future refresh returns the same values.

Amounts retain source units. Currency and whether `sales` is gross or net have not been confirmed. The RFM snapshot date is 2024-01-01. See the [metric and source contract](data-contract.md), [reconciliation report](../reports/warehouse-reconciliation.md), and [business insights](business-insights.md) for definitions, provenance, and limitations.

## Headline results

| Measure | Result |
|---|---:|
| Sales lines | 51,290 |
| Distinct orders | 25,728 |
| Total sales | 6,517,674.00 |
| Total profit | 1,065,413.58 |
| Profit margin (`total_profit / total_sales`) | 16.35% |
| Weighted average discount across sales lines | 14.2883% |

Sales lines, orders, sales, and profit reconcile across the documented Gold marts. The numbers are full-period totals over four years, not annualized results.

## Results by business question

| Q | Business question | Result from this snapshot | Gold mart / interpretation |
|---:|---|---|---|
| 1 | What are total revenue and profit? | 51,290 sales lines; 25,728 orders; sales 6,517,674.00; profit 1,065,413.58; margin 16.35%. | `mart_sales_by_segment` and `mart_monthly_sales`; full 2020–2023 total in source units. |
| 2 | How do sales and profit compare by segment? | Corporate: sales 3,840,707.00, profit 608,523.36, margin 15.84%. Consumer: 2,146,780.00, 365,377.50, 17.02%. Self-Employed: 530,187.00, 91,512.72, 17.26%. | `mart_sales_by_segment`; segment is the transaction fact’s segment value. |
| 3 | Which 10 products sold the most units? | Leaders: P000116 (1,780 units; sales 67,640), P000619 (1,195; 15,535), P000512 (518; 16,058), P000114 (476; 2,380), P001501 (462; 5,082). The remaining five products are listed in the [reconciliation evidence](../reports/warehouse-reconciliation.md). | `mart_product_performance`; “best-selling” means units sold, not revenue or profit. |
| 4 | How many customers are in each gender × occupation group? | 15 groups meet the minimum count of 10; all groups reconcile to a population of 17,415. Unknown values are retained. | `mart_customer_profile_by_gender_occupation`; group-level counts, not customer-level records. |
| 5 | What is average discount by product category? | Weighted average discount is 14.2883% across 51,290 lines and six categories including Unknown. | `mart_discount_profitability`; line-weighted and includes zero-discount lines. Source taxonomy quality limits category interpretation. |
| 6 | What is profit margin by market? | Six market groups were reconciled; overall sales are 6,517,674.00 and profit is 1,065,413.58. The Unknown group has 2 lines, 1 order, sales 486.00, and profit 243.00. | `mart_profitability_by_market`; Unknown is kept separate and is not assigned to a named market. |
| 7 | How many loss-making orders are there by segment? | Consumer: 2,864 of 13,291 orders. Corporate: 1,667 of 7,724. Self-Employed: 965 of 4,713. | `mart_loss_making_orders_by_segment`; an order is loss-making when the sum of its line profit is below zero. Approximate rates are 21.55%, 21.58%, and 20.48%, respectively. |
| 8 | How many VIP customers are at risk of churn? | At 2024-01-01: 17,415 customers scored, 3,483 VIPs. With a 90-day inactivity threshold: 14,660 customers at risk, including 2,732 VIPs. | `mart_customer_rfm`; aggregate-only approved result. Risk is a recency heuristic, not a churn label or current state. |
| 9 | How does category mix differ between Consumer and Corporate? | 12 segment × category rows (six categories per segment); category shares reconcile to 100% of each segment’s sales. | `mart_category_sales_mix_by_segment`; reports revenue mix, not products bought together or causal cross-sell impact. |
| 10 | Which 15 countries have the highest sales? | Leaders: United States (sales 1,326,577; 4,998 orders), Australia (381,404; 1,419), France (374,791; 1,473). Unknown geography is retained separately, not ranked as an identified country. | `mart_top_countries_by_sales`; ranking is by sales. The mart and baseline reconcile for all 15 ranked countries. |
| 11 | How does monthly sales change year over year? | 48 contiguous months from Jan 2020 to Dec 2023; monthly totals reconcile to sales 6,517,674.00 and profit 1,065,413.58. Dec 2023 sales were 280,918. | `mart_monthly_sales`; YoY growth is unavailable for the first 12 months because the comparison period is absent. |
| 12 | Which three products have the highest profit in each category? | The top product in each identified category: Body care P000116 (profit 9,089.67); Face care P002117 (3,727.15); Hair care P002215 (6,071.38); Home and Accessories P002715 (3,487.15); Make up P000222 (3,979.41). | `mart_product_performance`; 15 ranked rows total. Unknown-category products are excluded from business ranking but retained in the mart. |
| 13 | How many customers shop across multiple regions? | Population 17,415; 5,087 customers have matched sales in multiple regions; one customer has orphan-region activity; maximum matched regions per customer is 9. Orphan activity: 2 lines, sales 486.00, profit 243.00. | `mart_customer_region_behavior`; only approved aggregate output is exposed; no customer identifiers. |
| 14 | How are customers distributed across RFM scores? | At 2024-01-01, all 17,415 customers are scored and none lack purchase history. Each quintile contains 3,483 customers for Recency, Frequency, and Monetary. | `mart_customer_rfm`; numeric quintile scores, not lifecycle segments such as “Champions.” |
| 15 | Which products are commonly bought together? | No pair qualifies at the default 0.5% support threshold (129 orders required). The most frequent pair occurs in 3 orders; 12 pairs appear only at the exploratory 0.01% threshold. | `mart_market_basket_associations`; the default result is empty. Sparse pairs do not support a cross-sell recommendation. |

## Discount and profit detail

| Discount band | Sales lines | Loss-making lines | Loss-line rate | Total sales | Total profit |
|---|---:|---:|---:|---:|---:|
| 0% | 29,470 | 0 | 0.00% | 3,647,815 | 1,141,917.51 |
| (0%, 20%] | 10,533 | 2,747 | 26.08% | 1,396,693 | 211,677.68 |
| (20%, 40%] | 4,430 | 2,306 | 52.05% | 594,576 | -51,387.30 |
| (40%, 60%] | 4,736 | 3,867 | 81.65% | 616,105 | -146,576.11 |
| >60% | 2,121 | 2,121 | 100.00% | 262,485 | -90,218.20 |

In this snapshot, aggregate profit turns negative above the 20% discount band and loss-line rate increases across higher bands. This is a useful signal for reviewing product-level margin floors, promotion mechanics, and incremental contribution. The data is observational and does not isolate discount effects from product mix, costs, seasonality, or customer selection.

The line-weighted average discount by category is:

| Category | Sales lines | Average discount |
|---|---:|---:|
| Body care | 26,400 | 14.26% |
| Face care | 3,183 | 14.14% |
| Hair care | 7,065 | 14.15% |
| Home and Accessories | 7,849 | 14.64% |
| Make up | 6,791 | 14.22% |
| Unknown | 2 | 0.00% |

## Market profitability

| Market | Sales lines | Orders | Total sales | Total profit | Profit margin |
|---|---:|---:|---:|---:|---:|
| Asia Pacific | 14,300 | 7,080 | 1,831,162.00 | 228,499.59 | 12.48% |
| Europe | 11,729 | 6,013 | 1,487,444.00 | 331,644.70 | 22.30% |
| USCA | 10,378 | 5,203 | 1,372,045.00 | 222,770.12 | 16.24% |
| LATAM | 10,294 | 5,144 | 1,339,726.00 | 216,042.72 | 16.13% |
| Africa | 4,587 | 2,288 | 486,811.00 | 66,213.45 | 13.60% |
| Unknown | 2 | 1 | 486.00 | 243.00 | 50.00% |

Among identified markets, Asia Pacific has the highest sales and Europe the highest margin. Do not interpret the 50% margin for Unknown as a meaningful market result: it is based on two orphan-region sales lines.

## Product leaders

Top products by units sold:

| Rank | Product code | Units sold | Total sales |
|---:|---|---:|---:|
| 1 | P000116 | 1,780 | 67,640.00 |
| 2 | P000619 | 1,195 | 15,535.00 |
| 3 | P000512 | 518 | 16,058.00 |
| 4 | P000114 | 476 | 2,380.00 |
| 5 | P001501 | 462 | 5,082.00 |

Top-profit product in each identified category:

| Category | Product code | Total profit |
|---|---|---:|
| Body care | P000116 | 9,089.67 |
| Face care | P002117 | 3,727.15 |
| Hair care | P002215 | 6,071.38 |
| Home and Accessories | P002715 | 3,487.15 |
| Make up | P000222 | 3,979.41 |

The source product taxonomy is preserved. Some product labels do not appear consistent with their source category, so category-level findings need taxonomy review before they drive assortment decisions.

## RFM threshold sensitivity

| Inactivity threshold | Customers at risk | VIP customers at risk |
|---:|---:|---:|
| 60 days | 15,339 | 2,901 |
| 90 days | 14,660 | 2,732 |
| 180 days | 12,584 | 2,255 |

The threshold changes the size of the flagged population. Select a threshold using business context and validation against later customer outcomes; these counts alone do not establish predictive quality.

## Validation and limits

- The recorded warehouse baseline suite passed 15/15 cases for the referenced snapshot. The executable contracts live in [`text2sql/evaluation/golden_set_v1.yml`](../text2sql/evaluation/golden_set_v1.yml).
- Source-to-mart reconciliation evidence and data-quality risks are documented in the [warehouse reconciliation report](../reports/warehouse-reconciliation.md).
- `sales` and `profit` retain source units. Currency and gross/net semantics remain unconfirmed.
- Product category labels have known source inconsistencies. They are preserved rather than silently remapped.
- Orphan product and region keys remain visible as Unknown/unmatched so joins do not silently remove fact rows.
- RFM is historical and heuristic. Refresh the data and validate against later outcomes before operational use.
- High-discount association is not causal evidence. The basket mart’s default result is empty and is not a recommendation engine.

## Related charts

See the [project README](../README.md) for the Executive Dashboards & Gold Visualizations gallery, or use the [chart index](assets/charts/README.md) to regenerate them.
