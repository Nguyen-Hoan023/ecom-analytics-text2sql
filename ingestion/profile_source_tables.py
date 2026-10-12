"""Check source-table access and row counts without extracting row data."""

from __future__ import annotations

from sqlalchemy import text

from ingestion.config import Settings
from ingestion.sqlserver import create_source_engine, redact_source_secrets

EXPECTED_TABLES = ("customer", "ecom_sales", "product", "region")


def quote_identifier(identifier: str) -> str:
    """Escape a SQL Server identifier for use in a query."""
    return f"[{identifier.replace(']', ']]')}]"


def main() -> None:
    settings = Settings.from_env()
    engine = create_source_engine(settings)

    try:
        with engine.connect() as connection:
            available_tables = set(
                connection.execute(
                    text(
                        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
                        "WHERE TABLE_SCHEMA = :schema "
                        "AND TABLE_TYPE = 'BASE TABLE';"
                    ),
                    {"schema": settings.sqlserver_schema},
                ).scalars()
            )
            missing_tables = [
                table for table in EXPECTED_TABLES if table not in available_tables
            ]
            if missing_tables:
                raise RuntimeError(
                    f"Expected source tables not found in schema "
                    f"{settings.sqlserver_schema!r}: {', '.join(missing_tables)}"
                )

            print(
                f"Source database: {settings.sqlserver_database}; "
                f"schema: {settings.sqlserver_schema}"
            )
            for table in EXPECTED_TABLES:
                qualified_table = (
                    f"{quote_identifier(settings.sqlserver_schema)}."
                    f"{quote_identifier(table)}"
                )
                row_count = connection.execute(
                    text(f"SELECT COUNT_BIG(*) FROM {qualified_table};")
                ).scalar_one()
                print(f"{table}: {row_count:,} rows (SELECT access confirmed)")
    except Exception as exc:
        message = redact_source_secrets(str(exc), settings)
        raise SystemExit(
            f"Source profile failed ({type(exc).__name__}): {message}"
        ) from None
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
