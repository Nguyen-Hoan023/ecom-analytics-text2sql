/*
Phase 1: read-only source profile for Xom e_commerce schema (SQL Server).

How to run:
  1. Connect in SSMS/DBeaver/DataGrip to the database containing schema e_commerce.
  2. Run this file as a read-only account if available.
  3. Record aggregate results in docs/phase-01-data-understanding.md.

This script contains SELECT statements only. It deliberately avoids names,
emails and raw customer samples so its result sets are safe to summarize.
*/

SET NOCOUNT ON;

-- 1. Actual source metadata: use this to detect schema drift before ingestion.
SELECT
    TABLE_SCHEMA,
    TABLE_NAME,
    ORDINAL_POSITION,
    COLUMN_NAME,
    DATA_TYPE,
    CHARACTER_MAXIMUM_LENGTH,
    NUMERIC_PRECISION,
    NUMERIC_SCALE,
    IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'e_commerce'
  AND TABLE_NAME IN ('customer', 'ecom_sales', 'product', 'region')
ORDER BY TABLE_NAME, ORDINAL_POSITION;

-- 2. Exact row counts (the website displays rounded counts).
SELECT 'customer' AS table_name, COUNT_BIG(*) AS row_count FROM e_commerce.customer
UNION ALL
SELECT 'ecom_sales', COUNT_BIG(*) FROM e_commerce.ecom_sales
UNION ALL
SELECT 'product', COUNT_BIG(*) FROM e_commerce.product
UNION ALL
SELECT 'region', COUNT_BIG(*) FROM e_commerce.region;

