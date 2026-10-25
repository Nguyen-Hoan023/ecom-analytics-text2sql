from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ingestion.config import PROJECT_ROOT
from scripts import project


class ProjectCommandTests(unittest.TestCase):
    def test_dbt_discovery_uses_active_environment_scripts_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            scripts_directory = Path(temporary_directory) / "environment-scripts"
            scripts_directory.mkdir()
            dbt_executable = scripts_directory / ("dbt.exe" if os.name == "nt" else "dbt")
            dbt_executable.touch()
            # Simulate Python resolving outside the environment, as POSIX venv
            # symlinks do. dbt must still come from this environment's scripts.
            with (
                patch.object(project.sys, "executable", str(Path(temporary_directory) / "base" / "python")),
                patch.object(project.sysconfig, "get_path", return_value=str(scripts_directory)),
            ):
                self.assertEqual(project._find_dbt_executable(), str(dbt_executable))

    def test_dbt_discovery_does_not_fall_back_to_another_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with patch.object(project.sysconfig, "get_path", return_value=temporary_directory):
                self.assertIsNone(project._find_dbt_executable())

    def test_dbt_parse_uses_repo_paths_temp_profile_and_absolute_warehouse(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            warehouse_path = Path(temporary_directory) / "warehouse.duckdb"
            captured: dict[str, object] = {}

            def fake_run(arguments, *, cwd, env, check):
                captured["arguments"] = arguments
                captured["cwd"] = cwd
                captured["env"] = env
                captured["check"] = check
                profile_directory = Path(arguments[arguments.index("--profiles-dir") + 1])
                profile = profile_directory / "profiles.yml"
                self.assertTrue(profile.is_file())
                self.assertIn("ecom_analytics:", profile.read_text(encoding="utf-8"))
                return subprocess.CompletedProcess(arguments, 0)

            with (
                patch.dict(os.environ, {"DUCKDB_PATH": str(warehouse_path)}, clear=False),
                patch.object(project, "_find_dbt_executable", return_value="dbt"),
                patch.object(project.subprocess, "run", side_effect=fake_run),
            ):
                exit_code = project._run_dbt("parse", ())

        arguments = captured["arguments"]
        self.assertEqual(exit_code, 0)
        self.assertEqual(captured["cwd"], PROJECT_ROOT)
        self.assertEqual(captured["check"], False)
        self.assertEqual(captured["env"]["DUCKDB_PATH"], str(warehouse_path.resolve()))
        self.assertIn(str(PROJECT_ROOT / "ecom_analytics"), arguments)

    def test_dbt_build_does_not_create_a_missing_warehouse(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing_path = Path(temporary_directory) / "missing.duckdb"
            with (
                patch.dict(os.environ, {"DUCKDB_PATH": str(missing_path)}, clear=False),
                patch.object(project, "_find_dbt_executable", return_value="dbt"),
                patch.object(project.subprocess, "run") as run,
            ):
                with self.assertRaisesRegex(project.ProjectCommandError, "will not create"):
                    project._run_dbt("build", ())

            self.assertFalse(missing_path.exists())
            run.assert_not_called()

    def test_dbt_cannot_override_project_or_profile_paths(self) -> None:
        with self.assertRaises(project.ProjectCommandError):
            project._dbt_arguments_are_safe(("--profiles-dir", "somewhere-else"))

    def test_dbt_command_forwards_model_selection_arguments(self) -> None:
        with patch.object(project, "_run_dbt", return_value=0) as run_dbt:
            exit_code = project.main(
                ["dbt", "show", "--select", "mart_sales_by_segment"]
            )

        self.assertEqual(exit_code, 0)
        run_dbt.assert_called_once_with("show", ["--select", "mart_sales_by_segment"])

    def test_offline_checks_run_from_another_cwd_without_a_warehouse_or_gemini(self) -> None:
        script = PROJECT_ROOT / "scripts" / "project.py"
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing_path = Path(temporary_directory) / "not-created.duckdb"
            environment = os.environ.copy()
            environment["DUCKDB_PATH"] = str(missing_path)
            completed = subprocess.run(
                [sys.executable, str(script), "offline-checks"],
                cwd=temporary_directory,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertIn("Gemini calls=0", completed.stdout)
            self.assertFalse(missing_path.exists())


if __name__ == "__main__":
    unittest.main()
