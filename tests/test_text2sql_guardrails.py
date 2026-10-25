"""Unit tests for the Text-to-SQL catalog loader and SQL validation boundary."""

from __future__ import annotations

import unittest

from text2sql.catalog import load_config
from text2sql.validator import SQLValidationError, validate_sql


class CatalogLoaderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config()

    def test_loads_all_catalog_relations_and_access_classes(self) -> None:
        self.assertEqual(len(self.config.catalog.models_by_relation), 12)
        self.assertEqual(len(self.config.policy.allowed_relations), 10)
        self.assertEqual(len(self.config.policy.restricted_relations), 2)
        self.assertEqual(len(self.config.policy.templates), 3)

    def test_customer_level_relations_only_have_approved_templates(self) -> None:
        for relation, restriction in self.config.policy.restricted_relations.items():
            self.assertTrue(restriction.permitted_template_ids)
            for template_id in restriction.permitted_template_ids:
                self.assertEqual(self.config.policy.templates[template_id].relation, relation)


class SQLValidatorAllowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config()

    def test_allows_a_catalogued_gold_select(self) -> None:
        result = validate_sql(
            "SELECT segment, total_sales "
            "FROM analytics_gold.mart_sales_by_segment",
            self.config,
        )
        self.assertEqual(result.relation, "analytics_gold.mart_sales_by_segment")
        self.assertEqual(result.output_columns, ("segment", "total_sales"))
        self.assertEqual(result.max_result_rows, 500)
        self.assertIn("SELECT", result.sql)

    def test_allows_aggregates_and_count_star(self) -> None:
        result = validate_sql(
            "SELECT segment, COUNT(*) AS order_groups, "
            "SUM(total_sales) AS sales FROM analytics_gold.mart_sales_by_segment "
            "GROUP BY segment ORDER BY sales DESC LIMIT 10",
            self.config,
        )
        self.assertEqual(result.output_columns, ("segment", "order_groups", "sales"))

    def test_restricted_templates_validate_and_return_template_id(self) -> None:
        cases = (
            "q08_vip_risk_summary",
            "q13_region_behavior_summary",
            "q14_rfm_population_summary",
        )
        for template_id in cases:
            with self.subTest(template_id=template_id):
                template = self.config.policy.templates[template_id]
                result = validate_sql(
                    template.sql,
                    self.config,
                    template_id=template_id,
                )
                self.assertEqual(result.template_id, template_id)
                self.assertEqual(result.relation, template.relation)

    def test_restricted_template_accepts_formatting_changes(self) -> None:
        template = self.config.policy.templates["q08_vip_risk_summary"]
        reformatted = "\n".join(line.strip() for line in template.sql.splitlines())
        result = validate_sql(
            reformatted,
            self.config,
            template_id="q08_vip_risk_summary",
        )
        self.assertEqual(result.template_id, "q08_vip_risk_summary")

    def test_demographic_query_requires_minimum_group_size(self) -> None:
        result = validate_sql(
            "SELECT gender, occupation, customer_count "
            "FROM analytics_gold.mart_customer_profile_by_gender_occupation "
            "WHERE customer_count >= 10 ORDER BY customer_count DESC",
            self.config,
        )
        self.assertEqual(
            result.relation,
            "analytics_gold.mart_customer_profile_by_gender_occupation",
        )


class SQLValidatorDenyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_config()

    def assert_rejected(self, sql: str, **kwargs: object) -> None:
        with self.assertRaises(SQLValidationError):
            validate_sql(sql, self.config, **kwargs)

    def test_rejects_unallowlisted_or_non_gold_relations(self) -> None:
        cases = (
            "SELECT customer_id FROM analytics_gold.mart_customer_rfm",
            "SELECT customer_id FROM bronze.customer",
            "SELECT segment FROM analytics_silver.stg_ecom_sales",
            "SELECT segment FROM analytics_gold.not_a_mart",
            "SELECT segment FROM other_schema.mart_sales_by_segment",
            "SELECT segment FROM catalog.analytics_gold.mart_sales_by_segment",
        )
        for sql in cases:
            with self.subTest(sql=sql):
                self.assert_rejected(sql)

    def test_rejects_unknown_columns_and_functions(self) -> None:
        self.assert_rejected(
            "SELECT customer_email FROM analytics_gold.mart_sales_by_segment"
        )
        self.assert_rejected(
            "SELECT read_csv('private.csv') "
            "FROM analytics_gold.mart_sales_by_segment"
        )

    def test_rejects_select_star_but_allows_count_star(self) -> None:
        self.assert_rejected("SELECT * FROM analytics_gold.mart_sales_by_segment")
        self.assert_rejected(
            "SELECT mart_sales_by_segment.* "
            "FROM analytics_gold.mart_sales_by_segment"
        )
        result = validate_sql(
            "SELECT COUNT(*) AS row_count "
            "FROM analytics_gold.mart_sales_by_segment",
            self.config,
        )
        self.assertEqual(result.output_columns, ("row_count",))

    def test_rejects_joins_ctes_subqueries_and_table_functions(self) -> None:
        cases = (
            "SELECT a.segment FROM analytics_gold.mart_sales_by_segment a "
            "JOIN analytics_gold.mart_monthly_sales b ON 1 = 1",
            "WITH sales AS (SELECT segment FROM analytics_gold.mart_sales_by_segment) "
            "SELECT segment FROM sales",
            "SELECT segment FROM analytics_gold.mart_sales_by_segment "
            "WHERE segment IN (SELECT segment FROM analytics_gold.mart_sales_by_segment)",
            "SELECT * FROM read_csv_auto('private.csv')",
        )
        for sql in cases:
            with self.subTest(sql=sql):
                self.assert_rejected(sql)

    def test_rejects_non_select_multiple_statements_and_parse_errors(self) -> None:
        cases = (
            "DELETE FROM analytics_gold.mart_sales_by_segment",
            "SELECT segment FROM analytics_gold.mart_sales_by_segment; "
            "DROP TABLE analytics_gold.mart_sales_by_segment",
            "SELECT FROM analytics_gold.mart_sales_by_segment",
            "",
        )
        for sql in cases:
            with self.subTest(sql=sql):
                self.assert_rejected(sql)

    def test_restricted_relations_require_exact_approved_template(self) -> None:
        self.assert_rejected(
            "SELECT COUNT(*) FROM analytics_gold.mart_customer_region_behavior"
        )
        self.assert_rejected(
            "SELECT customer_id FROM analytics_gold.mart_customer_rfm",
            template_id="q08_vip_risk_summary",
        )
        self.assert_rejected(
            self.config.policy.templates["q08_vip_risk_summary"].sql,
            template_id="q13_region_behavior_summary",
        )

    def test_rejects_unknown_roles_and_templates_on_direct_relations(self) -> None:
        self.assert_rejected(
            "SELECT segment FROM analytics_gold.mart_sales_by_segment",
            role="admin_from_prompt",
        )
        self.assert_rejected(
            "SELECT segment FROM analytics_gold.mart_sales_by_segment",
            template_id="q08_vip_risk_summary",
        )

    def test_rejects_limit_above_hard_cap(self) -> None:
        self.assert_rejected(
            "SELECT segment FROM analytics_gold.mart_sales_by_segment LIMIT 501"
        )

    def test_demographic_guard_rejects_small_or_bypassed_groups(self) -> None:
        base = "FROM analytics_gold.mart_customer_profile_by_gender_occupation"
        cases = (
            f"SELECT gender, occupation, customer_count {base}",
            f"SELECT gender, occupation, customer_count {base} WHERE customer_count >= 9",
            f"SELECT gender, occupation, customer_count {base} "
            "WHERE customer_count >= 10 OR gender = 'F'",
            f"SELECT gender, SUM(customer_count) AS customer_count {base} "
            "WHERE customer_count >= 10 GROUP BY gender",
        )
        for sql in cases:
            with self.subTest(sql=sql):
                self.assert_rejected(sql)


if __name__ == "__main__":
    unittest.main()
