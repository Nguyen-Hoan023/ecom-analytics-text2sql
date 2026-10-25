"""Read-only DuckDB execution for SQL that passed the Text-to-SQL validator."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import duckdb

from ingestion.config import resolve_warehouse_path
from text2sql.catalog import CatalogConfig, CatalogConfigError, load_config
from text2sql.validator import SQLValidationError, ValidatedQuery, validate_sql


class ExecutorError(RuntimeError):
    """Base class for safe executor failures."""


class InvalidValidatedQueryError(ExecutorError):
    """Raised when a caller supplies an invalid or altered ValidatedQuery."""


class QueryTimeoutError(ExecutorError):
    """Raised when DuckDB execution exceeds the configured time limit."""


class QueryExecutionError(ExecutorError):
    """Raised when DuckDB cannot execute a validated query."""


@dataclass(frozen=True)
class QueryResult:
    """Bounded tabular output and execution metadata safe for application use."""

    columns: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...]
    row_count: int
    row_limit: int
    truncated: bool
    duration_ms: int
    relation: str
    model_name: str
    role: str


@dataclass(frozen=True)
class _ExecutionLimits:
    timeout_seconds: int
    max_threads: int
    memory_limit: str
    max_temp_directory_size: str
    hard_row_cap: int

    @classmethod
    def from_policy(cls, policy: Mapping[str, Any]) -> "_ExecutionLimits":
        required_true = (
            "open_database_read_only",
            "disable_external_access",
            "disable_extension_autoload",
            "disable_extension_autoinstall",
            "disable_community_extensions",
            "lock_security_configuration_after_setup",
        )
        for key in required_true:
            if policy.get(key) is not True:
                raise CatalogConfigError(
                    f"duckdb_execution.{key} must be true for the v1 executor."
                )

        def positive_int(key: str) -> int:
            value = policy.get(key)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise CatalogConfigError(f"duckdb_execution.{key} must be a positive integer.")
            return value

        def non_empty_string(key: str) -> str:
            value = policy.get(key)
            if not isinstance(value, str) or not value.strip():
                raise CatalogConfigError(f"duckdb_execution.{key} must be a non-empty string.")
            return value.strip()

        return cls(
            timeout_seconds=positive_int("max_query_runtime_seconds"),
            max_threads=positive_int("max_threads"),
            memory_limit=non_empty_string("memory_limit"),
            max_temp_directory_size=non_empty_string("max_temp_directory_size"),
            hard_row_cap=positive_int("output_rows_hard_cap"),
        )


def _resolve_database_path(database_path: str | Path | None) -> Path:
    return resolve_warehouse_path(database_path)


class DuckDBExecutor:
    """Execute only revalidated ``ValidatedQuery`` objects against a read-only DB.

    A new DuckDB connection is opened for each call. The path is trusted
    application configuration; it is never derived from generated SQL or a
    natural-language question.
    """

    def __init__(
        self,
        database_path: str | Path | None = None,
        config: CatalogConfig | None = None,
    ) -> None:
        self._config = config or load_config()
        self._limits = _ExecutionLimits.from_policy(self._config.policy.duckdb_execution)
        self._database_path = _resolve_database_path(database_path)
        if not self._database_path.is_file():
            raise ExecutorError("The configured DuckDB warehouse file does not exist.")

    def execute(self, query: ValidatedQuery) -> QueryResult:
        """Revalidate and execute a query, returning at most its permitted rows."""
        validated = self._revalidate(query)
        row_limit = min(
            validated.requested_limit
            if validated.requested_limit is not None
            else validated.default_result_rows,
            validated.max_result_rows,
            self._limits.hard_row_cap,
        )

        connection = self._open_read_only_connection()
        timed_out = threading.Event()

        def interrupt_query() -> None:
            timed_out.set()
            try:
                connection.interrupt()
            except Exception:
                # The query may have finished as the timer fired.
                pass

        timer = threading.Timer(self._limits.timeout_seconds, interrupt_query)
        timer.daemon = True
        started_at = time.monotonic()
        timer.start()
        try:
            cursor = connection.execute(validated.sql)
            description = cursor.description or ()
            columns = tuple(str(column[0]) for column in description)
            if tuple(column.casefold() for column in columns) != validated.output_columns:
                raise QueryExecutionError("DuckDB returned columns different from the validated query.")

            fetched_rows = cursor.fetchmany(row_limit + 1)
            if timed_out.is_set():
                raise QueryTimeoutError(
                    f"Query exceeded the {self._limits.timeout_seconds}-second execution limit."
                )
            truncated = len(fetched_rows) > row_limit
            rows = tuple(tuple(row) for row in fetched_rows[:row_limit])
            duration_ms = max(0, int((time.monotonic() - started_at) * 1000))
            return QueryResult(
                columns=columns,
                rows=rows,
                row_count=len(rows),
                row_limit=row_limit,
                truncated=truncated,
                duration_ms=duration_ms,
                relation=validated.relation,
                model_name=validated.model_name,
                role=validated.role,
            )
        except QueryExecutionError:
            raise
        except Exception as exc:
            if timed_out.is_set():
                raise QueryTimeoutError(
                    f"Query exceeded the {self._limits.timeout_seconds}-second execution limit."
                ) from None
            raise QueryExecutionError(
                f"DuckDB could not execute the validated query ({type(exc).__name__})."
            ) from None
        finally:
            timer.cancel()
            connection.close()

    def _revalidate(self, query: ValidatedQuery) -> ValidatedQuery:
        if type(query) is not ValidatedQuery:
            raise InvalidValidatedQueryError("Executor accepts only a ValidatedQuery object.")
        if not isinstance(query.role, str) or (
            query.template_id is not None and not isinstance(query.template_id, str)
        ):
            raise InvalidValidatedQueryError("ValidatedQuery contains invalid authorization metadata.")
        try:
            current = validate_sql(
                query.sql,
                self._config,
                role=query.role,
                template_id=query.template_id,
            )
        except SQLValidationError:
            raise InvalidValidatedQueryError(
                "ValidatedQuery no longer satisfies the current SQL access policy."
            ) from None

        metadata = (
            "sql",
            "relation",
            "model_name",
            "output_columns",
            "max_result_rows",
            "default_result_rows",
            "role",
            "template_id",
            "requested_limit",
        )
        if any(getattr(query, name) != getattr(current, name) for name in metadata):
            raise InvalidValidatedQueryError(
                "ValidatedQuery metadata does not match the current SQL access policy."
            )
        if current.max_result_rows > self._limits.hard_row_cap:
            raise InvalidValidatedQueryError("ValidatedQuery exceeds the executor hard row cap.")
        return current

    def _open_read_only_connection(self) -> duckdb.DuckDBPyConnection:
        settings = {
            "enable_external_access": False,
            "autoload_known_extensions": False,
            "autoinstall_known_extensions": False,
            "allow_community_extensions": False,
            "threads": self._limits.max_threads,
            "memory_limit": self._limits.memory_limit,
            "max_temp_directory_size": self._limits.max_temp_directory_size,
        }
        connection: duckdb.DuckDBPyConnection | None = None
        try:
            connection = duckdb.connect(
                database=str(self._database_path),
                read_only=True,
                config=settings,
            )
            # Lock configuration only after all security/resource settings have
            # been passed to connect, so a query cannot relax them afterwards.
            connection.execute("SET lock_configuration = true")
            return connection
        except Exception:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass
            raise ExecutorError("Could not open the DuckDB warehouse with the required protections.") from None
