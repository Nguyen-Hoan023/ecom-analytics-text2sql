# Read-only source profiling SQL

<code>source_profile.sql</code> is a manual SQL Server diagnostic script. It is separate from dbt and is not automatically executed by DLT or Airflow.

## Sections

The script checks metadata, row/null counts, candidate-key uniqueness, numeric/date ranges, foreign-key coverage, discount and segment distributions, geographic/category groups, and monthly aggregates. It avoids selecting customer names, email addresses, or raw customer samples.

## Run safely

Open the file in SSMS, DBeaver, or another SQL Server client connected to the database containing the configured source schema. Use a read-only account where available. Run sections separately if the client has batch limits.

Its schema and relation names form part of the source contract. Change them only when the source schema changes. A diagnostic anomaly is a signal to investigate, not permission to silently delete or rewrite data. Store only aggregate findings and confirmed metric definitions in project docs; never commit credentials or raw customer output.
