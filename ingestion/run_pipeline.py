"""Load the four e-commerce source tables into the local DuckDB Bronze dataset."""

from __future__ import annotations

import duckdb
import dlt
from sqlalchemy import text

from dlt.sources.sql_database import sql_database
from dlt.pipeline.progress import log as log_progress

from ingestion.config import Settings
from ingestion.profile_source_tables import EXPECTED_TABLES, quote_identifier
from ingestion.sqlserver import create_source_engine


def source_row_counts(engine, settings: Settings) -> dict[str, int]:
    """Capture source counts so the local load can be checked after ingestion."""
    counts: dict[str, int] = {}
    with engine.connect() as connection:
        for table in EXPECTED_TABLES:
            qualified_table = (
                f"{quote_identifier(settings.sqlserver_schema)}."
                f"{quote_identifier(table)}"
            )
            counts[table] = connection.execute(
                text(f"SELECT COUNT_BIG(*) FROM {qualified_table};")
            ).scalar_one()
    return counts


def warehouse_row_counts(database_path, dataset_name: str) -> dict[str, int]:
    """Read target counts from DuckDB without modifying the warehouse."""
    counts: dict[str, int] = {}
    with duckdb.connect(str(database_path), read_only=True) as connection:
        for table in EXPECTED_TABLES:
            counts[table] = connection.execute(
                f'SELECT COUNT(*) FROM "{dataset_name}"."{table}";'
            ).fetchone()[0]
    return counts


def main() -> None:
    settings = Settings.from_env()
    settings.duckdb_path.parent.mkdir(parents=True, exist_ok=True)

    source_engine = create_source_engine(settings)
    dataset_name = "bronze"

    try:
        expected_counts = source_row_counts(source_engine, settings)
        source = sql_database(
            credentials=source_engine,
            schema=settings.sqlserver_schema,
            table_names=list(EXPECTED_TABLES),
            chunk_size=10_000,
            reflection_level="full",
        )

        pipeline = dlt.pipeline(
            pipeline_name="ecommerce_sqlserver",
            destination=dlt.destinations.duckdb(str(settings.duckdb_path)),
            dataset_name=dataset_name,
            progress=log_progress(dump_system_stats=False),
        )
        load_info = pipeline.run(source, write_disposition="replace")
        print(load_info)

        actual_counts = warehouse_row_counts(settings.duckdb_path, dataset_name)
        mismatches = {
            table: {"source": expected_counts[table], "duckdb": actual_counts[table]}
            for table in EXPECTED_TABLES
            if expected_counts[table] != actual_counts[table]
        }
        if mismatches:
            raise RuntimeError(f"Source and DuckDB row counts differ: {mismatches}")

        print(f"DuckDB warehouse: {settings.duckdb_path}")
        print(f"Dataset: {dataset_name}")
        for table in EXPECTED_TABLES:
            print(f"{table}: {actual_counts[table]:,} rows (source count matched)")
    finally:
        source_engine.dispose()


if __name__ == "__main__":
    main()
