"""Shared SQL Server connection settings for source-side commands."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, URL

from ingestion.config import Settings


def create_source_engine(settings: Settings) -> Engine:
    """Create a read-only-intent, encrypted SQLAlchemy engine for SQL Server."""
    url = URL.create(
        drivername="mssql+pymssql",
        username=settings.sqlserver_username,
        password=settings.sqlserver_password,
        host=settings.sqlserver_host,
        port=settings.sqlserver_port,
        database=settings.sqlserver_database,
        query={"charset": "UTF-8"},
    )
    return create_engine(
        url,
        connect_args={
            "login_timeout": 15,
            "timeout": 60,
            "encryption": "require",
            "read_only": True,
            "appname": "ecom-analytics-text2sql",
        },
        pool_pre_ping=True,
    )


def redact_source_secrets(message: str, settings: Settings) -> str:
    """Remove configured credentials from driver error messages."""
    for secret in (settings.sqlserver_password, settings.sqlserver_username):
        if secret:
            message = message.replace(secret, "[REDACTED]")
    return message
