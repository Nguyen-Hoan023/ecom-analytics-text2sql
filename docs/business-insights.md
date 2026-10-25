# Business findings and decision questions

These findings describe the current 2020–2023 snapshot. They are decision prompts for follow-up analysis, not causal claims or operational recommendations by themselves. Amounts retain source units; currency and gross/net semantics are unconfirmed.

## Portfolio performance

The warehouse contains 51,290 sales lines and 25,728 distinct orders. Total sales are 6,517,674.00, total profit is 1,065,413.58, and aggregate profit margin is approximately 16.35%.

| Segment | Sales | Profit | Margin | Interpretation |
|---|---:|---:|---:|---|
| Corporate | 3,840,707.00 | 608,523.36 | 15.8% | Largest sales and profit contribution, lowest margin among the three segments. |
| Consumer | 2,146,780.00 | 365,377.50 | 17.0% | Second by sales/profit with higher margin than Corporate. |
| Self-Employed | 530,187.00 | 91,512.72 | 17.3% | Highest margin, smallest sales and profit contribution. |

**Question for the business:** Which specific products, discount levels, and order economics explain Corporate's lower margin? Do not infer budget allocation from margin alone.

## Discount and loss-making behavior

| Discount band | Sales lines | Loss-making line rate | Total profit |
|---|---:|---:|---:|
| 0% | 29,470 | 0.00% | 1,141,917.51 |
| (0, 20%] | 10,533 | 26.08% | 211,677.68 |
| (20%, 40%] | 4,430 | 52.05% | -51,387.30 |
| (40%, 60%] | 4,736 | 81.65% | -146,576.11 |
| >60% | 2,121 | 100.00% | -90,218.20 |

The observed high-discount bands have negative aggregate profit and higher loss-line rates. The pattern supports a targeted review of discount economics, but it does not show that discount alone caused losses. Product cost, product mix, customer/order selection, and promotion lift are not isolated by this observational dataset.

**Practical follow-up:** evaluate margin floors by product/category, compare incremental volume and contribution profit, then test any policy change with a controlled experiment.

## Customer and geography signals

- At the 2024-01-01 RFM snapshot, 3,483 of 17,415 customers are in the top monetary score group. A 90-day inactivity rule flags 14,660 customers, including 2,732 VIPs. This is historical and heuristic; refresh the source and validate future outcomes before any retention campaign.
- Loss-making order rates are about 20.5% for Self-Employed, 21.6% for Corporate, and 21.5% for Consumer. The order label is based on total order profit, not any single negative line.
- Market-level and country-level profitability vary substantially. Use the geography marts to prioritize drill-downs, while checking orphan and unknown geography and not assigning cause based on location alone.
- Product-pair counts are sparse at practical market-basket support thresholds. Do not use the current pair mart as a recommendation engine.

## Available visualizations

The ten static charts in [docs/assets/charts/](assets/charts/) cover executive KPIs, discount profitability, segment comparison, monthly trends, category mix, products, geography, RFM risk sensitivity, region behavior, and customer profile. Recreate them using the [visualization guide](../analytics/visualization/README.md).

## Metric caveats

Definitions and snapshot assumptions are in the [data contract](data-contract.md). In particular, do not label amounts with a currency, call the 90-day flag a churn prediction, or describe discount association as causal.