-- 3. Null counts for every column. This checks completeness without exposing values.
SELECT 'customer.customer_id' AS column_name, COUNT_BIG(*) AS row_count,
       SUM(CASE WHEN customer_id IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS null_count
FROM e_commerce.customer
UNION ALL SELECT 'customer.first_name', COUNT_BIG(*), SUM(CASE WHEN first_name IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.customer
UNION ALL SELECT 'customer.last_name', COUNT_BIG(*), SUM(CASE WHEN last_name IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.customer
UNION ALL SELECT 'customer.birth_date', COUNT_BIG(*), SUM(CASE WHEN birth_date IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.customer
UNION ALL SELECT 'customer.marital_status', COUNT_BIG(*), SUM(CASE WHEN marital_status IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.customer
UNION ALL SELECT 'customer.gender', COUNT_BIG(*), SUM(CASE WHEN gender IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.customer
UNION ALL SELECT 'customer.email_address', COUNT_BIG(*), SUM(CASE WHEN email_address IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.customer
UNION ALL SELECT 'customer.annual_income', COUNT_BIG(*), SUM(CASE WHEN annual_income IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.customer
UNION ALL SELECT 'customer.education_level', COUNT_BIG(*), SUM(CASE WHEN education_level IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.customer
UNION ALL SELECT 'customer.occupation', COUNT_BIG(*), SUM(CASE WHEN occupation IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.customer
UNION ALL SELECT 'customer.home_owner', COUNT_BIG(*), SUM(CASE WHEN home_owner IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.customer
UNION ALL SELECT 'ecom_sales.row_id', COUNT_BIG(*), SUM(CASE WHEN row_id IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.ecom_sales
UNION ALL SELECT 'ecom_sales.order_id', COUNT_BIG(*), SUM(CASE WHEN order_id IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.ecom_sales
UNION ALL SELECT 'ecom_sales.order_date', COUNT_BIG(*), SUM(CASE WHEN order_date IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.ecom_sales
UNION ALL SELECT 'ecom_sales.customer_id', COUNT_BIG(*), SUM(CASE WHEN customer_id IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.ecom_sales
UNION ALL SELECT 'ecom_sales.segment', COUNT_BIG(*), SUM(CASE WHEN segment IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.ecom_sales
UNION ALL SELECT 'ecom_sales.region_code', COUNT_BIG(*), SUM(CASE WHEN region_code IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.ecom_sales
UNION ALL SELECT 'ecom_sales.product_code', COUNT_BIG(*), SUM(CASE WHEN product_code IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.ecom_sales
UNION ALL SELECT 'ecom_sales.quantity', COUNT_BIG(*), SUM(CASE WHEN quantity IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.ecom_sales
UNION ALL SELECT 'ecom_sales.sales', COUNT_BIG(*), SUM(CASE WHEN sales IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.ecom_sales
UNION ALL SELECT 'ecom_sales.discount', COUNT_BIG(*), SUM(CASE WHEN discount IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.ecom_sales
UNION ALL SELECT 'ecom_sales.profit', COUNT_BIG(*), SUM(CASE WHEN profit IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.ecom_sales
UNION ALL SELECT 'product.product_code', COUNT_BIG(*), SUM(CASE WHEN product_code IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.product
UNION ALL SELECT 'product.product', COUNT_BIG(*), SUM(CASE WHEN product IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.product
UNION ALL SELECT 'product.category', COUNT_BIG(*), SUM(CASE WHEN category IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.product
UNION ALL SELECT 'product.subcategory', COUNT_BIG(*), SUM(CASE WHEN subcategory IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.product
UNION ALL SELECT 'region.region_code', COUNT_BIG(*), SUM(CASE WHEN region_code IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.region
UNION ALL SELECT 'region.city', COUNT_BIG(*), SUM(CASE WHEN city IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.region
UNION ALL SELECT 'region.state', COUNT_BIG(*), SUM(CASE WHEN state IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.region
UNION ALL SELECT 'region.country', COUNT_BIG(*), SUM(CASE WHEN country IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.region
UNION ALL SELECT 'region.country_latitude', COUNT_BIG(*), SUM(CASE WHEN country_latitude IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.region
UNION ALL SELECT 'region.country_longitude', COUNT_BIG(*), SUM(CASE WHEN country_longitude IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.region
UNION ALL SELECT 'region.region', COUNT_BIG(*), SUM(CASE WHEN region IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.region
UNION ALL SELECT 'region.market', COUNT_BIG(*), SUM(CASE WHEN market IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) FROM e_commerce.region
ORDER BY column_name;

-- 4. Candidate key nulls and distinct counts.
SELECT
    'customer.customer_id' AS candidate_key,
    COUNT_BIG(*) AS row_count,
    COUNT_BIG(customer_id) AS non_null_count,
    COUNT(DISTINCT customer_id) AS distinct_non_null_count
FROM e_commerce.customer
UNION ALL
SELECT 'ecom_sales.row_id', COUNT_BIG(*), COUNT_BIG(row_id), COUNT(DISTINCT row_id)
FROM e_commerce.ecom_sales
UNION ALL
SELECT 'product.product_code', COUNT_BIG(*), COUNT_BIG(product_code), COUNT(DISTINCT product_code)
FROM e_commerce.product
UNION ALL
SELECT 'region.region_code', COUNT_BIG(*), COUNT_BIG(region_code), COUNT(DISTINCT region_code)
FROM e_commerce.region;

-- 5. Duplicate candidate keys. Any returned row must be explained before joins.
SELECT customer_id AS duplicate_key, COUNT_BIG(*) AS occurrences
FROM e_commerce.customer
GROUP BY customer_id
HAVING COUNT_BIG(*) > 1;

SELECT row_id AS duplicate_key, COUNT_BIG(*) AS occurrences
FROM e_commerce.ecom_sales
GROUP BY row_id
HAVING COUNT_BIG(*) > 1;

SELECT product_code AS duplicate_key, COUNT_BIG(*) AS occurrences
FROM e_commerce.product
GROUP BY product_code
HAVING COUNT_BIG(*) > 1;

SELECT region_code AS duplicate_key, COUNT_BIG(*) AS occurrences
FROM e_commerce.region
GROUP BY region_code
HAVING COUNT_BIG(*) > 1;

-- 6. Fact-table shape, date coverage, nulls and basic numeric ranges.
SELECT
    COUNT_BIG(*) AS sales_rows,
    COUNT(DISTINCT row_id) AS distinct_row_ids,
    COUNT(DISTINCT order_id) AS distinct_non_null_orders,
    SUM(CASE WHEN order_id IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS null_order_id_rows,
    SUM(CASE WHEN order_date IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS null_order_date_rows,
    MIN(order_date) AS min_order_date,
    MAX(order_date) AS max_order_date,
    SUM(CASE WHEN quantity IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS null_quantity_rows,
    SUM(CASE WHEN quantity = 0 THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS zero_quantity_rows,
    SUM(CASE WHEN quantity < 0 THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS negative_quantity_rows,
    MIN(quantity) AS min_quantity,
    MAX(quantity) AS max_quantity,
    SUM(CASE WHEN sales IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS null_sales_rows,
    SUM(CASE WHEN sales = 0 THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS zero_sales_rows,
    SUM(CASE WHEN sales < 0 THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS negative_sales_rows,
    MIN(sales) AS min_sales,
    MAX(sales) AS max_sales,
    SUM(CASE WHEN profit IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS null_profit_rows,
    SUM(CASE WHEN profit < 0 THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS negative_profit_lines,
    MIN(profit) AS min_profit,
    MAX(profit) AS max_profit
FROM e_commerce.ecom_sales;

-- 7. Discount scale and range. Do not label as percent until min/max are reviewed.
SELECT
    COUNT_BIG(*) AS sales_rows,
    SUM(CASE WHEN discount IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS null_discount_rows,
    MIN(discount) AS min_discount,
    MAX(discount) AS max_discount,
    AVG(discount) AS avg_discount,
    SUM(CASE WHEN discount < 0 THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS negative_discount_rows,
    SUM(CASE WHEN discount > 1 THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS discount_over_one_rows,
    SUM(CASE WHEN discount > 100 THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS discount_over_100_rows
FROM e_commerce.ecom_sales;

SELECT discount, COUNT_BIG(*) AS sales_rows
FROM e_commerce.ecom_sales
GROUP BY discount
ORDER BY discount;

-- 8. Domain distributions; review spelling, casing, unexpected values and nulls.
SELECT segment, COUNT_BIG(*) AS sales_rows, SUM(sales) AS revenue, SUM(profit) AS profit
FROM e_commerce.ecom_sales
GROUP BY segment
ORDER BY sales_rows DESC;

SELECT category, subcategory, COUNT_BIG(*) AS product_rows,
       COUNT(DISTINCT product_code) AS distinct_product_codes
FROM e_commerce.product
GROUP BY category, subcategory
ORDER BY category, subcategory;

SELECT market, region, COUNT_BIG(*) AS region_rows,
       COUNT(DISTINCT region_code) AS distinct_region_codes
FROM e_commerce.region
GROUP BY market, region
ORDER BY market, region;

SELECT gender, occupation, COUNT_BIG(*) AS customer_rows
FROM e_commerce.customer
GROUP BY gender, occupation
ORDER BY gender, occupation;

-- Plausibility checks for customer attributes; only aggregate values are returned.
SELECT
    COUNT_BIG(*) AS customer_rows,
    MIN(birth_date) AS min_birth_date,
    MAX(birth_date) AS max_birth_date,
    SUM(CASE WHEN birth_date > CONVERT(date, GETDATE()) THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS future_birth_dates,
    MIN(annual_income) AS min_annual_income,
    MAX(annual_income) AS max_annual_income,
    SUM(CASE WHEN annual_income < 0 THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS negative_annual_income_rows
FROM e_commerce.customer;

-- Coordinate range check: valid latitude is [-90, 90], longitude is [-180, 180].
SELECT
    COUNT_BIG(*) AS region_rows,
    SUM(CASE WHEN country_latitude IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS null_latitude_rows,
    SUM(CASE WHEN country_longitude IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS null_longitude_rows,
    SUM(CASE WHEN country_latitude < -90 OR country_latitude > 90 THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS out_of_range_latitude_rows,
    SUM(CASE WHEN country_longitude < -180 OR country_longitude > 180 THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS out_of_range_longitude_rows
FROM e_commerce.region;

-- 9. Referential-integrity coverage at the fact-row grain.
-- NOT EXISTS prevents duplicate dimension keys from inflating these counts.
SELECT
    'customer_id -> customer.customer_id' AS relationship,
    COUNT_BIG(*) AS sales_rows,
    SUM(CASE WHEN s.customer_id IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS null_fact_key_rows,
    SUM(CASE WHEN s.customer_id IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM e_commerce.customer AS c
                      WHERE c.customer_id = s.customer_id
                  )
             THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS orphan_fact_rows
FROM e_commerce.ecom_sales AS s
UNION ALL
SELECT
    'product_code -> product.product_code', COUNT_BIG(*),
    SUM(CASE WHEN s.product_code IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END),
    SUM(CASE WHEN s.product_code IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM e_commerce.product AS p
                      WHERE p.product_code = s.product_code
                  )
             THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END)
FROM e_commerce.ecom_sales AS s
UNION ALL
SELECT
    'region_code -> region.region_code', COUNT_BIG(*),
    SUM(CASE WHEN s.region_code IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END),
    SUM(CASE WHEN s.region_code IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM e_commerce.region AS r
                      WHERE r.region_code = s.region_code
                  )
             THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END)
FROM e_commerce.ecom_sales AS s;

-- 10. Order grain and line-loss vs order-loss distinction.
;WITH order_summary AS (
    SELECT
        order_id,
        COUNT_BIG(*) AS line_count,
        SUM(profit) AS order_profit
    FROM e_commerce.ecom_sales
    WHERE order_id IS NOT NULL
    GROUP BY order_id
)
SELECT
    COUNT_BIG(*) AS orders_with_id,
    SUM(CASE WHEN line_count = 1 THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS single_line_orders,
    SUM(CASE WHEN line_count > 1 THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS multi_line_orders,
    MAX(line_count) AS max_lines_per_order,
    SUM(CASE WHEN order_profit IS NULL THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS orders_with_no_non_null_profit,
    SUM(CASE WHEN order_profit < 0 THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS loss_making_orders
FROM order_summary;

-- Q7 assigns order-level loss to a transaction segment. Check whether an order
-- contains more than one non-null segment before using that assignment.
;WITH order_segments AS (
    SELECT order_id, COUNT(DISTINCT segment) AS segment_count
    FROM e_commerce.ecom_sales
    WHERE order_id IS NOT NULL
    GROUP BY order_id
)
SELECT
    COUNT_BIG(*) AS orders_with_id,
    SUM(CASE WHEN segment_count = 0 THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS orders_with_no_non_null_segment,
    SUM(CASE WHEN segment_count > 1 THEN CONVERT(bigint, 1) ELSE CONVERT(bigint, 0) END) AS orders_with_multiple_segments
FROM order_segments;

-- 11. Check whether date history has missing calendar months (zero rows are surfaced).
;WITH monthly_sales AS (
    SELECT
        DATEFROMPARTS(YEAR(order_date), MONTH(order_date), 1) AS order_month,
        COUNT_BIG(*) AS sales_rows,
        SUM(sales) AS revenue
    FROM e_commerce.ecom_sales
    WHERE order_date IS NOT NULL
    GROUP BY DATEFROMPARTS(YEAR(order_date), MONTH(order_date), 1)
), month_bounds AS (
    SELECT MIN(order_month) AS first_month, MAX(order_month) AS last_month
    FROM monthly_sales
), month_calendar AS (
    SELECT first_month AS order_month
    FROM month_bounds
    WHERE first_month IS NOT NULL
    UNION ALL
    SELECT DATEADD(month, 1, order_month)
    FROM month_calendar
    CROSS JOIN month_bounds
    WHERE order_month < last_month
)
SELECT
    c.order_month,
    COALESCE(m.sales_rows, 0) AS sales_rows,
    m.revenue
FROM month_calendar AS c
LEFT JOIN monthly_sales AS m ON m.order_month = c.order_month
ORDER BY c.order_month
OPTION (MAXRECURSION 0);
