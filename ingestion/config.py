"""Read and validate local pipeline configuration without printing secrets."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"
DEFAULT_DUCKDB_PATH = Path("duckdb_warehouse/warehouse.duckdb")


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
            "XOM_SQLSERVER_HOST": os.getenv("XOM_SQLSERVER_HOST", "").strip(),
            "XOM_SQLSERVER_DATABASE": os.getenv("XOM_SQLSERVER_DATABASE", "").strip(),
            "XOM_SQLSERVER_USERNAME": os.getenv("XOM_SQLSERVER_USERNAME", "").strip(),
            "XOM_SQLSERVER_PASSWORD": os.getenv("XOM_SQLSERVER_PASSWORD", ""),
        }
        missing = [name for name, value in required.items() if not value.strip()]
        if missing:
            missing_names = ", ".join(missing)
            raise ValueError(
                f"Missing required settings: {missing_names}. "
                "Copy .env.example to .env and fill the local values."
            )

        port_value = os.getenv("XOM_SQLSERVER_PORT", "1433").strip()
        try:
            port = int(port_value)
        except ValueError as exc:
            raise ValueError("XOM_SQLSERVER_PORT must be an integer.") from exc
        if not 1 <= port <= 65535:
            raise ValueError("XOM_SQLSERVER_PORT must be between 1 and 65535.")

        schema = os.getenv("XOM_SQLSERVER_SCHEMA", "e_commerce").strip()
        if not schema:
            raise ValueError("XOM_SQLSERVER_SCHEMA must not be empty.")

        warehouse_path = Path(
            os.getenv("DUCKDB_PATH", str(DEFAULT_DUCKDB_PATH))
        ).expanduser()
        if not warehouse_path.is_absolute():
            warehouse_path = PROJECT_ROOT / warehouse_path

        return cls(
            sqlserver_host=required["XOM_SQLSERVER_HOST"],
            sqlserver_database=required["XOM_SQLSERVER_DATABASE"],
            sqlserver_username=required["XOM_SQLSERVER_USERNAME"],
            sqlserver_password=required["XOM_SQLSERVER_PASSWORD"],
            sqlserver_port=port,
            sqlserver_schema=schema,
            duckdb_path=warehouse_path.resolve(),
        )
