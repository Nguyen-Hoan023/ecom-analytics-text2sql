"""Natural-language routing into the validated Text-to-SQL execution path."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping

from text2sql.catalog import CatalogConfig, ModelSpec, load_config
from text2sql.executor import DuckDBExecutor, ExecutorError, QueryResult
from text2sql.gemini import (
    MAX_QUESTION_LENGTH,
    GeminiConfigurationError,
    GeminiDecisionGenerator,
    GeminiGenerationError,
    GeminiSettings,
    ModelDecision,
    SYSTEM_INSTRUCTION,
)
from text2sql.service import QueryService, QueryServiceError, TemplateInfo
from text2sql.validator import SQLValidationError, validate_sql


_EMAIL_PATTERN = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b", re.IGNORECASE)
_PHONE_PATTERN = re.compile(
    r"(?<!\w)(?:\+\d{1,3}[\s.-]?\d[\d\s().-]{6,}\d|"
    r"\(\d{3}\)\s*\d{3}[-. ]?\d{4}|\d{3}[-. ]\d{3}[-. ]\d{4})(?!\w)"
)
_CUSTOMER_ID_PATTERN = re.compile(r"\b[A-Z]{2}-\d{6,}\b", re.IGNORECASE)
_LONG_NUMBER_PATTERN = re.compile(r"(?<!\d)\d(?:[\s().-]*\d){9,14}(?!\d)")
_DISCOUNT_CAUSALITY_PATTERNS = (
    re.compile(
        r"\b(discounts?|khuyến mãi|giảm giá)\b.{0,70}\b(cause|caused|causing|impact|effect|gây|làm|khiến|tác động|ảnh hưởng)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(cause|caused|impact|effect|gây|nguyên nhân|tác động|ảnh hưởng)\b.{0,70}\b(discounts?|khuyến mãi|giảm giá)\b",
        re.IGNORECASE,
    ),
)
_DESTRUCTIVE_INTENT_PATTERN = re.compile(
    r"\b(?:drop|delete|truncate|alter)\s+(?:table|database|schema|view)\b|"
    r"\b(?:insert\s+into|update\s+[a-z_][\w.]*\s+set|create\s+(?:table|view|schema|database))\b|"
    r"\b(?:xóa|xoa|xoá|huỷ|hủy|sửa|ghi)\s+(?:bảng|table|database|schema|view|dữ liệu)\b",
    re.IGNORECASE,
)
_CURRENT_PERIOD_PATTERNS = (
    re.compile(r"\b(?:tháng này|năm nay|tuần này|hôm nay|hiện tại|kỳ hiện tại)\b", re.IGNORECASE),
    re.compile(r"\b(?:this month|this year|this week|today|currently|current period)\b", re.IGNORECASE),
)
_AMBIGUOUS_PROFIT_PATTERN = re.compile(
    r"\b(?:lợi nhuận|loi nhuan)\b.{0,45}\b(?:tốt nhất|cao nhất|nhiều nhất)\b|"
    r"\b(?:tốt nhất|cao nhất|nhiều nhất)\b.{0,45}\b(?:lợi nhuận|loi nhuan)\b|"
    r"\bmost profitable\b|\b(?:best|highest)\s+profit(?:ability)?\b|"
    r"\bprofit(?:ability)?\s+(?:is\s+)?(?:best|highest|most profitable)\b",
    re.IGNORECASE,
)
_SENSITIVE_TERMS = (
    "customer_id",
    "customer id",
    "email_address",
    "email address",
    "email",
    "e-mail",
    "first_name",
    "first name",
    "last_name",
    "last name",
    "birth_date",
    "birth date",
    "annual_income",
    "annual income",
    "ngày sinh",
    "thu nhập",
    "họ tên khách",
    "tên khách hàng",
    "email khách hàng",
    "số điện thoại",
    "địa chỉ nhà",
    "customer name",
    "customer email",
    "customer phone",
    "customer address",
    "phone",
    "telephone",
    "sđt",
    "điện thoại",
)
_SENSITIVE_TERM_PATTERN = re.compile(
    "|".join(re.escape(term) for term in sorted(_SENSITIVE_TERMS, key=len, reverse=True)),
    re.IGNORECASE,
)
_NEGATION_BEFORE_FIELD_PATTERN = re.compile(
    r"\b(không|khong|not|don't|do not|without|exclude|excluding|omit|never)\b[^.!?]{0,45}$",
    re.IGNORECASE,
)
_INDIVIDUAL_LIST_PATTERNS = (
    re.compile(r"\b(list|show|identify|give me|return)\b.{0,30}\b(customers|individual customers|customer records)\b", re.I),
    re.compile(r"\b(customers?)\b.{0,30}\b(names?|ids?|records|emails?|phone numbers?)\b", re.I),
    re.compile(r"\b(top\s+\d+|best|worst)\s+customers\b", re.I),
    re.compile(r"\b(liệt kê|danh sách|cho tôi từng|từng)\b.{0,35}\b(danh sách khách hàng|từng khách hàng|thông tin khách hàng)\b", re.I),
    re.compile(r"\b(top\s+\d+|khách hàng tốt nhất|khách hàng tệ nhất)\b.{0,20}\b(khách hàng)\b", re.I),
)


@dataclass(frozen=True)
class TextToSQLResponse:
    status: Literal["answered", "clarify", "refused", "rejected", "unavailable", "failed"]
    message: str
    result: QueryResult | None = None
    sql: str | None = None
    template_id: str | None = None


def _contains_sensitive_request(question: str) -> bool:
    return (
        any(
            not _NEGATION_BEFORE_FIELD_PATTERN.search(question[: match.start()])
            for match in _SENSITIVE_TERM_PATTERN.finditer(question)
        )
        or bool(_EMAIL_PATTERN.search(question))
        or bool(_PHONE_PATTERN.search(question))
        or bool(_CUSTOMER_ID_PATTERN.search(question))
        or bool(_LONG_NUMBER_PATTERN.search(question))
        or any(
            not _NEGATION_BEFORE_FIELD_PATTERN.search(question[: match.start()])
            for pattern in _INDIVIDUAL_LIST_PATTERNS
            for match in pattern.finditer(question)
        )
    )


def _sanitize_negated_sensitive_terms(question: str) -> str:
    """Omit restricted field names when the user explicitly excludes them."""
    pieces: list[str] = []
    cursor = 0
    for match in _SENSITIVE_TERM_PATTERN.finditer(question):
        prefix = question[: match.start()]
        if not _NEGATION_BEFORE_FIELD_PATTERN.search(prefix):
            continue
        pieces.extend((question[cursor : match.start()], "[restricted field omitted]"))
        cursor = match.end()
    if cursor == 0:
        return question
    pieces.append(question[cursor:])
    return "".join(pieces)


def _question_language(question: str) -> Literal["vi", "en"]:
    vietnamese_chars = "đĐ"
    if any(char in vietnamese_chars or "\u1ea0" <= char <= "\u1ef9" for char in question):
        return "vi"
    normalized = question.casefold()
    if any(
        term in normalized
        for term in (
            "doanh thu", "khách hàng", "khach hang", "sản phẩm", "san pham",
            "lợi nhuận", "loi nhuan", "bao nhiêu", "bao nhieu",
        )
    ):
        return "vi"
    return "en"


def _model_context(
    config: CatalogConfig,
    role_name: str,
    templates: tuple[TemplateInfo, ...],
) -> dict[str, Any]:
    role = config.policy.roles.get(role_name)
    if role is None:
        raise ValueError("The configured Text-to-SQL role does not exist.")

    models: list[dict[str, Any]] = []
    for relation in sorted(role.allowed_relations):
        model = config.catalog.models_by_relation.get(relation.casefold())
        if model is None:
            continue
        models.append(_model_payload(model))

    metrics = {
        name: {
            key: value
            for key, value in specification.items()
            if key in {"synonyms", "meaning", "caveat", "aggregation"}
        }
        for name, specification in config.catalog.metrics.items()
    }
    template_payload = []
    for template in templates:
        restriction = role.restricted_relations.get(template.relation.casefold())
        if restriction is None or template.template_id not in restriction.permitted_template_ids:
            continue
        template_payload.append(
            {
                "template_id": template.template_id,
                "output_columns": list(template.output_columns),
                "permitted_result": template.permitted_result,
                "forbidden_result": template.forbidden_result,
            }
        )
    return {
        "dialect": config.catalog.dialect,
        "dataset": config.catalog.dataset,
        "allowed_models": models,
        "metric_contract": metrics,
        "approved_aggregate_templates": template_payload,
        "language_rules": config.catalog.language,
        "query_policy": {
            "allowed_schema": config.policy.allowed_schema,
            "single_select_only": True,
            "joins_ctes_subqueries_select_star": False,
            "max_result_rows": role.max_result_rows,
            "default_result_rows": role.default_result_rows,
            "demographic_min_group_size": role.demographic_min_group_size,
            "customer_level_output": role.customer_level_output,
        },
    }


def _model_payload(model: ModelSpec) -> dict[str, Any]:
    return {
        "relation": model.relation,
        "description": model.description,
        "grain": model.grain,
        "dimensions": list(model.dimensions),
        "columns": [
            {"name": column.name, "type": column.data_type, "meaning": column.meaning}
            for column in model.columns.values()
            if column.name not in model.restricted_columns
        ],
        "caveats": list(model.caveats),
    }


def build_generation_payload(
    question: str,
    config: CatalogConfig | None = None,
    *,
    templates: tuple[TemplateInfo, ...] | None = None,
) -> tuple[str, str]:
    """Return system instructions and JSON context, without contacting Gemini."""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Question must be a non-empty string.")
    if len(question) > MAX_QUESTION_LENGTH:
        raise ValueError(f"Question must be at most {MAX_QUESTION_LENGTH} characters.")

    active_config = config or load_config()
    role_name = active_config.policy.default_role
    if templates is None:
        role = active_config.policy.roles[role_name]
        templates = tuple(
            TemplateInfo(
                template_id=template.template_id,
                relation=template.relation,
                output_columns=template.output_columns,
                permitted_result=template.permitted_result,
                forbidden_result=template.forbidden_result,
            )
            for template in active_config.policy.templates.values()
            if (restriction := role.restricted_relations.get(template.relation.casefold()))
            and template.template_id in restriction.permitted_template_ids
        )
    context = _model_context(active_config, role_name, templates)
    payload = json.dumps(
        {
            "context": context,
            "user_question_untrusted": _sanitize_negated_sensitive_terms(question),
        },
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )
    return SYSTEM_INSTRUCTION, payload


class NaturalLanguageQueryService:
    """Generate, validate, and locally execute one Text-to-SQL request.

    Only the question and allowlisted semantic metadata are sent to Gemini.
    Query results and warehouse rows remain local. The role is resolved from
    trusted local policy and is never accepted from the natural-language input.
    """

    def __init__(
        self,
        *,
        database_path: str | Path | None = None,
        config: CatalogConfig | None = None,
        generator: GeminiDecisionGenerator | None = None,
        executor: DuckDBExecutor | None = None,
    ) -> None:
        self._config = config or load_config()
        self._role = self._config.policy.default_role
        self._generator = generator or GeminiDecisionGenerator(GeminiSettings.from_env())
        self._database_path = database_path
        self._executor = executor
        self._templates = QueryService(database_path=database_path, config=self._config)

    def prompt_only(self, question: str) -> tuple[str, str]:
        """Build the exact prompt locally for review; no API call is made."""
        approved_templates = self._templates.list_approved_templates(role=self._role)
        return build_generation_payload(
            question,
            self._config,
            templates=approved_templates,
        )

    @staticmethod
    def _answer_message(
        result: QueryResult,
        template_id: str | None,
        language: Literal["vi", "en"],
    ) -> str:
        notes = [
            "Kết quả đã được truy vấn read-only sau khi kiểm tra policy."
            if language == "vi"
            else "The query ran read-only after policy validation."
        ]
        columns = {column.casefold() for column in result.columns}
        if "total_sales" in columns:
            notes.append(
                "total_sales là tổng sales theo đơn vị nguồn; currency và gross/net chưa được xác nhận."
                if language == "vi"
                else "total_sales is summed source sales in source units; currency and gross/net semantics are unconfirmed."
            )
        if result.relation.casefold() == "analytics_gold.mart_category_sales_mix_by_segment":
            notes.append(
                "Đây là cơ cấu doanh số theo category, không phải sản phẩm thường được mua cùng nhau hay bằng chứng cross-sell."
                if language == "vi"
                else "This is category sales mix, not products commonly bought together or evidence of cross-sell impact."
            )
        if (
            result.relation.casefold() == "analytics_gold.mart_market_basket_associations"
            and result.row_count == 0
        ):
            notes.append(
                "Không có cặp sản phẩm nào đạt support tối thiểu 0,5% trong mart hiện tại."
                if language == "vi"
                else "No product pairs meet the current 0.5% support threshold in this mart."
            )
        if template_id in {"q08_vip_risk_summary", "q14_rfm_population_summary"}:
            notes.append(
                "RFM là snapshot lịch sử 2024-01-01; churn_risk_90d là heuristic không hoạt động 90 ngày, không phải nhãn churn hiện tại."
                if language == "vi"
                else "RFM is a historical 2024-01-01 snapshot; churn_risk_90d is a 90-day inactivity heuristic, not a current churn label."
            )
        if template_id == "q13_region_behavior_summary":
            notes.append(
                "Region orphan là giao dịch không khớp dimension region; không gán vào region hay market đã biết."
                if language == "vi"
                else "Orphan-region activity did not match the region dimension and is not assigned to a known region or market."
            )
        return " ".join(notes)

    def ask(self, question: str) -> TextToSQLResponse:
        if not isinstance(question, str) or not question.strip():
            return TextToSQLResponse("clarify", "Hãy nhập một câu hỏi phân tích.")
        language = _question_language(question)
        if len(question) > MAX_QUESTION_LENGTH:
            return TextToSQLResponse(
                "clarify",
                (
                    f"Câu hỏi quá dài; giới hạn hiện tại là {MAX_QUESTION_LENGTH} ký tự."
                    if language == "vi"
                    else f"The question is too long; the current limit is {MAX_QUESTION_LENGTH} characters."
                ),
            )
        if _contains_sensitive_request(question):
            return TextToSQLResponse(
                "refused",
                (
                    "Yêu cầu có vẻ đòi hỏi dữ liệu nhận diện cá nhân hoặc từng khách hàng; hệ thống chỉ hỗ trợ kết quả tổng hợp."
                    if language == "vi"
                    else "This request appears to ask for personal identifiers or individual customer records; only aggregate results are available."
                ),
            )
        if _DESTRUCTIVE_INTENT_PATTERN.search(question):
            return TextToSQLResponse(
                "refused",
                (
                    "Chỉ hỗ trợ truy vấn phân tích read-only; yêu cầu thay đổi hoặc xóa dữ liệu bị từ chối."
                    if language == "vi"
                    else "Only read-only analytical queries are supported; requests to change or delete data are refused."
                ),
            )
        if any(pattern.search(question) for pattern in _CURRENT_PERIOD_PATTERNS):
            return TextToSQLResponse(
                "clarify",
                (
                    "Kho dữ liệu hiện có kết thúc ngày 2023-12-31 nên không xác định được tháng/năm hiện tại. "
                    "Bạn muốn xem tháng hoặc năm cụ thể nào trong giai đoạn 2020–2023?"
                    if language == "vi"
                    else "The warehouse ends on 2023-12-31, so it cannot identify the current month or year. "
                    "Which specific month or year from 2020–2023 should I use?"
                ),
            )
        if (
            _AMBIGUOUS_PROFIT_PATTERN.search(question)
            and not re.search(r"\b(?:total_profit|profit_margin|profit margin)\b", question, re.IGNORECASE)
        ):
            return TextToSQLResponse(
                "clarify",
                (
                    "Bạn muốn xếp hạng theo tổng lợi nhuận (total_profit) hay tỷ suất lợi nhuận (profit_margin)?"
                    if language == "vi"
                    else "Should I rank by total profit (total_profit) or profit margin (profit_margin)?"
                ),
            )
        if any(pattern.search(question) for pattern in _DISCOUNT_CAUSALITY_PATTERNS):
            return TextToSQLResponse(
                "clarify",
                (
                    "Dữ liệu chỉ hỗ trợ so sánh mô tả giữa discount và profit; không chứng minh discount là nguyên nhân. Bạn muốn xem profit theo discount band nào?"
                    if language == "vi"
                    else "The data supports descriptive comparisons between discount and profit; it does not establish that discount caused the change. Would you like to compare profit by discount band?"
                ),
            )

        try:
            _, payload = self.prompt_only(question)
            decision: ModelDecision = self._generator.generate(user_payload=payload)
        except GeminiConfigurationError as exc:
            return TextToSQLResponse("unavailable", str(exc))
        except GeminiGenerationError as exc:
            return TextToSQLResponse("unavailable", str(exc))
        except Exception:
            return TextToSQLResponse("unavailable", "Không thể chuẩn bị an toàn yêu cầu Gemini.")

        if decision.action == "clarify":
            return TextToSQLResponse("clarify", decision.message)
        if decision.action == "refuse":
            return TextToSQLResponse("refused", decision.message)
        if decision.action == "template":
            approved_ids = {
                template.template_id
                for template in self._templates.list_approved_templates(role=self._role)
            }
            if decision.template_id not in approved_ids:
                return TextToSQLResponse(
                    "rejected",
                    "Mô hình chọn một template không được policy hiện tại phê duyệt; không có truy vấn nào được chạy.",
                )
            try:
                result = self._templates.execute_template(decision.template_id, role=self._role)
            except QueryServiceError:
                return TextToSQLResponse("rejected", "Template không vượt qua policy; không có truy vấn nào được chạy.")
            except ExecutorError:
                return TextToSQLResponse("failed", "Warehouse không thể chạy template đã duyệt.")
            return TextToSQLResponse(
                "answered",
                self._answer_message(result, decision.template_id, language),
                result=result,
                template_id=decision.template_id,
            )

        try:
            validated_query = validate_sql(decision.sql, self._config, role=self._role)
        except SQLValidationError:
            return TextToSQLResponse(
                "rejected",
                "SQL do mô hình tạo không đáp ứng policy; không có truy vấn nào được chạy.",
            )
        try:
            result = self._get_executor().execute(validated_query)
        except ExecutorError:
            return TextToSQLResponse("failed", "Warehouse không thể chạy truy vấn đã được kiểm tra.")
        return TextToSQLResponse(
            "answered",
            self._answer_message(result, None, language),
            result=result,
            sql=validated_query.sql,
        )

    def close(self) -> None:
        self._generator.close()

    def _get_executor(self) -> DuckDBExecutor:
        if self._executor is None:
            self._executor = DuckDBExecutor(
                database_path=self._database_path,
                config=self._config,
            )
        return self._executor
