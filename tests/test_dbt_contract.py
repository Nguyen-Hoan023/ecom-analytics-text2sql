"""Unit tests for the warehouse-free dbt/semantic-catalog contract."""

from __future__ import annotations

import unittest

from text2sql.catalog import load_catalog
from text2sql.dbt_contract import validate_dbt_manifest


class DbtCatalogContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog()

    def make_manifest(self, *, omit: str | None = None, extra: bool = False):
        nodes = {}
        for relation, model in self.catalog.models_by_relation.items():
            if model.name == omit:
                continue
            nodes[f"model.ecom_analytics.{model.name}"] = {
                "resource_type": "model",
                "name": model.name,
                "alias": model.name,
                "schema": self.catalog.gold_schema,
                "config": {"materialized": "table"},
            }
        if extra:
            nodes["model.ecom_analytics.mart_not_registered"] = {
                "resource_type": "model",
                "name": "mart_not_registered",
                "alias": "mart_not_registered",
                "schema": self.catalog.gold_schema,
                "config": {"materialized": "table"},
            }
        return {"nodes": nodes}

    def test_catalog_relations_match_gold_models(self):
        self.assertEqual(validate_dbt_manifest(self.make_manifest(), self.catalog), ())

    def test_missing_gold_model_fails_contract(self):
        failures = validate_dbt_manifest(
            self.make_manifest(omit="mart_sales_by_segment"), self.catalog
        )
        self.assertTrue(any("mart_sales_by_segment" in failure for failure in failures))

    def test_unregistered_gold_model_fails_contract(self):
        failures = validate_dbt_manifest(self.make_manifest(extra=True), self.catalog)
        self.assertTrue(any("mart_not_registered" in failure for failure in failures))

    def test_ephemeral_gold_model_fails_contract(self):
        manifest = self.make_manifest()
        manifest["nodes"]["model.ecom_analytics.mart_sales_by_segment"]["config"][
            "materialized"
        ] = "ephemeral"
        failures = validate_dbt_manifest(manifest, self.catalog)
        self.assertTrue(any("must be a queryable dbt model" in failure for failure in failures))

    def test_invalid_manifest_shape_fails_contract(self):
        self.assertEqual(
            validate_dbt_manifest({"nodes": []}, self.catalog),
            ("manifest.nodes must be a mapping",),
        )


if __name__ == "__main__":
    unittest.main()
