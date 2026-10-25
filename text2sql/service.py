"""Policy-backed query service for approved aggregate templates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from text2sql.catalog import CatalogConfig, RolePolicy, load_config
from text2sql.executor import DuckDBExecutor, QueryResult
from text2sql.validator import SQLValidationError, validate_sql


class QueryServiceError(RuntimeError):
    """Base class for query-service errors."""


class UnknownTemplateError(QueryServiceError):
    """Raised when the requested template is not present in policy."""


class TemplateAccessDeniedError(QueryServiceError):
    """Raised when the trusted role cannot use a configured template."""


@dataclass(frozen=True)
class TemplateInfo:
    """Safe template metadata; the SQL body is kept inside the service."""

    template_id: str
    relation: str
    output_columns: tuple[str, ...]
    permitted_result: str
    forbidden_result: str


class QueryService:
    """Run only aggregate templates approved by the access policy.

    ``role`` must come from trusted application configuration or authenticated
    identity. It must never be copied from a user's natural-language question.
    This service deliberately exposes no method for executing arbitrary SQL.
    """

    def __init__(
        self,
        database_path: str | Path | None = None,
        config: CatalogConfig | None = None,
    ) -> None:
        self._config = config or load_config()
        self._database_path = database_path
        self._executor: DuckDBExecutor | None = None

    def list_approved_templates(self, *, role: str | None = None) -> tuple[TemplateInfo, ...]:
        """List templates permitted to a trusted role without exposing SQL."""
        role_policy = self._resolve_role(role)
        visible: list[TemplateInfo] = []
        for template_id, template in self._config.policy.templates.items():
            restriction = role_policy.restricted_relations.get(template.relation.casefold())
            if restriction is None or template_id not in restriction.permitted_template_ids:
                continue
            visible.append(
                TemplateInfo(
                    template_id=template.template_id,
                    relation=template.relation,
                    output_columns=template.output_columns,
                    permitted_result=template.permitted_result,
                    forbidden_result=template.forbidden_result,
                )
            )
        return tuple(visible)

    def execute_template(
        self,
        template_id: str,
        *,
        role: str | None = None,
    ) -> QueryResult:
        """Validate and execute one policy-defined aggregate template."""
        if not isinstance(template_id, str) or not template_id.strip():
            raise UnknownTemplateError("A non-empty approved template_id is required.")

        role_policy = self._resolve_role(role)
        template = self._config.policy.templates.get(template_id)
        if template is None:
            raise UnknownTemplateError("The requested template is not configured.")

        restriction = role_policy.restricted_relations.get(template.relation.casefold())
        if restriction is None or template_id not in restriction.permitted_template_ids:
            raise TemplateAccessDeniedError(
                "The trusted role is not permitted to execute this template."
            )

        try:
            query = validate_sql(
                template.sql,
                self._config,
                role=role_policy.name,
                template_id=template.template_id,
            )
        except SQLValidationError:
            # A policy template that no longer validates must fail closed.
            raise QueryServiceError(
                "The configured template does not satisfy the current SQL policy."
            ) from None
        return self._get_executor().execute(query)

    def _resolve_role(self, role: str | None) -> RolePolicy:
        role_name = self._config.policy.default_role if role is None else role
        if not isinstance(role_name, str) or role_name not in self._config.policy.roles:
            raise TemplateAccessDeniedError("The trusted role is not configured.")
        return self._config.policy.roles[role_name]

    def _get_executor(self) -> DuckDBExecutor:
        if self._executor is None:
            self._executor = DuckDBExecutor(
                database_path=self._database_path,
                config=self._config,
            )
        return self._executor
