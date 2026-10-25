"""Run trusted SQL/template baselines against the current DuckDB warehouse.

This evaluates warehouse outputs, not natural-language interpretation. Use
``run_nl_evaluation`` separately for Gemini routing and guardrail behavior.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

from text2sql.catalog import CatalogConfig, load_config
from text2sql.executor import DuckDBExecutor, QueryResult
from text2sql.service import QueryService
from text2sql.validator import SQLValidationError, validate_sql


DEFAULT_GOLDEN_SET_PATH = Path(__file__).with_name("golden_set_v1.yml")


@dataclass(frozen=True)
class CaseOutcome:
    case_id: str
    passed: bool
    failures: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvaluationReport:
    evaluation_set_id: str
    version: int
    outcomes: tuple[CaseOutcome, ...]
    deferred_guardrail_count: int

    @property
    def passed_count(self) -> int:
        return sum(outcome.passed for outcome in self.outcomes)

    @property
    def failed_count(self) -> int:
        return len(self.outcomes) - self.passed_count


def _load_evaluation_set(path: str | Path = DEFAULT_GOLDEN_SET_PATH) -> Mapping[str, Any]:
    evaluation_path = Path(path).expanduser().resolve()
    try:
        with evaluation_path.open("r", encoding="utf-8") as stream:
            raw = yaml.safe_load(stream)
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"Could not load evaluation set ({type(exc).__name__}).") from None

    if not isinstance(raw, dict):
        raise ValueError("The evaluation set root must be a YAML mapping.")
    cases = raw.get("cases")
    guardrails = raw.get("guardrail_cases")
    if not isinstance(cases, list) or not isinstance(guardrails, list):
        raise ValueError("The evaluation set must define cases and guardrail_cases lists.")
    case_ids = [case.get("case_id") for case in cases if isinstance(case, dict)]
    if len(cases) != 15 or len(case_ids) != 15 or len(set(case_ids)) != 15:
        raise ValueError("Golden set v1 must contain exactly 15 uniquely named cases.")
    if len(guardrails) != 8 or any(not isinstance(case, dict) for case in guardrails):
        raise ValueError("Golden set v1 must contain exactly 8 guardrail cases.")
    _validate_evaluation_set_contract(raw)
    return raw


def _validate_evaluation_set_contract(evaluation_set: Mapping[str, Any]) -> None:
    """Fail before API calls when a golden case drifts from catalog or policy."""
    config = load_config()
    expected_ids = {f"q{index:02d}" for index in range(1, 16)}
    cases = evaluation_set["cases"]
    case_ids = {str(case.get("case_id")) for case in cases}
    if case_ids != expected_ids:
        raise ValueError("Golden set v1 case IDs must be q01 through q15.")

    for case in cases:
        case_id = str(case["case_id"])
        for field in ("question_vi", "question_en", "paraphrase_vi"):
            value = case.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Golden case {case_id} is missing a non-empty {field}.")

        expected_columns = case.get("expected_columns")
        if (
            not isinstance(expected_columns, list)
            or not expected_columns
            or any(not isinstance(column, str) or not column.strip() for column in expected_columns)
        ):
            raise ValueError(f"Golden case {case_id} expected_columns must be a non-empty string list.")
        normalized_columns = tuple(column.casefold() for column in expected_columns)
        if len(set(normalized_columns)) != len(normalized_columns):
            raise ValueError(f"Golden case {case_id} expected_columns contains duplicates.")

        expected_relations = case.get("expected_relations")
        if (
            not isinstance(expected_relations, list)
            or not expected_relations
            or any(not isinstance(relation, str) or not relation.strip() for relation in expected_relations)
        ):
            raise ValueError(f"Golden case {case_id} must define expected_relations.")
        for relation in expected_relations:
            if not isinstance(relation, str) or relation.casefold() not in config.catalog.models_by_relation:
                raise ValueError(f"Golden case {case_id} references an unknown relation.")

        metric_contracts = case.get("metric_contracts")
        if (
            not isinstance(metric_contracts, list)
            or any(not isinstance(metric, str) or not metric.strip() for metric in metric_contracts)
        ):
            raise ValueError(f"Golden case {case_id} metric_contracts must be a list.")
        unknown_metrics = sorted(set(metric_contracts) - set(config.catalog.metrics))
        if unknown_metrics:
            raise ValueError(
                f"Golden case {case_id} references unknown metric contract(s): "
                f"{', '.join(unknown_metrics)}."
            )

        expected_result = case.get("expected_result")
        if not isinstance(expected_result, Mapping):
            raise ValueError(f"Golden case {case_id} expected_result must be a mapping.")
        row_count = expected_result.get("row_count")
        if isinstance(row_count, bool) or not isinstance(row_count, int) or row_count < 0:
            raise ValueError(f"Golden case {case_id} expected row_count must be a non-negative integer.")

        baseline = case.get("baseline")
        if not isinstance(baseline, Mapping):
            raise ValueError(f"Golden case {case_id} must define a baseline mapping.")
        if baseline.get("type") == "policy_template":
            template_id = baseline.get("template_id")
            if not isinstance(template_id, str) or not template_id.strip():
                raise ValueError(f"Golden case {case_id} must define a template_id.")
            template = config.policy.templates.get(template_id)
            if template is None:
                raise ValueError(f"Golden case {case_id} references an unknown policy template.")
            if template.relation.casefold() not in {item.casefold() for item in expected_relations}:
                raise ValueError(f"Golden case {case_id} template relation is outside expected_relations.")
            if template.output_columns != normalized_columns:
                raise ValueError(f"Golden case {case_id} expected_columns differ from its template output schema.")
            query = validate_sql(
                template.sql,
                config,
                role=config.policy.default_role,
                template_id=template.template_id,
            )
        elif baseline.get("type") == "sql":
            sql = baseline.get("sql")
            if not isinstance(sql, str) or not sql.strip():
                raise ValueError(f"Golden case {case_id} must define baseline SQL.")
            query = validate_sql(sql, config, role=config.policy.default_role)
            if query.relation.casefold() not in {item.casefold() for item in expected_relations}:
                raise ValueError(f"Golden case {case_id} SQL relation is outside expected_relations.")
        else:
            raise ValueError(f"Golden case {case_id} baseline type must be sql or policy_template.")

        if query.output_columns != normalized_columns:
            raise ValueError(f"Golden case {case_id} expected_columns differ from its baseline output schema.")


def _as_decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        try:
            return Decimal(str(value))
        except InvalidOperation:
            return None
    return None


def _values_match(actual: Any, expected: Any, tolerance: Decimal) -> bool:
    actual_number = _as_decimal(actual)
    expected_number = _as_decimal(expected)
    if actual_number is not None and expected_number is None and isinstance(expected, str):
        try:
            expected_number = Decimal(expected)
        except InvalidOperation:
            pass
    if actual_number is not None and expected_number is not None:
        return abs(actual_number - expected_number) <= tolerance
    if isinstance(actual, (date, datetime)) and isinstance(expected, str):
        return actual.isoformat() == expected
    return actual == expected


def _row_dicts(result: QueryResult) -> tuple[dict[str, Any], ...]:
    return tuple(
        {column.casefold(): value for column, value in zip(result.columns, row)}
        for row in result.rows
    )


def _check_projection(
    actual: Mapping[str, Any],
    expected: Mapping[str, Any],
    tolerance: Decimal,
    label: str,
) -> list[str]:
    failures: list[str] = []
    for raw_column, expected_value in expected.items():
        column = str(raw_column).casefold()
        if column not in actual:
            failures.append(f"{label}: missing expected field {column!r}")
        elif not _values_match(actual[column], expected_value, tolerance):
            failures.append(f"{label}: value mismatch for {column!r}")
    return failures


def _scalar_value(
    name: str,
    rows: Sequence[Mapping[str, Any]],
    columns: Sequence[str],
    tolerance: Decimal,
) -> tuple[Any | None, str | None]:
    key = name.casefold()
    if not rows:
        return None, f"scalar assertion {name!r} requires at least one returned row"
    if key in columns:
        values = [row[key] for row in rows]
        if len(values) == 1:
            return values[0], None
        try:
            return sum((Decimal(str(value)) for value in values), Decimal(0)), None
        except (InvalidOperation, TypeError):
            return None, f"cannot aggregate scalar assertion {name!r}"

    if key == "overall_weighted_average_discount":
        try:
            discount_column = "average_discount" if "average_discount" in columns else "avg_discount"
            weighted_sum = sum(
                Decimal(str(row[discount_column])) * Decimal(str(row["sales_line_count"]))
                for row in rows
            )
            weight_sum = sum(Decimal(str(row["sales_line_count"])) for row in rows)
            if weight_sum == 0:
                return None, "weighted discount assertion has zero total weight"
            return weighted_sum / weight_sum, None
        except (KeyError, InvalidOperation, TypeError):
            return None, "weighted discount assertion requires avg_discount and sales_line_count"

    score_count = re.fullmatch(r"each_(recency|frequency|monetary)_score_count", key)
    if score_count:
        prefix = f"{score_count.group(1)}_score_"
        score_values = [
            row[column]
            for row in rows
            for column in columns
            if column.startswith(prefix) and column.endswith("_customers")
        ]
        if not score_values:
            return None, f"no score-count columns found for {score_count.group(1)}"
        if any(not _values_match(value, score_values[0], tolerance) for value in score_values[1:]):
            return None, f"score-count columns differ for {score_count.group(1)}"
        return score_values[0], None

    return None, f"unsupported scalar assertion {name!r}"


def _compare_case(case: Mapping[str, Any], result: QueryResult, tolerance: Decimal) -> list[str]:
    failures: list[str] = []
    case_id = str(case["case_id"])
    expected_columns = tuple(str(value).casefold() for value in case["expected_columns"])
    actual_columns = tuple(column.casefold() for column in result.columns)
    if actual_columns != expected_columns:
        failures.append("returned columns differ from the golden contract")
    expected_relations = {
        str(value).casefold() for value in case.get("expected_relations", [])
    }
    if expected_relations and result.relation.casefold() not in expected_relations:
        failures.append("query used a relation outside the expected mart contract")
    expected = case["expected_result"]
    if result.row_count != expected["row_count"]:
        failures.append(f"row count mismatch (expected {expected['row_count']}, got {result.row_count})")
    if result.truncated:
        failures.append("baseline exceeded the configured result limit")

    rows = _row_dicts(result)
    if "scalar" in expected:
        scalar = expected["scalar"]
        if not isinstance(scalar, Mapping):
            failures.append("scalar expectation must be a mapping")
        else:
            for name, expected_value in scalar.items():
                actual_value, error = _scalar_value(name, rows, actual_columns, tolerance)
                if error:
                    failures.append(error)
                elif not _values_match(actual_value, expected_value, tolerance):
                    failures.append(f"scalar value mismatch for {name!r}")

    for expectation_name in ("rows", "top_rows"):
        expected_rows = expected.get(expectation_name)
        if expected_rows is not None:
            if not isinstance(expected_rows, list) or len(rows) < len(expected_rows):
                failures.append(f"not enough rows for {expectation_name} assertion")
            else:
                for index, expected_row in enumerate(expected_rows):
                    failures.extend(
                        _check_projection(rows[index], expected_row, tolerance, f"{expectation_name}[{index}]")
                    )

    for expectation_name, key_columns in (
        ("rows_by_gender_occupation", ("gender", "occupation")),
        ("rows_by_segment", ("segment",)),
    ):
        expected_rows = expected.get(expectation_name)
        if expected_rows is not None:
            actual_index = {
                tuple(row.get(column) for column in key_columns): row for row in rows
            }
            for expected_row in expected_rows:
                key = tuple(expected_row.get(column) for column in key_columns)
                actual_row = actual_index.get(key)
                if actual_row is None:
                    failures.append(f"{expectation_name}: missing key {key!r}")
                else:
                    failures.extend(
                        _check_projection(actual_row, expected_row, tolerance, f"{expectation_name}{key!r}")
                    )

    keyed_rows = expected.get("rows_by_key")
    if keyed_rows is not None:
        for expected_row in keyed_rows:
            key_name = "market" if "market" in expected_row else "country"
            key = expected_row[key_name]
            actual_row = next((row for row in rows if row.get(key_name) == key), None)
            if actual_row is None:
                failures.append(f"rows_by_key: missing {key_name} {key!r}")
            else:
                failures.extend(
                    _check_projection(actual_row, expected_row, tolerance, f"rows_by_key[{key!r}]")
                )

    segment_summaries = expected.get("scalar_by_segment")
    if segment_summaries is not None:
        for segment, summary in segment_summaries.items():
            group = [row for row in rows if row.get("segment") == segment]
            if len(group) != summary["category_count"]:
                failures.append(f"scalar_by_segment[{segment!r}]: category count mismatch")
            total_sales = sum((Decimal(str(row["total_sales"])) for row in group), Decimal(0))
            if not _values_match(total_sales, summary["total_sales"], tolerance):
                failures.append(f"scalar_by_segment[{segment!r}]: total_sales mismatch")

    category_summaries = expected.get("rows_by_category")
    if category_summaries is not None:
        for summary in category_summaries:
            category = summary["category"]
            actual_row = next(
                (
                    row for row in rows
                    if row.get("category") == category and row.get("category_profit_rank") == 1
                ),
                None,
            )
            if actual_row is None:
                failures.append(f"rows_by_category: missing rank 1 for {category!r}")
            else:
                failures.extend(
                    _check_projection(
                        actual_row,
                        {
                            "product_code": summary["rank_1_product_code"],
                            "total_profit": summary["rank_1_total_profit"],
                        },
                        tolerance,
                        f"rows_by_category[{category!r}]",
                    )
                )

    date_range = expected.get("date_range")
    if date_range is not None:
        dates = [row.get("sales_month") for row in rows if row.get("sales_month") is not None]
        if not dates:
            failures.append("date_range assertion found no sales_month values")
        else:
            normalized = [value.isoformat() if isinstance(value, (date, datetime)) else str(value) for value in dates]
            if min(normalized) != date_range["first"] or max(normalized) != date_range["last"]:
                failures.append("sales_month date range mismatch")

    expected_population = expected.get("expected_population")
    if expected_population is not None:
        actual_population = sum(
            (Decimal(str(row["customer_count"])) for row in rows), Decimal(0)
        )
        if not _values_match(actual_population, expected_population, tolerance):
            failures.append("customer population total mismatch")

    # Include the case id in diagnostics so reports remain useful when cases are
    # filtered or reordered in a later evaluation-set version.
    return [f"{case_id}: {failure}" for failure in failures]


def run_baselines(
    *,
    evaluation_path: str | Path = DEFAULT_GOLDEN_SET_PATH,
    database_path: str | Path | None = None,
    role: str | None = None,
) -> EvaluationReport:
    """Execute and compare the 15 canonical SQL/template baselines."""
    evaluation_set = _load_evaluation_set(evaluation_path)
    config: CatalogConfig = load_config()
    trusted_role = config.policy.default_role if role is None else role
    executor = DuckDBExecutor(database_path=database_path, config=config)
    service = QueryService(database_path=database_path, config=config)
    tolerance = Decimal(str(evaluation_set["comparison"]["numeric_absolute_tolerance"]))
    outcomes: list[CaseOutcome] = []

    for case in evaluation_set["cases"]:
        case_id = str(case["case_id"])
        baseline = case.get("baseline", {})
        try:
            if baseline.get("type") == "policy_template":
                result = service.execute_template(baseline["template_id"], role=trusted_role)
            elif baseline.get("type") == "sql":
                query = validate_sql(baseline["sql"], config, role=trusted_role)
                result = executor.execute(query)
            else:
                outcomes.append(CaseOutcome(case_id, False, ("unsupported baseline type",)))
                continue
            failures = _compare_case(case, result, tolerance)
            outcomes.append(CaseOutcome(case_id, not failures, tuple(failures)))
        except SQLValidationError as exc:
            outcomes.append(CaseOutcome(case_id, False, (f"SQL validation failed: {exc}",)))
        except Exception as exc:
            # Avoid echoing SQL, environment values, or the underlying database
            # message into the evaluation report.
            outcomes.append(
                CaseOutcome(case_id, False, (f"baseline execution failed ({type(exc).__name__})",))
            )

    return EvaluationReport(
        evaluation_set_id=str(evaluation_set["evaluation_set_id"]),
        version=int(evaluation_set["version"]),
        outcomes=tuple(outcomes),
        deferred_guardrail_count=len(evaluation_set["guardrail_cases"]),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate the e-commerce SQL/template baselines.")
    parser.add_argument("--evaluation-set", type=Path, default=DEFAULT_GOLDEN_SET_PATH)
    parser.add_argument("--database", type=Path, default=None, help="Optional DuckDB warehouse path.")
    parser.add_argument("--role", default=None, help="Trusted configured role; defaults to policy default.")
    args = parser.parse_args(argv)

    try:
        report = run_baselines(
            evaluation_path=args.evaluation_set,
            database_path=args.database,
            role=args.role,
        )
    except Exception as exc:
        print(f"Evaluation could not start ({type(exc).__name__}).", file=sys.stderr)
        return 2

    for outcome in report.outcomes:
        state = "PASS" if outcome.passed else "FAIL"
        print(f"{state} {outcome.case_id}")
        for failure in outcome.failures:
            print(f"  - {failure}")
    print(
        f"\n{report.evaluation_set_id} v{report.version}: "
        f"{report.passed_count}/{len(report.outcomes)} baseline cases passed; "
        f"{report.deferred_guardrail_count} guardrail cases require the "
        "separate natural-language evaluator."
    )
    return 0 if report.failed_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
