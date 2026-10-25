from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ingestion.config import ENV_FILE, PROJECT_ROOT, resolve_warehouse_path


class WarehousePathResolutionTests(unittest.TestCase):
    def test_relative_environment_path_is_anchored_at_repo_root_not_cwd(self) -> None:
        original_directory = Path.cwd()
        with tempfile.TemporaryDirectory() as temporary_directory:
            with (
                patch.dict(os.environ, {"DUCKDB_PATH": "local-data/test.duckdb"}, clear=False),
                patch("ingestion.config.dotenv_values") as dotenv_values,
            ):
                os.chdir(temporary_directory)
                try:
                    resolved = resolve_warehouse_path()
                finally:
                    os.chdir(original_directory)

        self.assertEqual(resolved, (PROJECT_ROOT / "local-data" / "test.duckdb").resolve())
        dotenv_values.assert_not_called()

    def test_absolute_environment_path_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            absolute_path = Path(temporary_directory) / "warehouse.duckdb"
            with patch.dict(os.environ, {"DUCKDB_PATH": str(absolute_path)}, clear=False):
                self.assertEqual(resolve_warehouse_path(), absolute_path.resolve())

    def test_dotenv_is_fallback_and_does_not_require_sql_credentials(self) -> None:
        with (
            patch.dict(os.environ, {"DUCKDB_PATH": ""}, clear=False),
            patch(
                "ingestion.config.dotenv_values",
                return_value={"DUCKDB_PATH": "from-env-file/warehouse.duckdb"},
            ) as dotenv_values,
        ):
            resolved = resolve_warehouse_path()

        self.assertEqual(
            resolved,
            (PROJECT_ROOT / "from-env-file" / "warehouse.duckdb").resolve(),
        )
        dotenv_values.assert_called_once_with(ENV_FILE)

    def test_explicit_path_overrides_environment_and_dotenv(self) -> None:
        with (
            patch.dict(os.environ, {"DUCKDB_PATH": "ignored.duckdb"}, clear=False),
            patch("ingestion.config.dotenv_values") as dotenv_values,
        ):
            resolved = resolve_warehouse_path("explicit/warehouse.duckdb")

        self.assertEqual(
            resolved,
            (PROJECT_ROOT / "explicit" / "warehouse.duckdb").resolve(),
        )
        dotenv_values.assert_not_called()


if __name__ == "__main__":
    unittest.main()
