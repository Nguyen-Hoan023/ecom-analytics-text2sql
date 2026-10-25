"""Fail-closed SQLGlot validation for the Text-to-SQL query boundary."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

from text2sql.catalog import CatalogConfig, CatalogConfigError, load_config


class SQLValidationError(ValueError):
    """Raised when generated SQL does not satisfy the current access policy."""


@dataclass(frozen=True)
class ValidatedQuery:
    """Normalized SQL plus the constraints an executor must continue to enforce."""

    sql: str
    relation: str
    model_name: str
    output_columns: tuple[str, ...]
    max_result_rows: int
    default_result_rows: int
    role: str
    template_id: str | None = None
    requested_limit: int | None = None


_ALLOWED_EXPRESSION_TYPES = tuple(
    expression_type
    for name in (
        "Select",
        "From",
        "Table",
        "TableAlias",
        "Identifier",
        "Column",
        "Alias",
        "Literal",
        "Boolean",
        "Null",
        "Star",
        "Func",
        "DataType",
        "DataTypeParam",
        "Var",
        "Where",
        "Group",
        "Having",
        "Order",
        "Ordered",
        "Limit",
        "Distinct",
        "Paren",
        "Tuple",
        "And",
        "Or",
        "Not",
        "EQ",
        "NEQ",
        "GT",
        "GTE",
        "LT",
        "LTE",
        "Is",
        "Between",
        "In",
        "Like",
        "ILike",
        "Add",
        "Sub",
        "Mul",
        "Div",
        "Mod",
        "Neg",
        "Case",
        "If",
    )
    if isinstance((expression_type := getattr(exp, name, None)), type)
)

_NON_FUNCTION_EXPRESSION_TYPES = tuple(
    expression_type
    for name in (
        "And",
        "Or",
        "Not",
        "EQ",
        "NEQ",
        "GT",
        "GTE",
        "LT",
        "LTE",
        "Is",
        "Between",
        "In",
        "Like",
        "ILike",
        "Add",
        "Sub",
        "Mul",
        "Div",
        "Mod",
        "Neg",
    )
    if isinstance((expression_type := getattr(exp, name, None)), type)
)


def _parse_one_select(sql: str) -> exp.Select:
    if not isinstance(sql, str) or not sql.strip():
        raise SQLValidationError("SQL must be a non-empty string.")
    try:
        statements = [statement for statement in sqlglot.parse(sql, read="duckdb") if statement]
    except SqlglotError as exc:
        raise SQLValidationError(f"SQL could not be parsed as DuckDB SQL: {exc}") from exc

    if len(statements) != 1:
        raise SQLValidationError("Exactly one SQL statement is allowed.")
    statement = statements[0]
    if not isinstance(statement, exp.Select):
        raise SQLValidationError("Only a SELECT statement is allowed.")
    if not statement.expressions:
        raise SQLValidationError("SELECT must contain at least one output expression.")
    if len(list(statement.find_all(exp.Select))) != 1:
        raise SQLValidationError("Nested SELECT statements are not allowed.")
    if statement.args.get("with") is not None:
        raise SQLValidationError("CTEs are not allowed.")
    if statement.args.get("joins"):
        raise SQLValidationError("JOINs are not allowed.")
    return statement


def _validate_ast_nodes(statement: exp.Select, allowed_functions: Iterable[str]) -> None:
    allowed_function_names = {name.upper() for name in allowed_functions}
    for node in statement.walk():
        if not isinstance(node, _ALLOWED_EXPRESSION_TYPES):
            raise SQLValidationError(
                f"SQL contains a construct that is not allowed: {type(node).__name__}."
            )
        if isinstance(node, exp.Func) and not isinstance(
            node, (exp.Case, exp.If, *_NON_FUNCTION_EXPRESSION_TYPES)
        ):
            function_name = node.sql_name().upper()
            if type(node).__name__ == "Anonymous":
                function_name = str(node.name).upper()
            if function_name not in allowed_function_names:
                raise SQLValidationError(f"Function {function_name!r} is not allowed.")

    for star in statement.find_all(exp.Star):
        if not isinstance(star.parent, exp.Count):
            raise SQLValidationError("SELECT * is not allowed; COUNT(*) is allowed.")


def _extract_relation(statement: exp.Select, gold_schema: str) -> tuple[str, str | None]:
    tables = list(statement.find_all(exp.Table))
    if len(tables) != 1:
        raise SQLValidationError("The query must read from exactly one allowlisted Gold mart.")

    table = tables[0]
    if not isinstance(table.this, exp.Identifier):
        raise SQLValidationError("Table functions and computed table sources are not allowed.")
    if not table.db or table.db.casefold() != gold_schema.casefold():
        raise SQLValidationError(f"Tables must be fully qualified in schema {gold_schema!r}.")
    if table.catalog:
        raise SQLValidationError("Three-part and catalog-qualified table names are not allowed.")

    relation = f"{table.db}.{table.name}".casefold()
    alias: str | None = None
    table_alias = table.args.get("alias")
    if table_alias is not None:
        if table_alias.args.get("columns"):
            raise SQLValidationError("Column aliases on a table reference are not allowed.")
        alias_identifier = table_alias.args.get("this")
        if not isinstance(alias_identifier, exp.Identifier):
            raise SQLValidationError("The table alias is invalid.")
        alias = alias_identifier.name.casefold()
    return relation, alias


def _output_names(statement: exp.Select) -> tuple[str, ...]:
    names: list[str] = []
    for index, projection in enumerate(statement.expressions, start=1):
        if isinstance(projection, exp.Alias):
            name = projection.args["alias"].name
        elif isinstance(projection, exp.Column):
            name = projection.name
        else:
            name = projection.output_name or f"column_{index}"
        names.append(str(name).casefold())
    if len(set(names)) != len(names):
        raise SQLValidationError("Selected columns must have unique output names.")
    return tuple(names)


def _validate_columns(
    statement: exp.Select,
    *,
    relation: str,
    table_alias: str | None,
    column_names: set[str],
    restricted_columns: set[str],
    forbidden_output_columns: set[str],
    output_names: tuple[str, ...],
) -> None:
    allowed_qualifiers = {relation.rsplit(".", 1)[1]}
    if table_alias:
        allowed_qualifiers.add(table_alias)

    selected_expressions = statement.expressions
    selected_base_columns: set[str] = set()
    output_alias_names: set[str] = set()
    for projection in selected_expressions:
        if isinstance(projection, exp.Alias):
            output_alias_names.add(projection.args["alias"].name.casefold())
            expression = projection.this
        else:
            expression = projection
        if isinstance(expression, exp.Column):
            selected_base_columns.add(expression.name.casefold())

    for column in statement.find_all(exp.Column):
        name = column.name.casefold()
        if name == "*":
            continue
        if column.catalog or column.db:
            raise SQLValidationError("Column references cannot cross schemas or catalogs.")
        qualifier = column.table
        if qualifier and qualifier.casefold() not in allowed_qualifiers:
            raise SQLValidationError(f"Column qualifier {qualifier!r} does not match the source mart.")
        if name not in column_names and name not in output_alias_names:
            raise SQLValidationError(f"Column {column.name!r} is not in the selected mart catalog.")
        if name in restricted_columns:
            raise SQLValidationError(f"Column {column.name!r} is restricted by the catalog.")

    forbidden = forbidden_output_columns.union(restricted_columns)
    if set(output_names).intersection(forbidden):
        denied = sorted(set(output_names).intersection(forbidden))
        raise SQLValidationError(f"Forbidden output column name(s): {', '.join(denied)}.")
    if selected_base_columns.intersection(forbidden):
        denied = sorted(selected_base_columns.intersection(forbidden))
        raise SQLValidationError(f"Forbidden output column(s): {', '.join(denied)}.")


def _flatten_and(expression: exp.Expression) -> list[exp.Expression]:
    if isinstance(expression, exp.Paren):
        return _flatten_and(expression.this)
    if isinstance(expression, exp.And):
        return _flatten_and(expression.this) + _flatten_and(expression.expression)
    return [expression]


def _validate_demographic_query(
    statement: exp.Select,
    *,
    relation: str,
    role_min_group_size: int,
    guard: dict,
) -> None:
    if relation.casefold() != str(guard.get("relation", "")).casefold():
        return
    if not guard.get("require_simple_row_selection", False):
        raise SQLValidationError("The demographic disclosure guard is not safely configured.")

    allowed_projection_columns = {"gender", "occupation", str(guard["count_column"]).casefold()}
    for projection in statement.expressions:
        expression = projection.this if isinstance(projection, exp.Alias) else projection
        if not isinstance(expression, exp.Column) or expression.name.casefold() not in allowed_projection_columns:
            raise SQLValidationError(
                "Demographic mart access is limited to its existing grouped rows; "
                "select gender, occupation, or customer_count directly."
            )
    if statement.args.get("group") is not None or statement.args.get("having") is not None:
        raise SQLValidationError("Regrouping the demographic mart is not allowed in v1.")

    where = statement.args.get("where")
    if where is None:
        raise SQLValidationError(
            f"Demographic queries must filter customer_count >= {role_min_group_size}."
        )
    if any(isinstance(node, exp.Or) for node in where.walk()):
        raise SQLValidationError("OR is not allowed in the demographic minimum-size filter.")

    count_column = str(guard["count_column"]).casefold()
    threshold_found = False
    for conjunct in _flatten_and(where.this):
        if not isinstance(conjunct, exp.GTE) or not isinstance(conjunct.this, exp.Column):
            continue
        right = conjunct.expression
        if (
            conjunct.this.name.casefold() == count_column
            and isinstance(right, exp.Literal)
            and not right.is_string
        ):
            try:
                threshold_found = int(right.this) >= role_min_group_size
            except (TypeError, ValueError):
                threshold_found = False
            if threshold_found:
                break
    if not threshold_found:
        raise SQLValidationError(
            f"Demographic queries must include a conjunctive {count_column} >= "
            f"{role_min_group_size} predicate."
        )


def _validate_explicit_limit(statement: exp.Select, max_rows: int) -> int | None:
    limit = statement.args.get("limit")
    if limit is None:
        return None
    value = limit.args.get("expression")
    if not isinstance(value, exp.Literal) or value.is_string:
        raise SQLValidationError("LIMIT must be a non-negative integer literal.")
    try:
        requested = int(value.this)
    except (TypeError, ValueError) as exc:
        raise SQLValidationError("LIMIT must be a non-negative integer literal.") from exc
    if requested < 0:
        raise SQLValidationError("LIMIT must not be negative.")
    if requested > max_rows:
        raise SQLValidationError(f"LIMIT cannot exceed the role's hard cap of {max_rows} rows.")
    return requested


def _canonical(sql: str) -> str:
    try:
        statements = [statement for statement in sqlglot.parse(sql, read="duckdb") if statement]
    except SqlglotError as exc:
        raise SQLValidationError(f"Configured template SQL is invalid: {exc}") from exc
    if len(statements) != 1 or not isinstance(statements[0], exp.Select):
        raise SQLValidationError("Configured templates must each contain exactly one SELECT.")
    return statements[0].sql(dialect="duckdb", pretty=False)


def validate_sql(
    sql: str,
    config: CatalogConfig | None = None,
    *,
    role: str | None = None,
    template_id: str | None = None,
) -> ValidatedQuery:
    """Validate SQL before it is handed to an executor.

    The function does not connect to DuckDB or execute SQL. An executor must
    still open the database read-only and enforce the returned row cap and
    runtime/resource limits.
    """
    config = config or load_config()
    catalog = config.catalog
    policy = config.policy
    role_name = role or policy.default_role
    role_policy = policy.roles.get(role_name)
    if role_policy is None:
        raise SQLValidationError(f"Unknown or untrusted role {role_name!r}.")

    statement = _parse_one_select(sql)
    _validate_ast_nodes(statement, policy.sql_validation["allowed_functions"])
    relation, table_alias = _extract_relation(statement, catalog.gold_schema)

    model = catalog.models_by_relation.get(relation)
    if model is None:
        raise SQLValidationError(f"Relation {relation!r} is absent from the semantic catalog.")
    if relation in role_policy.allowed_relations:
        restriction = None
        if template_id is not None:
            raise SQLValidationError("template_id is only valid for restricted aggregate templates.")
    else:
        restriction = role_policy.restricted_relations.get(relation)
        if restriction is None:
            raise SQLValidationError(f"Relation {relation!r} is not allowlisted for role {role_name!r}.")
        if template_id is None:
            raise SQLValidationError(
                f"Relation {relation!r} is customer-level restricted; an approved template_id is required."
            )
        if template_id not in restriction.permitted_template_ids:
            raise SQLValidationError(
                f"Template {template_id!r} is not approved for relation {relation!r}."
            )
        template = policy.templates.get(template_id)
        if template is None or template.relation != relation:
            raise SQLValidationError("The requested template does not target this restricted relation.")
        if _canonical(sql) != _canonical(template.sql):
            raise SQLValidationError(
                f"SQL does not exactly match approved aggregate template {template_id!r}."
            )

    output_names = _output_names(statement)
    forbidden_output = (
        set(restriction.forbidden_output_columns) if restriction is not None else set()
    )
    _validate_columns(
        statement,
        relation=relation,
        table_alias=table_alias,
        column_names=set(model.columns),
        restricted_columns=set(model.restricted_columns),
        forbidden_output_columns=forbidden_output,
        output_names=output_names,
    )

    demographic_guard = policy.sql_validation.get("demographic_minimum_group_size", {})
    if not isinstance(demographic_guard, dict):
        raise CatalogConfigError("sql_validation.demographic_minimum_group_size must be a mapping.")
    _validate_demographic_query(
        statement,
        relation=relation,
        role_min_group_size=role_policy.demographic_min_group_size,
        guard=demographic_guard,
    )

    executor_cap = policy.duckdb_execution.get("output_rows_hard_cap")
    if isinstance(executor_cap, bool) or not isinstance(executor_cap, int) or executor_cap < 1:
        raise CatalogConfigError("duckdb_execution.output_rows_hard_cap must be a positive integer.")
    max_rows = min(role_policy.max_result_rows, executor_cap)
    requested_limit = _validate_explicit_limit(statement, max_rows)

    normalized_sql = statement.sql(dialect="duckdb", pretty=False)
    return ValidatedQuery(
        sql=normalized_sql,
        relation=relation,
        model_name=model.name,
        output_columns=output_names,
        max_result_rows=max_rows,
        default_result_rows=min(role_policy.default_result_rows, max_rows),
        role=role_name,
        template_id=template_id,
        requested_limit=requested_limit,
    )
