"""Read and validate local pipeline configuration without printing secrets."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"
DEFAULT_DUCKDB_PATH = Path("duckdb_warehouse/warehouse.duckdb")


def resolve_warehouse_path(path_value: str | Path | None = None) -> Path:
    """Resolve DuckDB path consistently without requiring source credentials.

    Precedence is an explicit argument, process environment, the root ``.env``
    value, then the repository-relative default. Relative paths are anchored at
    the repository root, independent of the caller's current working directory.
    The function never creates the database or its parent directory.
    """
    if path_value is None:
        configured_path = os.environ.get("DUCKDB_PATH", "").strip()
        if not configured_path:
            configured_path = str(dotenv_values(ENV_FILE).get("DUCKDB_PATH") or "").strip()
        path_value = configured_path or DEFAULT_DUCKDB_PATH

    path = Path(path_value).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


@dataclass(frozen=True)
class Settings:
    """Runtime settings shared by ingestion and local analytics commands."""

    sqlserver_host: str
    sqlserver_database: str
    sqlserver_username: str = field(repr=False)
    sqlserver_password: str = field(repr=False)
    sqlserver_port: int = 1433
    sqlserver_schema: str = "e_commerce"
    duckdb_path: Path = PROJECT_ROOT / DEFAULT_DUCKDB_PATH

    @classmethod
    def from_env(cls, env_file: Path = ENV_FILE) -> "Settings":
        """Load settings from the repository .env and validate required fields."""
        load_dotenv(dotenv_path=env_file, override=False)

        required = {
            "SOURCE_SQLSERVER_HOST": os.getenv("SOURCE_SQLSERVER_HOST", "").strip(),
            "SOURCE_SQLSERVER_DATABASE": os.getenv("SOURCE_SQLSERVER_DATABASE", "").strip(),
            "SOURCE_SQLSERVER_USERNAME": os.getenv("SOURCE_SQLSERVER_USERNAME", "").strip(),
            "SOURCE_SQLSERVER_PASSWORD": os.getenv("SOURCE_SQLSERVER_PASSWORD", ""),
        }
        missing = [name for name, value in required.items() if not value.strip()]
        if missing:
            missing_names = ", ".join(missing)
            raise ValueError(
                f"Missing required settings: {missing_names}. "
                "Copy .env.example to .env and fill the local values."
            )

        port_value = os.getenv("SOURCE_SQLSERVER_PORT", "1433").strip()
        try:
            port = int(port_value)
        except ValueError as exc:
            raise ValueError("SOURCE_SQLSERVER_PORT must be an integer.") from exc
        if not 1 <= port <= 65535:
            raise ValueError("SOURCE_SQLSERVER_PORT must be between 1 and 65535.")

        schema = os.getenv("SOURCE_SQLSERVER_SCHEMA", "e_commerce").strip()
        if not schema:
            raise ValueError("SOURCE_SQLSERVER_SCHEMA must not be empty.")

        return cls(
            sqlserver_host=required["SOURCE_SQLSERVER_HOST"],
            sqlserver_database=required["SOURCE_SQLSERVER_DATABASE"],
            sqlserver_username=required["SOURCE_SQLSERVER_USERNAME"],
            sqlserver_password=required["SOURCE_SQLSERVER_PASSWORD"],
            sqlserver_port=port,
            sqlserver_schema=schema,
            duckdb_path=resolve_warehouse_path(),
        )
