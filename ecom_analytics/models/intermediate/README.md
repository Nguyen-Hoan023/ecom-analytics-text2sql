# Intermediate sales enrichment

<code>int_sales_enriched</code> is the reusable sales-line fact that joins the cleaned transaction model to customer, product, and region attributes.

## Grain and joins

- **Grain:** one row per <code>sales_line_id</code>, inherited from <code>stg_ecom_sales</code>.
- **Join keys:** <code>customer_id</code>, <code>product_code</code>, and <code>region_code</code>.
- **Join type:** left joins preserve sales when a dimension key is unmatched.
- **Unknown handling:** missing/unmatched dimension attributes become explicit unknown values while original foreign keys stay available for diagnostics.

The model must not multiply sales lines. The singular test <code>assert_int_sales_enriched_row_count.sql</code> compares its row count with staging and fails if enrichment changes the fact population.

## Downstream use

Gold sales, product, geography, and customer-behavior marts use this model to share consistent dimension mapping. Do not duplicate the three joins independently in each mart unless a documented grain requires it.

## Change checklist

If you change joins or dimension attributes, check the row-count contract, orphan-key diagnostics, totals for sales and profit, and each affected Gold mart. Build from the repository root:

    uv run --project . python scripts/project.py dbt build --select int_sales_enriched+
