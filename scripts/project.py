"""Stable project commands that work independently of the caller's cwd."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path
from typing import Sequence


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DBT_PROJECT_DIR = REPOSITORY_ROOT / "ecom_analytics"
DBT_PROFILE_TEMPLATE = DBT_PROJECT_DIR / "profiles.yml.example"

# A script launched by absolute path starts with scripts/ on sys.path. Add the
# repository root so the same entry point works from any current directory.
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from ingestion.config import resolve_warehouse_path


class ProjectCommandError(RuntimeError):
    """A safe, user-actionable project command error."""


def _find_dbt_executable() -> str | None:
    # POSIX virtualenv Python executables often symlink to the base interpreter.
    # sysconfig keeps the active environment's scripts directory in that case.
    candidate = Path(sysconfig.get_path("scripts")) / (
        "dbt.exe" if os.name == "nt" else "dbt"
    )
    return str(candidate) if candidate.is_file() else None


def _require_warehouse(purpose: str) -> Path:
    path = resolve_warehouse_path()
    if not path.is_file():
        raise ProjectCommandError(
            f"DuckDB warehouse is missing for {purpose}: {path}. "
            "Run source ingestion first. This command will not create an empty warehouse."
        )
    return path


def _dbt_arguments_are_safe(arguments: Sequence[str]) -> None:
    protected_options = ("--project-dir", "--profiles-dir")
    for argument in arguments:
        if any(
            argument == option or argument.startswith(f"{option}=")
            for option in protected_options
        ):
            raise ProjectCommandError(
                "The wrapper owns --project-dir and --profiles-dir so dbt uses "
                "the repository project and its temporary profile."
            )


def _run_dbt(command: str, arguments: Sequence[str]) -> int:
    executable = _find_dbt_executable()
    if executable is None:
        raise ProjectCommandError(
            "Could not find dbt in the active Python environment. Run `uv sync` first."
        )
    if not DBT_PROFILE_TEMPLATE.is_file():
        raise ProjectCommandError(
            f"Safe dbt profile template is missing: {DBT_PROFILE_TEMPLATE}"
        )

    _dbt_arguments_are_safe(arguments)
    warehouse_path = resolve_warehouse_path()
    if command in {"build", "test", "show"} and not warehouse_path.is_file():
        raise ProjectCommandError(
            f"DuckDB warehouse is missing for `dbt {command}`: {warehouse_path}. "
            "Run source ingestion first. This command will not create an empty warehouse."
        )

    environment = os.environ.copy()
    environment["DUCKDB_PATH"] = str(warehouse_path)

    # The project-level template has no credentials. A temporary copy avoids
    # depending on or overwriting any ignored Windows profiles.yml.
    with tempfile.TemporaryDirectory(prefix="xom-ecom-dbt-profile-") as profile_directory:
        temporary_profile = Path(profile_directory) / "profiles.yml"
        shutil.copyfile(DBT_PROFILE_TEMPLATE, temporary_profile)
        process_arguments = [
            executable,
            command,
            "--project-dir",
            str(DBT_PROJECT_DIR),
            "--profiles-dir",
            profile_directory,
            *arguments,
        ]
        completed = subprocess.run(
            process_arguments,
            cwd=REPOSITORY_ROOT,
            env=environment,
            check=False,
        )
    return completed.returncode


def _run_python_module(module: str, arguments: Sequence[str] = (), *, require_data: bool) -> int:
    environment = os.environ.copy()
    environment["DUCKDB_PATH"] = str(resolve_warehouse_path())
    if require_data:
        _require_warehouse(module)
    completed = subprocess.run(
        [sys.executable, "-m", module, *arguments],
        cwd=REPOSITORY_ROOT,
        env=environment,
        check=False,
    )
    return completed.returncode


def _run_script(script: Path, arguments: Sequence[str] = ()) -> int:
    if not script.is_file():
        raise ProjectCommandError(f"Project script is missing: {script}")
    completed = subprocess.run(
        [sys.executable, str(script), *arguments],
        cwd=REPOSITORY_ROOT,
        env=os.environ.copy(),
        check=False,
    )
    return completed.returncode


def _doctor() -> int:
    warehouse_path = resolve_warehouse_path()
    dbt_executable = _find_dbt_executable()
    checks = (
        ("Repository root", REPOSITORY_ROOT.is_dir(), str(REPOSITORY_ROOT)),
        ("Python runtime", (3, 11) <= sys.version_info[:2] < (3, 12), sys.version.split()[0]),
        ("dbt executable", dbt_executable is not None, dbt_executable or "not found; run `uv sync`"),
        ("dbt profile template", DBT_PROFILE_TEMPLATE.is_file(), str(DBT_PROFILE_TEMPLATE)),
        (
            "DuckDB warehouse",
            warehouse_path.is_file(),
            str(warehouse_path) if warehouse_path.is_file() else f"missing (run ingestion): {warehouse_path}",
        ),
    )
    for name, passed, detail in checks:
        print(f"{'OK' if passed else 'MISSING'} {name}: {detail}")
    print("No credentials were printed and no warehouse file was created.")
    return 0 if all(passed for _, passed, _ in checks) else 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run E-Commerce analytics commands from any working directory."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Check paths and local prerequisites without creating files.")

    dbt = commands.add_parser("dbt", help="Run a supported dbt command with an absolute DuckDB path.")
    dbt.add_argument("dbt_command", choices=("parse", "build", "test", "show"))
    # Keep dbt's own options out of argparse so selectors such as --select
    # and flags added by later dbt versions pass through unchanged.
    dbt.add_argument("dbt_args", nargs=argparse.REMAINDER)

    commands.add_parser("offline-checks", help="Run deterministic checks without Gemini or a warehouse.")
    commands.add_parser("baselines", help="Run the 15 SQL/template checks against DuckDB.")
    commands.add_parser("charts", help="Generate the ten static Gold-mart charts.")
    ui = commands.add_parser("ui", help="Start the local Text-to-SQL browser interface.")
    ui.add_argument("arguments", nargs=argparse.REMAINDER)

    astro = commands.add_parser("astro", help="Run local Astro project preparation.")
    astro_commands = astro.add_subparsers(dest="astro_command", required=True)
    astro_commands.add_parser("prepare", help="Refresh the generated Astro runtime source stage.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.command == "doctor":
            return _doctor()
        if args.command == "dbt":
            dbt_arguments = list(args.dbt_args)
            if dbt_arguments[:1] == ["--"]:
                dbt_arguments = dbt_arguments[1:]
            return _run_dbt(args.dbt_command, dbt_arguments)
        if args.command == "offline-checks":
            return _run_python_module(
                "text2sql.evaluation.run_offline_checks",
                require_data=False,
            )
        if args.command == "baselines":
            return _run_python_module(
                "text2sql.evaluation.run_baselines",
                require_data=True,
            )
        if args.command == "charts":
            _require_warehouse("chart generation")
            return _run_script(REPOSITORY_ROOT / "analytics" / "visualization" / "generate_charts.py")
        if args.command == "ui":
            _require_warehouse("the Text-to-SQL UI")
            return _run_python_module("text2sql.web_app", args.arguments, require_data=False)
        if args.command == "astro" and args.astro_command == "prepare":
            return _run_script(REPOSITORY_ROOT / "orchestration" / "scripts" / "prepare_runtime.py")
    except ProjectCommandError as exc:
        print(f"Project command failed: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"Project command failed ({type(exc).__name__}).", file=sys.stderr)
        return 2

    print("Project command is not implemented.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
