from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from orchestration.scripts import prepare_runtime


class PrepareRuntimeTests(unittest.TestCase):
    def test_copy_allowlist_skips_dbt_user_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source"
            destination = root / "destination"
            (source / "models").mkdir(parents=True)
            (source / ".user.yml").write_text("id: local-only\n", encoding="utf-8")
            (source / "profiles.yml").write_text("profile: local-only\n", encoding="utf-8")
            (source / "models" / "schema.yml").write_text("version: 2\n", encoding="utf-8")
            (source / "models" / "model.sql").write_text("select 1\n", encoding="utf-8")

            copied_count = prepare_runtime._copy_allowlisted_tree(
                source,
                destination,
                frozenset({".sql", ".yml"}),
            )

            self.assertEqual(copied_count, 2)
            self.assertTrue((destination / "models" / "schema.yml").is_file())
            self.assertTrue((destination / "models" / "model.sql").is_file())
            self.assertFalse((destination / ".user.yml").exists())
            self.assertFalse((destination / "profiles.yml").exists())

    def test_validation_rejects_local_dbt_user_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            staging_root = Path(temporary_directory)
            required_files = (
                "ingestion/run_pipeline.py",
                "ingestion/check_source_connection.py",
                "text2sql/evaluation/run_baselines.py",
                "text2sql/evaluation/golden_set_v1.yml",
                "ecom_analytics/dbt_project.yml",
                "ecom_analytics/profiles.yml",
            )
            for relative_path in required_files:
                path = staging_root / relative_path
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture\n", encoding="utf-8")
            local_metadata = staging_root / "ecom_analytics" / ".user.yml"
            local_metadata.write_text("id: local-only\n", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, r"ecom_analytics/\.user\.yml"):
                prepare_runtime._validate_staging(staging_root)


if __name__ == "__main__":
    unittest.main()
