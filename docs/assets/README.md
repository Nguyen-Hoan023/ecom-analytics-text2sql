# Documentation assets

This folder stores reviewable visual outputs used by the documentation.

## Contents

| Asset | Owner/source | Update method |
|---|---|---|
| [system-architecture.png](system-architecture.png) | Repository architecture | Edit the image when system boundaries or data/control flows change. |
| [charts/](charts/) | Gold marts | Regenerate with the chart script after a successful dbt build. See [chart inventory](charts/README.md). |

## Asset rules

- Keep diagrams aligned with the actual code and deployment boundary.
- Keep charts aggregate; do not add customer-level records or local source exports.
- Do not commit DuckDB files, credentials, screenshots containing secrets, or temporary chart drafts.
- Prefer a source file or reproducible generator for visuals when available. The static chart PNGs are generated outputs, not hand-edited data.
