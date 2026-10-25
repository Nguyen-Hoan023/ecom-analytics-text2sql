# Analytics assets

This module contains analysis outputs that sit on top of the dbt Gold layer. It does not own ingestion, warehouse modeling, or query authorization.

## Contents

| Path | Responsibility |
|---|---|
| [`visualization/`](visualization/README.md) | Reproducible static charts generated from curated Gold marts. |

## Data flow

The chart generator opens the configured DuckDB warehouse read-only, queries the Gold marts, reconciles key totals, and writes PNG files to `docs/assets/charts/`. These checked-in images are presentation snapshots; regenerate them after a warehouse refresh when the underlying snapshot or models change.

For question-driven charts in the Text-to-SQL browser UI, see the [Text-to-SQL package](../text2sql/README.md). Those charts are built from the bounded result returned by the validated query executor and are separate from this static chart set.

## Reproducibility and interpretation

- Run chart generation from the repository root through `scripts/project.py charts`.
- Keep query definitions and chart-building code in `analytics/visualization/`; do not hand-edit generated chart images.
- Avoid customer-level identifiers or records in charts.
- Label money in source units until currency and gross/net semantics are confirmed.
- Treat discount and regional relationships as descriptive unless a causal design supports stronger claims.

The chart inventory and output directory are documented in [`docs/assets/charts/`](../docs/assets/charts/README.md).
