# Customer marts

This folder contains customer analytics at three different grains. Direct Text-to-SQL access to customer-level RFM and region behavior is denied; the application exposes only approved aggregate templates for those restricted relations.

| Model | Grain | Important boundary |
|---|---|---|
| <code>mart_customer_rfm</code> | One row per customer at one snapshot date | Scores, VIP flag, and inactivity-risk flags are historical classifications, not labels of future churn. |
| <code>mart_customer_profile_by_gender_occupation</code> | Gender × occupation | Aggregate counts only; small groups must satisfy the configured minimum group size before a direct query is allowed. |
| <code>mart_customer_region_behavior</code> | One row per customer | Region-count and orphan-region diagnostics; sensitive customer-level details are served only through an approved summary template. |

## RFM conventions

The current snapshot is <code>2024-01-01</code>. Recency is measured in days from snapshot date to last transaction date. Frequency counts distinct orders. Monetary value sums source sales. Quintile scores are calculated within the eligible customer population; VIP uses the approved high monetary score definition. The 90-day risk flag is an inactivity heuristic, not a model trained on churn outcomes.

Do not export customer identifiers, individual scores, or customer-level result rows to model prompts, charts, reports, or public examples. See <code>text2sql/access_policy.yml</code> for the exact query policy.
