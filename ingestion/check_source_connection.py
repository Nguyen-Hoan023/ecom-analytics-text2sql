"""Run a read-only SQL Server connection smoke check."""

from __future__ import annotations

from sqlalchemy import text

from ingestion.config import Settings
from ingestion.sqlserver import create_source_engine, redact_source_secrets


def main() -> None:
    settings = Settings.from_env()
    engine = create_source_engine(settings)

    try:
        with engine.connect() as connection:
            database_name, check_value = connection.execute(
                text("SELECT DB_NAME(), CAST(1 AS int);")
            ).one()

        if check_value != 1:
            raise RuntimeError("The read-only smoke query returned an unexpected result.")

        print(
            "SQL Server connection succeeded. "
            f"Selected database: {database_name!r}. "
            "Read-only smoke query returned 1."
        )
    except Exception as exc:
        message = redact_source_secrets(str(exc), settings)
        raise SystemExit(
            f"SQL Server connection check failed ({type(exc).__name__}): {message}"
        ) from None
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
