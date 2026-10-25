"""Run no-API acceptance checks for deterministic guardrails and golden data."""

from __future__ import annotations

import sys
from decimal import Decimal

from text2sql.catalog import load_config
from text2sql.evaluation.run_baselines import (
    DEFAULT_GOLDEN_SET_PATH,
    _load_evaluation_set,
)
from text2sql.evaluation.run_nl_evaluation import _guardrail_failures
from text2sql.nl_service import NaturalLanguageQueryService


_OFFLINE_GUARDRAILS = frozenset(
    {
        "deny_customer_identifiers",
        "deny_customer_level_rfm",
        "deny_customer_level_region_behavior",
        "deny_destructive_instruction",
        "clarify_current_period",
        "clarify_profitability_metric",
        "reject_causal_discount_claim",
    }
)


class _NoModelCalls:
    """Fail loudly if an offline-safe question unexpectedly reaches Gemini."""

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, *, user_payload: str):
        self.calls += 1
        raise AssertionError("Offline guardrail unexpectedly called the model.")

    def close(self) -> None:
        pass


def run_offline_checks(evaluation_path=DEFAULT_GOLDEN_SET_PATH) -> int:
    evaluation_set = _load_evaluation_set(evaluation_path)
    cases_by_id = {str(case["case_id"]): case for case in evaluation_set["cases"]}
    config = load_config()
    tolerance = Decimal(str(evaluation_set["comparison"]["numeric_absolute_tolerance"]))
    guardrails = evaluation_set["guardrail_cases"]
    selected = [item for item in guardrails if item["case_id"] in _OFFLINE_GUARDRAILS]
    if len(selected) != len(_OFFLINE_GUARDRAILS):
        raise ValueError("The offline guardrail ID set does not match the golden set.")

    generator = _NoModelCalls()
    service = NaturalLanguageQueryService(config=config, generator=generator)
    guardrail_failures = 0
    try:
        for guardrail in selected:
            for language, question_key in (("vi", "question_vi"), ("en", "question_en")):
                response = service.ask(str(guardrail[question_key]))
                failures = _guardrail_failures(
                    guardrail,
                    response,
                    language=language,
                    cases_by_id=cases_by_id,
                    numeric_tolerance=tolerance,
                )
                if generator.calls:
                    failures.append("offline guardrail reached the model generator")
                state = "PASS" if not failures else "FAIL"
                print(f"{state} {guardrail['case_id']} {language} offline [{response.status}]")
                for failure in failures:
                    print(f"  - {failure}")
                guardrail_failures += bool(failures)
    finally:
        service.close()

    paraphrases = [case.get("paraphrase_vi") for case in evaluation_set["cases"]]
    paraphrases_valid = (
        len(paraphrases) == 15
        and all(isinstance(item, str) and item.strip() for item in paraphrases)
        and len({item.strip().casefold() for item in paraphrases if isinstance(item, str)}) == 15
    )
    print(
        f"{'PASS' if paraphrases_valid else 'FAIL'} paraphrase inventory "
        f"[{sum(bool(item and str(item).strip()) for item in paraphrases)}/15 non-empty, unique]"
    )
    print("DEFER paraphrase semantic understanding [requires Gemini; no model calls made]")

    deferred = [item["case_id"] for item in guardrails if item["case_id"] not in _OFFLINE_GUARDRAILS]
    for case_id in deferred:
        print(f"DEFER {case_id} [requires natural-language routing; baseline is checked separately]")
    print(
        f"\nOffline checks: {len(selected) * 2 - guardrail_failures}/{len(selected) * 2} deterministic guardrail language cases passed; "
        f"Gemini calls=0; {len(deferred)} guardrail case(s) deferred."
    )
    return 1 if guardrail_failures or not paraphrases_valid else 0


def main() -> int:
    try:
        return run_offline_checks()
    except Exception as exc:
        print(f"Offline evaluation could not run ({type(exc).__name__}).", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
