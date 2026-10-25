# Geography marts

| Model | Grain | Main use |
|---|---|---|
| <code>mart_profitability_by_market</code> | One row per market | Compare line/order counts, sales, profit, and margin by market. |
| <code>mart_top_countries_by_sales</code> | Ranked known country plus unknown bucket | Rank the top 15 known countries by sales while retaining unknown geography for reconciliation. |

## Join and ranking rules

Geography attributes come from the region dimension joined through <code>int_sales_enriched</code>. Do not remove the unknown bucket from completeness checks. The ranked known-country list uses a stable secondary ordering for ties; the unknown aggregate is preserved separately and has no known-country rank.

Regional results use source geography labels and descriptive aggregation. A country or market difference is not a causal explanation for profitability. See the parent [Gold mart guide](../README.md) for shared metric definitions.
