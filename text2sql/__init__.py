"""Guarded Text-to-SQL building blocks for the Xom E-Com analytics project."""

from text2sql.catalog import (
    AccessPolicy,
    CatalogConfig,
    CatalogConfigError,
    SemanticCatalog,
    load_catalog,
    load_config,
    load_policy,
)
from text2sql.executor import (
    DuckDBExecutor,
    ExecutorError,
    InvalidValidatedQueryError,
    QueryExecutionError,
    QueryResult,
    QueryTimeoutError,
)
from text2sql.gemini import (
    GeminiConfigurationError,
    GeminiDecisionGenerator,
    GeminiGenerationError,
    GeminiSettings,
    ModelDecision,
)
from text2sql.nl_service import NaturalLanguageQueryService, TextToSQLResponse, build_generation_payload
from text2sql.service import (
    QueryService,
    QueryServiceError,
    TemplateAccessDeniedError,
    TemplateInfo,
    UnknownTemplateError,
)
from text2sql.validator import SQLValidationError, ValidatedQuery, validate_sql

__all__ = [
    "AccessPolicy",
    "CatalogConfig",
    "CatalogConfigError",
    "DuckDBExecutor",
    "ExecutorError",
    "GeminiConfigurationError",
    "GeminiDecisionGenerator",
    "GeminiGenerationError",
    "GeminiSettings",
    "InvalidValidatedQueryError",
    "QueryExecutionError",
    "QueryResult",
    "QueryService",
    "QueryServiceError",
    "QueryTimeoutError",
    "NaturalLanguageQueryService",
    "ModelDecision",
    "SQLValidationError",
    "SemanticCatalog",
    "TemplateAccessDeniedError",
    "TemplateInfo",
    "TextToSQLResponse",
    "UnknownTemplateError",
    "ValidatedQuery",
    "load_catalog",
    "load_config",
    "load_policy",
    "validate_sql",
    "build_generation_payload",
]
