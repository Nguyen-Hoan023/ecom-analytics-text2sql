"""Run a read-only SQL Server connection smoke check."""

from __future__ import annotations

import pymssql

from ingestion.config import Settings


def _redact_secrets(message: str, *secrets: str) -> str:
    for secret in secrets:
        if secret:
            message = message.replace(secret, "[REDACTED]")
    return message


def main() -> None:
    settings = Settings.from_env()
    connection = None
    cursor = None

    try:
        connection = pymssql.connect(
            server=settings.sqlserver_host,
            port=str(settings.sqlserver_port),
            user=settings.sqlserver_username,
            password=settings.sqlserver_password,
            database=settings.sqlserver_database,
            login_timeout=15,
            timeout=15,
            encryption="require",
        )
        cursor = connection.cursor()
        cursor.execute("SELECT DB_NAME(), CAST(1 AS int);")
        database_name, check_value = cursor.fetchone()

        if check_value != 1:
            raise RuntimeError("The read-only smoke query returned an unexpected result.")

        print(
            "SQL Server connection succeeded. "
            f"Selected database: {database_name!r}. "
            "Read-only smoke query returned 1."
        )
    except Exception as exc:
        message = _redact_secrets(
            str(exc), settings.sqlserver_password, settings.sqlserver_username
        )
        raise SystemExit(
            f"SQL Server connection check failed ({type(exc).__name__}): {message}"
        ) from None
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    main()
