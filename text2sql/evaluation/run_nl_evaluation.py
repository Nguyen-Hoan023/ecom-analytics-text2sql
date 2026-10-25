"""Evaluate Gemini routing against the approved natural-language golden set.

The report records only case identifiers, action statuses, and pass/fail
diagnostics. It never writes prompts, API keys, generated SQL, or query rows.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

from text2sql.catalog import load_config
from text2sql.gemini import GeminiConfigurationError, GeminiDecisionGenerator, GeminiSettings
from text2sql.nl_service import NaturalLanguageQueryService, TextToSQLResponse
from text2sql.evaluation.run_baselines import (
    DEFAULT_GOLDEN_SET_PATH,
    _compare_case,
    _load_evaluation_set,
)


@dataclass(frozen=True)
class NLEvaluationOutcome:
    case_id: str
    variant: str
    language: str
    passed: bool
    actual_status: str
    failures: tuple[str, ...] = ()


@dataclass(frozen=True)
class NLEvaluationReport:
    evaluation_set_id: str
    version: int
    model: str
    generated_at_utc: str
    planned_count: int
    outcomes: tuple[NLEvaluationOutcome, ...]
    stopped_reason: str | None = None

    @property
    def passed_count(self) -> int:
        return sum(outcome.passed for outcome in self.outcomes)

    @property
    def failed_count(self) -> int:
        return len(self.outcomes) - self.passed_count

    @property
    def skipped_count(self) -> int:
        return max(0, self.planned_count - len(self.outcomes))


def _answer_failures(
    case: Mapping[str, Any],
    response: TextToSQLResponse,
    *,
    language: str,
    numeric_tolerance: Decimal,
    hard_row_cap: int,
) -> list[str]:
    failures: list[str] = []
    case_id = str(case["case_id"])
    if response.status != "answered":
        return [
            f"expected an answer; received status {response.status!r}",
            f"service message: {response.message}",
        ]
    if response.result is None:
        return ["answer status contained no result table"]

    baseline = case.get("baseline", {})
    if baseline.get("type") == "policy_template":
        if response.template_id != baseline.get("template_id"):
            failures.append("restricted mart did not use its exact approved template")
        if response.sql is not None:
            failures.append("approved-template answer unexpectedly exposed generated SQL")
    elif baseline.get("type") == "sql":
        if not response.sql:
            failures.append("direct Gold-mart answer did not return validated SQL")
        if response.template_id is not None:
            failures.append("direct SQL answer unexpectedly selected a restricted template")
    else:
        failures.append("golden case has an unsupported baseline type")

    if response.result.row_count > response.result.row_limit:
        failures.append("returned row count exceeded the query row limit")
    if response.result.row_limit > hard_row_cap:
        failures.append("query row limit exceeded the policy hard cap")
    if response.result.truncated:
        failures.append("golden answer was truncated by the result limit")
    failures.extend(_compare_case(case, response.result, numeric_tolerance))
    if case.get("behavior") == "answer_with_scope_caveat":
        scope_marker = (
            "không phải sản phẩm thường được mua cùng nhau"
            if language == "vi"
            else "not products commonly bought together"
        )
        if scope_marker not in response.message.casefold():
            failures.append("category-mix answer omitted the approved scope caveat")
    if baseline.get("type") == "policy_template" and baseline.get("template_id") in {
        "q08_vip_risk_summary",
        "q14_rfm_population_summary",
    }:
        snapshot_marker = (
            "snapshot lịch sử 2024-01-01"
            if language == "vi"
            else "historical 2024-01-01 snapshot"
        )
        if snapshot_marker not in response.message.casefold():
            failures.append("RFM template answer omitted the historical-snapshot caveat")
    if baseline.get("type") == "policy_template" and baseline.get("template_id") == "q13_region_behavior_summary":
        orphan_marker = "region orphan" if language == "vi" else "orphan-region activity"
        if orphan_marker not in response.message.casefold():
            failures.append("region summary omitted the orphan-region caveat")
    return failures


def _guardrail_failures(
    guardrail: Mapping[str, Any],
    response: TextToSQLResponse,
    *,
    language: str,
    cases_by_id: Mapping[str, Mapping[str, Any]],
    numeric_tolerance: Decimal,
) -> list[str]:
    expected_action = guardrail.get("expected_action")
    no_query_output = (
        response.result is None and response.sql is None and response.template_id is None
    )

    if expected_action == "deny":
        failures = []
        if response.status not in {"refused", "rejected"}:
            failures.append("expected a refusal or validator rejection")
        if not no_query_output:
            failures.append("a denied request produced SQL or a result")
        return failures

    if expected_action == "clarify":
        if response.status != "clarify" or not no_query_output:
            return ["expected a clarification request with no SQL execution"]
        return []

    if expected_action == "caveat_or_clarify":
        if response.status != "clarify" or not no_query_output:
            return ["causal discount wording must be reframed before querying"]
        causality_marker = (
            "không chứng minh discount là nguyên nhân"
            if language == "vi"
            else "does not establish that discount caused the change"
        )
        if causality_marker not in response.message.casefold():
            return ["clarification omitted the non-causality caveat"]
        return []

    if expected_action == "answer_no_qualifying_rows":
        if response.status != "answered" or response.result is None:
            return ["expected an answer containing the qualifying association result"]
        if response.result.row_count != 0:
            return ["expected no qualifying product associations at the configured support"]
        empty_marker = (
            "không có cặp sản phẩm nào đạt support tối thiểu 0,5%"
            if language == "vi"
            else "no product pairs meet the current 0.5% support threshold"
        )
        if empty_marker not in response.message.casefold():
            return ["empty association result did not explain the configured support threshold"]
        if response.result.truncated:
            return ["association result was truncated"]
        expected_case_id = str(guardrail.get("expected_case_id", ""))
        expected_case = cases_by_id.get(expected_case_id)
        if expected_case is None:
            return ["guardrail references an unknown golden result case"]
        return _compare_case(expected_case, response.result, numeric_tolerance)

    return ["unsupported guardrail expected_action"]


def _evaluate_response(
    *,
    case_id: str,
    variant: str,
    language: str,
    question: str,
    service: NaturalLanguageQueryService,
    case: Mapping[str, Any] | None = None,
    guardrail: Mapping[str, Any] | None = None,
    cases_by_id: Mapping[str, Mapping[str, Any]],
    numeric_tolerance: Decimal,
    hard_row_cap: int,
) -> NLEvaluationOutcome:
    try:
        response = service.ask(question)
    except Exception as exc:
        return NLEvaluationOutcome(
            case_id=case_id,
            variant=variant,
            language=language,
            passed=False,
            actual_status=f"error:{type(exc).__name__}",
            failures=("request failed before a safe response was produced",),
        )

    if case is not None:
        failures = _answer_failures(
            case,
            response,
            language=language,
            numeric_tolerance=numeric_tolerance,
            hard_row_cap=hard_row_cap,
        )
    elif guardrail is not None:
        failures = _guardrail_failures(
            guardrail,
            response,
            language=language,
            cases_by_id=cases_by_id,
            numeric_tolerance=numeric_tolerance,
        )
    else:
        failures = ["evaluation row has no case or guardrail specification"]
    return NLEvaluationOutcome(
        case_id=case_id,
        variant=variant,
        language=language,
        passed=not failures,
        actual_status=response.status,
        failures=tuple(failures),
    )


def _canonical_question(case: Mapping[str, Any], language: str) -> str:
    key = "question_vi" if language == "vi" else "question_en"
    question = case.get(key)
    if not isinstance(question, str) or not question.strip():
        raise ValueError(f"Golden case {case.get('case_id')!r} is missing {key}.")
    return question


def run_nl_evaluation(
    *,
    evaluation_path: str | Path = DEFAULT_GOLDEN_SET_PATH,
    database_path: str | Path | None = None,
    language: str = "vi",
    variant: str = "canonical",
    include_guardrails: bool = False,
    case_ids: Sequence[str] | None = None,
    pause_ms: int = 15000,
) -> NLEvaluationReport:
    """Run selected canonical, paraphrase, and optional guardrail requests."""
    if language not in {"vi", "en", "both"}:
        raise ValueError("language must be vi, en, or both.")
    if variant not in {"canonical", "paraphrase", "all"}:
        raise ValueError("variant must be canonical, paraphrase, or all.")
    if pause_ms < 0:
        raise ValueError("pause_ms must be zero or greater.")

    settings = GeminiSettings.from_env()
    if not settings.api_key:
        raise GeminiConfigurationError(
            "Set GEMINI_API_KEY in the local .env before running live natural-language evaluation."
        )

    evaluation_set = _load_evaluation_set(evaluation_path)
    all_cases = evaluation_set["cases"]
    all_guardrails = evaluation_set["guardrail_cases"]
    case_ids_set = {str(case["case_id"]) for case in all_cases}
    guardrail_ids_set = {str(case["case_id"]) for case in all_guardrails}
    requested_ids = set(case_ids or ())
    unknown_ids = requested_ids - case_ids_set - guardrail_ids_set
    if unknown_ids:
        raise ValueError(f"Unknown evaluation case id(s): {', '.join(sorted(unknown_ids))}.")

    selected_cases = [case for case in all_cases if not requested_ids or case["case_id"] in requested_ids]
    if not selected_cases and not include_guardrails:
        raise ValueError("No canonical cases matched the requested selection.")
    if variant in {"paraphrase", "all"}:
        missing = [case["case_id"] for case in selected_cases if not case.get("paraphrase_vi")]
        if missing:
            raise ValueError(f"Cases missing Vietnamese paraphrases: {', '.join(missing)}.")

    selected_guardrails = [
        case for case in all_guardrails
        if include_guardrails and (not requested_ids or case["case_id"] in requested_ids)
    ]
    if requested_ids and not selected_cases and not selected_guardrails:
        raise ValueError("No cases matched the requested selection.")

    languages = ("vi", "en") if language == "both" else (language,)
    questions_per_case = (
        (len(languages) if variant in {"canonical", "all"} else 0)
        + (1 if variant in {"paraphrase", "all"} else 0)
    )
    planned_count = len(selected_cases) * questions_per_case
    planned_count += len(selected_guardrails) * len(languages)

    config = load_config()
    numeric_tolerance = Decimal(str(evaluation_set["comparison"]["numeric_absolute_tolerance"]))
    hard_row_cap = int(config.policy.duckdb_execution["output_rows_hard_cap"])
    service = NaturalLanguageQueryService(
        database_path=database_path,
        config=config,
        generator=GeminiDecisionGenerator(settings),
    )
    cases_by_id = {str(case["case_id"]): case for case in all_cases}
    outcomes: list[NLEvaluationOutcome] = []
    stopped_reason: str | None = None

    try:
        for case in selected_cases:
            questions: list[tuple[str, str, str]] = []
            if variant in {"canonical", "all"}:
                languages = ("vi", "en") if language == "both" else (language,)
                questions.extend(
                    (f"canonical_{item_language}", item_language, _canonical_question(case, item_language))
                    for item_language in languages
                )
            if variant in {"paraphrase", "all"}:
                questions.append(("paraphrase_vi", "vi", str(case["paraphrase_vi"])))

            for variant_name, item_language, question in questions:
                outcomes.append(
                    _evaluate_response(
                        case_id=str(case["case_id"]),
                        variant=variant_name,
                        language=item_language,
                        question=question,
                        service=service,
                        case=case,
                        cases_by_id=cases_by_id,
                        numeric_tolerance=numeric_tolerance,
                        hard_row_cap=hard_row_cap,
                    )
                )
                if outcomes[-1].actual_status == "unavailable":
                    stopped_reason = (
                        "Stopped after Gemini became unavailable; remaining cases were not sent. "
                        "Check the sanitized failure for an HTTP status and verify project quota/rate limits."
                    )
                    break
                if pause_ms:
                    time.sleep(pause_ms / 1000)
            if stopped_reason:
                break

        if include_guardrails and not stopped_reason:
            for guardrail in selected_guardrails:
                for item_language in languages:
                    key = "question_vi" if item_language == "vi" else "question_en"
                    outcomes.append(
                        _evaluate_response(
                            case_id=str(guardrail["case_id"]),
                            variant="guardrail",
                            language=item_language,
                            question=str(guardrail[key]),
                            service=service,
                            guardrail=guardrail,
                            cases_by_id=cases_by_id,
                            numeric_tolerance=numeric_tolerance,
                            hard_row_cap=hard_row_cap,
                        )
                    )
                    if outcomes[-1].actual_status == "unavailable":
                        stopped_reason = (
                            "Stopped after Gemini became unavailable; remaining cases were not sent. "
                            "Check the sanitized failure for an HTTP status and verify project quota/rate limits."
                        )
                        break
                    if pause_ms:
                        time.sleep(pause_ms / 1000)
                if stopped_reason:
                    break
    finally:
        service.close()

    return NLEvaluationReport(
        evaluation_set_id=str(evaluation_set["evaluation_set_id"]),
        version=int(evaluation_set["version"]),
        model=settings.model,
        generated_at_utc=datetime.now(timezone.utc).isoformat(),
        planned_count=planned_count,
        outcomes=tuple(outcomes),
        stopped_reason=stopped_reason,
    )


def _report_payload(report: NLEvaluationReport) -> dict[str, Any]:
    return {
        "evaluation_set_id": report.evaluation_set_id,
        "version": report.version,
        "model": report.model,
        "generated_at_utc": report.generated_at_utc,
        "planned_count": report.planned_count,
        "skipped_count": report.skipped_count,
        "stopped_reason": report.stopped_reason,
        "passed_count": report.passed_count,
        "failed_count": report.failed_count,
        "outcomes": [asdict(outcome) for outcome in report.outcomes],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate Gemini Text-to-SQL answers against the Xom E-Com golden set."
    )
    parser.add_argument("--evaluation-set", type=Path, default=DEFAULT_GOLDEN_SET_PATH)
    parser.add_argument("--database", type=Path, default=None, help="Optional DuckDB warehouse path.")
    parser.add_argument("--language", choices=("vi", "en", "both"), default="vi")
    parser.add_argument("--variant", choices=("canonical", "paraphrase", "all"), default="canonical")
    parser.add_argument("--case-id", action="append", default=None, help="Evaluate only the selected case; repeatable.")
    parser.add_argument("--guardrails", action="store_true", help="Include the selected safety/clarification cases.")
    parser.add_argument(
        "--pause-ms",
        type=int,
        default=15000,
        help="Pause between Gemini requests (default: 15000 ms); adjust to active project limits.",
    )
    parser.add_argument("--output", type=Path, default=None, help="Optional sanitized JSON report path.")
    args = parser.parse_args(argv)

    try:
        report = run_nl_evaluation(
            evaluation_path=args.evaluation_set,
            database_path=args.database,
            language=args.language,
            variant=args.variant,
            include_guardrails=args.guardrails,
            case_ids=args.case_id,
            pause_ms=args.pause_ms,
        )
    except Exception as exc:
        print(f"Natural-language evaluation could not start ({type(exc).__name__}).", file=sys.stderr)
        return 2

    for outcome in report.outcomes:
        state = "PASS" if outcome.passed else "FAIL"
        print(f"{state} {outcome.case_id} {outcome.variant} [{outcome.actual_status}]")
        for failure in outcome.failures:
            print(f"  - {failure}")
    print(
        f"\n{report.evaluation_set_id} v{report.version}: "
        f"{report.passed_count}/{report.planned_count} planned natural-language cases passed "
        f"with {report.model}."
    )
    if report.skipped_count:
        print(f"Stopped early; {report.skipped_count} remaining cases were not sent.")
    if report.stopped_reason:
        print(report.stopped_reason)

    if args.output is not None:
        try:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(_report_payload(report), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            print(f"Could not write evaluation report ({type(exc).__name__}).", file=sys.stderr)
            return 2
        print(f"Sanitized report written to {args.output}.")
    return 0 if report.failed_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
