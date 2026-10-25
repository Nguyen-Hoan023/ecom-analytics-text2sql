# dbt data tests

This directory contains singular dbt tests: SQL assertions that must return zero rows for the warehouse contract to hold. Generic `not_null`, `unique`, and relationship tests are declared beside models in YAML; singular cross-model and reconciliation checks live here.

## What belongs here

- Fact-preservation and row-count reconciliation after dimension joins.
- Grain assertions for marts whose key is composite or needs explicit validation.
- Metric reconciliation between Gold and its documented source/intermediate relation.
- Domain-specific invariants that cannot be expressed clearly as a generic YAML test.

## Running tests

From the repository root:

    uv run --project . python scripts/project.py dbt test

For a targeted assertion, run dbt with its test node name or select the related model. During CI, `dbt parse` and static contracts can run without a populated warehouse; data tests require the source-derived warehouse.

## Authoring rules

1. Return failing records only; a passing test returns no rows.
2. State the invariant in the filename, such as `assert_<model>_<grain>.sql`.
3. Compare values at compatible grain and preserve source-unit semantics.
4. Do not turn a one-time snapshot number into a permanent expected value unless the contract explicitly defines it.
5. Keep customer-level identifiers out of test logs and public artifacts.

See the parent [model map](../models/README.md), [data contract](../../docs/data-contract.md), and [dbt project guide](../README.md).
