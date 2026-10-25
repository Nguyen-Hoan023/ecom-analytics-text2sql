"""Load and validate the semantic catalog and application access policy."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import sqlglot
from sqlglot import exp
import yaml


class CatalogConfigError(ValueError):
    """Raised when the semantic catalog or access policy is invalid."""


@dataclass(frozen=True)
class ColumnSpec:
    name: str
    data_type: str
    meaning: str


@dataclass(frozen=True)
class ModelSpec:
    name: str
    relation: str
    description: str
    grain: str
    access_class: str
    query_mode: str
    dimensions: tuple[str, ...]
    caveats: tuple[str, ...]
    columns: Mapping[str, ColumnSpec]
    restricted_columns: tuple[str, ...]


@dataclass(frozen=True)
class SemanticCatalog:
    version: int
    dialect: str
    gold_schema: str
    models_by_name: Mapping[str, ModelSpec]
    models_by_relation: Mapping[str, ModelSpec]
    metrics: Mapping[str, Any]
    language: Mapping[str, Any]
    dataset: Mapping[str, Any]
    status: str


@dataclass(frozen=True)
class RestrictedRelation:
    access: str
    permitted_template_ids: tuple[str, ...]
    forbidden_output_columns: tuple[str, ...]


@dataclass(frozen=True)
class AggregateTemplate:
    template_id: str
    relation: str
    sql: str
    output_columns: tuple[str, ...]
    permitted_result: str
    forbidden_result: str


@dataclass(frozen=True)
class RolePolicy:
    name: str
    allowed_relations: tuple[str, ...]
    restricted_relations: Mapping[str, RestrictedRelation]
    max_result_rows: int
    default_result_rows: int
    demographic_min_group_size: int
    customer_level_output: str


@dataclass(frozen=True)
class AccessPolicy:
    version: int
    dialect: str
    allowed_schema: str
    default_role: str
    allowed_relations: tuple[str, ...]
    restricted_relations: Mapping[str, RestrictedRelation]
    roles: Mapping[str, RolePolicy]
    templates: Mapping[str, AggregateTemplate]
    sql_validation: Mapping[str, Any]
    duckdb_execution: Mapping[str, Any]
    status: str


@dataclass(frozen=True)
class CatalogConfig:
    catalog: SemanticCatalog
    policy: AccessPolicy


def _default_path(filename: str) -> Path:
    return Path(__file__).resolve().parent / filename


def _read_yaml(path: str | Path, *, label: str) -> Mapping[str, Any]:
    source = Path(path)
    try:
        with source.open("r", encoding="utf-8") as file:
            document = yaml.safe_load(file)
    except (OSError, yaml.YAMLError) as exc:
        raise CatalogConfigError(f"Could not load {label} at {source}: {exc}") from exc

    if not isinstance(document, dict):
        raise CatalogConfigError(f"{label} must contain a YAML mapping at its root.")
    return document


def _required_string(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CatalogConfigError(f"{field} must be a non-empty string.")
    return value.strip()


def _required_positive_int(value: Any, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise CatalogConfigError(f"{field} must be a positive integer.")
    return value


def _resolve_reference(root: Mapping[str, Any], reference: str, *, field: str) -> Any:
    current: Any = root
    for key in reference.split("."):
        if not isinstance(current, Mapping) or key not in current:
            raise CatalogConfigError(f"{field} references missing policy path {reference!r}.")
        current = current[key]
    return current


def _resolve_role_value(
    root: Mapping[str, Any], value: Any, *, field: str
) -> Any:
    if isinstance(value, str):
        return _resolve_reference(root, value, field=field)
    return value


def _parse_restricted_relations(value: Any, *, field: str) -> dict[str, RestrictedRelation]:
    if not isinstance(value, Mapping):
        raise CatalogConfigError(f"{field} must resolve to a mapping.")

    parsed: dict[str, RestrictedRelation] = {}
    for relation, raw in value.items():
        relation_name = _required_string(relation, field=f"{field} relation").casefold()
        if relation_name in parsed:
            raise CatalogConfigError(f"Duplicate restricted relation {relation_name!r}.")
        if not isinstance(raw, Mapping):
            raise CatalogConfigError(f"{field}.{relation_name} must be a mapping.")

        access = _required_string(raw.get("access"), field=f"{field}.{relation_name}.access")
        permitted_ids = raw.get("permitted_template_ids")
        forbidden_columns = raw.get("forbidden_output_columns", [])
        if not isinstance(permitted_ids, list) or not permitted_ids:
            raise CatalogConfigError(
                f"{field}.{relation_name}.permitted_template_ids must be a non-empty list."
            )
        if not isinstance(forbidden_columns, list):
            raise CatalogConfigError(
                f"{field}.{relation_name}.forbidden_output_columns must be a list."
            )
        parsed[relation_name] = RestrictedRelation(
            access=access,
            permitted_template_ids=tuple(
                _required_string(item, field=f"{field}.{relation_name}.permitted_template_ids")
                for item in permitted_ids
            ),
            forbidden_output_columns=tuple(
                _required_string(item, field=f"{field}.{relation_name}.forbidden_output_columns")
                .casefold()
                for item in forbidden_columns
            ),
        )
    return parsed


def load_catalog(path: str | Path | None = None) -> SemanticCatalog:
    """Read catalog YAML and validate model, relation and column definitions."""
    source = path or _default_path("semantic_catalog.yml")
    raw = _read_yaml(source, label="semantic catalog")

    version = _required_positive_int(raw.get("catalog_version"), field="catalog_version")
    dialect = _required_string(raw.get("dialect"), field="dialect").casefold()
    gold_schema = _required_string(raw.get("gold_schema"), field="gold_schema")
    if dialect != "duckdb":
        raise CatalogConfigError("The semantic catalog dialect must be 'duckdb'.")

    raw_models = raw.get("models")
    if not isinstance(raw_models, list) or not raw_models:
        raise CatalogConfigError("models must be a non-empty list.")

    models_by_name: dict[str, ModelSpec] = {}
    models_by_relation: dict[str, ModelSpec] = {}
    for index, raw_model in enumerate(raw_models):
        field = f"models[{index}]"
        if not isinstance(raw_model, Mapping):
            raise CatalogConfigError(f"{field} must be a mapping.")

        name = _required_string(raw_model.get("name"), field=f"{field}.name")
        relation = _required_string(raw_model.get("relation"), field=f"{field}.relation")
        description = _required_string(raw_model.get("description"), field=f"{field}.description")
        grain = _required_string(raw_model.get("grain"), field=f"{field}.grain")
        access_class = _required_string(raw_model.get("access_class"), field=f"{field}.access_class")
        query_mode = _required_string(raw_model.get("query_mode"), field=f"{field}.query_mode")

        relation_parts = relation.split(".")
        if (
            len(relation_parts) != 2
            or relation_parts[0].casefold() != gold_schema.casefold()
            or relation_parts[1].casefold() != name.casefold()
        ):
            raise CatalogConfigError(
                f"{field}.relation must be {gold_schema}.{name}; got {relation!r}."
            )

        raw_columns = raw_model.get("columns")
        if not isinstance(raw_columns, list) or not raw_columns:
            raise CatalogConfigError(f"{field}.columns must be a non-empty list.")
        columns: dict[str, ColumnSpec] = {}
        for column_index, raw_column in enumerate(raw_columns):
            column_field = f"{field}.columns[{column_index}]"
            if not isinstance(raw_column, Mapping):
                raise CatalogConfigError(f"{column_field} must be a mapping.")
            column_name = _required_string(
                raw_column.get("name"), field=f"{column_field}.name"
            ).casefold()
            if column_name in columns:
                raise CatalogConfigError(f"Duplicate column {column_name!r} in {relation}.")
            columns[column_name] = ColumnSpec(
                name=column_name,
                data_type=_required_string(raw_column.get("type"), field=f"{column_field}.type"),
                meaning=_required_string(
                    raw_column.get("meaning"), field=f"{column_field}.meaning"
                ),
            )

        raw_restricted = raw_model.get("restricted_columns", [])
        if not isinstance(raw_restricted, list):
            raise CatalogConfigError(f"{field}.restricted_columns must be a list.")
        restricted_columns = tuple(
            _required_string(item, field=f"{field}.restricted_columns").casefold()
            for item in raw_restricted
        )
        if not set(restricted_columns).issubset(columns):
            raise CatalogConfigError(
                f"{field}.restricted_columns contains a field absent from its catalog columns."
            )

        raw_dimensions = raw_model.get("dimensions", [])
        if not isinstance(raw_dimensions, list):
            raise CatalogConfigError(f"{field}.dimensions must be a list.")
        dimensions = tuple(
            _required_string(item, field=f"{field}.dimensions").casefold()
            for item in raw_dimensions
        )
        if not set(dimensions).issubset(columns):
            raise CatalogConfigError(f"{field}.dimensions contains a field absent from its columns.")

        raw_caveats = raw_model.get("caveats", [])
        if isinstance(raw_caveats, str):
            raw_caveats = [raw_caveats]
        if not isinstance(raw_caveats, list):
            raise CatalogConfigError(f"{field}.caveats must be a string or list of strings.")
        caveats = tuple(
            _required_string(item, field=f"{field}.caveats") for item in raw_caveats
        )

        model = ModelSpec(
            name=name,
            relation=f"{gold_schema}.{name}",
            description=description,
            grain=grain,
            access_class=access_class,
            query_mode=query_mode,
            dimensions=dimensions,
            caveats=caveats,
            columns=columns,
            restricted_columns=restricted_columns,
        )
        name_key = name.casefold()
        relation_key = relation.casefold()
        if name_key in models_by_name or relation_key in models_by_relation:
            raise CatalogConfigError(f"Duplicate model or relation definition for {name!r}.")
        models_by_name[name_key] = model
        models_by_relation[relation_key] = model

    return SemanticCatalog(
        version=version,
        dialect=dialect,
        gold_schema=gold_schema,
        models_by_name=models_by_name,
        models_by_relation=models_by_relation,
        metrics=raw.get("metrics", {}),
        language=raw.get("language", {}),
        dataset=raw.get("dataset", {}),
        status=str(raw.get("status", "unknown")),
    )


def load_policy(path: str | Path | None = None) -> AccessPolicy:
    """Read access-policy YAML and verify all relation and template references."""
    source = path or _default_path("access_policy.yml")
    raw = _read_yaml(source, label="access policy")

    version = _required_positive_int(raw.get("policy_version"), field="policy_version")
    dialect = _required_string(raw.get("dialect"), field="policy dialect").casefold()
    if dialect != "duckdb":
        raise CatalogConfigError("The access policy dialect must be 'duckdb'.")

    data_access = raw.get("data_access")
    if not isinstance(data_access, Mapping):
        raise CatalogConfigError("data_access must be a mapping.")
    allowed_schema = _required_string(
        data_access.get("allowed_schema"), field="data_access.allowed_schema"
    )
    allowed_relations = data_access.get("allowed_relations")
    if not isinstance(allowed_relations, list):
        raise CatalogConfigError("data_access.allowed_relations must be a list.")
    normalized_allowed = tuple(
        _required_string(item, field="data_access.allowed_relations").casefold()
        for item in allowed_relations
    )
    if len(set(normalized_allowed)) != len(normalized_allowed):
        raise CatalogConfigError("data_access.allowed_relations contains duplicates.")

    restricted = _parse_restricted_relations(
        data_access.get("restricted_relations"), field="data_access.restricted_relations"
    )
    if set(normalized_allowed).intersection(relation.casefold() for relation in restricted):
        raise CatalogConfigError("A relation cannot be both directly allowed and restricted.")

    raw_templates = raw.get("approved_aggregate_templates")
    if not isinstance(raw_templates, Mapping):
        raise CatalogConfigError("approved_aggregate_templates must be a mapping.")
    templates: dict[str, AggregateTemplate] = {}
    for template_id, raw_template in raw_templates.items():
        template_key = _required_string(template_id, field="template id")
        if not isinstance(raw_template, Mapping):
            raise CatalogConfigError(f"Template {template_key!r} must be a mapping.")
        template_sql = _required_string(
            raw_template.get("sql"), field=f"template {template_key}.sql"
        )
        raw_output_columns = raw_template.get("output_columns")
        if not isinstance(raw_output_columns, list) or not raw_output_columns:
            raise CatalogConfigError(
                f"Template {template_key!r} output_columns must be a non-empty list."
            )
        output_columns = tuple(
            _required_string(item, field=f"template {template_key}.output_columns").casefold()
            for item in raw_output_columns
        )
        if len(set(output_columns)) != len(output_columns):
            raise CatalogConfigError(
                f"Template {template_key!r} output_columns contains duplicates."
            )
        try:
            parsed_statements = [
                statement for statement in sqlglot.parse(template_sql, read=dialect) if statement
            ]
        except sqlglot.errors.SqlglotError as exc:
            raise CatalogConfigError(
                f"Template {template_key!r} SQL could not be parsed ({type(exc).__name__})."
            ) from None
        if len(parsed_statements) != 1:
            raise CatalogConfigError(
                f"Template {template_key!r} must contain exactly one SQL statement."
            )
        parsed_sql = parsed_statements[0]
        if not isinstance(parsed_sql, exp.Select):
            raise CatalogConfigError(f"Template {template_key!r} must be a SELECT statement.")
        parsed_output_columns = tuple(
            str(projection.alias_or_name).casefold() for projection in parsed_sql.expressions
        )
        if parsed_output_columns != output_columns:
            raise CatalogConfigError(
                f"Template {template_key!r} output_columns do not match its SQL projection."
            )
        templates[template_key] = AggregateTemplate(
            template_id=template_key,
            relation=_required_string(
                raw_template.get("relation"), field=f"template {template_key}.relation"
            ).casefold(),
            sql=template_sql,
            output_columns=output_columns,
            permitted_result=_required_string(
                raw_template.get("permitted_result"),
                field=f"template {template_key}.permitted_result",
            ),
            forbidden_result=_required_string(
                raw_template.get("forbidden_result"),
                field=f"template {template_key}.forbidden_result",
            ),
        )

    for relation, restriction in restricted.items():
        if restriction.access != "approved_aggregate_template_only":
            raise CatalogConfigError(
                f"Restricted relation {relation!r} must use approved_aggregate_template_only."
            )
        for template_id in restriction.permitted_template_ids:
            template = templates.get(template_id)
            if template is None:
                raise CatalogConfigError(
                    f"Restricted relation {relation!r} references missing template {template_id!r}."
                )
            if template.relation != relation.casefold():
                raise CatalogConfigError(
                    f"Template {template_id!r} points to {template.relation!r}, not {relation!r}."
                )

    roles_raw = raw.get("roles")
    if not isinstance(roles_raw, Mapping) or not roles_raw:
        raise CatalogConfigError("roles must be a non-empty mapping.")
    roles: dict[str, RolePolicy] = {}
    for role_name, role_raw in roles_raw.items():
        role_key = _required_string(role_name, field="role name")
        if not isinstance(role_raw, Mapping):
            raise CatalogConfigError(f"Role {role_key!r} must be a mapping.")
        resolved_allowed = _resolve_role_value(
            raw,
            role_raw.get("allowed_relations_ref", role_raw.get("allowed_relations")),
            field=f"role {role_key}.allowed_relations",
        )
        resolved_restricted = _resolve_role_value(
            raw,
            role_raw.get("restricted_relations_ref", role_raw.get("restricted_relations")),
            field=f"role {role_key}.restricted_relations",
        )
        if not isinstance(resolved_allowed, list):
            raise CatalogConfigError(f"Role {role_key!r} allowed relations must be a list.")
        role_allowed = tuple(
            _required_string(item, field=f"role {role_key}.allowed_relations").casefold()
            for item in resolved_allowed
        )
        if len(set(role_allowed)) != len(role_allowed):
            raise CatalogConfigError(f"Role {role_key!r} allowed relations contain duplicates.")
        role_restricted = _parse_restricted_relations(
            resolved_restricted, field=f"role {role_key}.restricted_relations"
        )
        if set(role_allowed).intersection(relation.casefold() for relation in role_restricted):
            raise CatalogConfigError(
                f"Role {role_key!r} has relations that are both allowed and restricted."
            )

        max_rows = _required_positive_int(
            role_raw.get("max_result_rows"), field=f"role {role_key}.max_result_rows"
        )
        default_rows = _required_positive_int(
            role_raw.get("default_result_rows"), field=f"role {role_key}.default_result_rows"
        )
        if default_rows > max_rows:
            raise CatalogConfigError(
                f"Role {role_key!r} default_result_rows cannot exceed max_result_rows."
            )
        min_group_size = _required_positive_int(
            role_raw.get("demographic_min_group_size"),
            field=f"role {role_key}.demographic_min_group_size",
        )
        roles[role_key] = RolePolicy(
            name=role_key,
            allowed_relations=role_allowed,
            restricted_relations=role_restricted,
            max_result_rows=max_rows,
            default_result_rows=default_rows,
            demographic_min_group_size=min_group_size,
            customer_level_output=_required_string(
                role_raw.get("customer_level_output"),
                field=f"role {role_key}.customer_level_output",
            ),
        )

    default_role = _required_string(
        raw.get("identity", {}).get("default_role") if isinstance(raw.get("identity"), Mapping) else None,
        field="identity.default_role",
    )
    if default_role not in roles:
        raise CatalogConfigError(f"Default role {default_role!r} is not defined in roles.")

    sql_validation = raw.get("sql_validation")
    if not isinstance(sql_validation, Mapping):
        raise CatalogConfigError("sql_validation must be a mapping.")
    required_flags = {
        "allowed_root_statement": "SELECT",
        "allow_single_statement_only": True,
        "allow_ctes": False,
        "allow_joins": False,
        "allow_select_star": False,
        "allow_table_functions": False,
        "allow_external_file_or_network_access": False,
        "allow_user_defined_or_extension_functions": False,
        "require_every_base_relation_in_allowlist": True,
        "require_every_column_in_catalog": True,
        "reject_on_parse_or_validation_error": True,
    }
    for field, expected in required_flags.items():
        if sql_validation.get(field) != expected:
            raise CatalogConfigError(
                f"sql_validation.{field} must be {expected!r} for the v1 validator."
            )
    functions = sql_validation.get("allowed_functions")
    if not isinstance(functions, list) or not functions:
        raise CatalogConfigError("sql_validation.allowed_functions must be a non-empty list.")
    allowed_functions = tuple(
        _required_string(item, field="sql_validation.allowed_functions").upper()
        for item in functions
    )
    if len(set(allowed_functions)) != len(allowed_functions):
        raise CatalogConfigError("sql_validation.allowed_functions contains duplicates.")

    duckdb_execution = raw.get("duckdb_execution")
    if not isinstance(duckdb_execution, Mapping):
        raise CatalogConfigError("duckdb_execution must be a mapping.")

    return AccessPolicy(
        version=version,
        dialect=dialect,
        allowed_schema=allowed_schema,
        default_role=default_role,
        allowed_relations=normalized_allowed,
        restricted_relations=restricted,
        roles=roles,
        templates=templates,
        sql_validation={**sql_validation, "allowed_functions": allowed_functions},
        duckdb_execution=duckdb_execution,
        status=str(raw.get("status", "unknown")),
    )


def load_config(
    catalog_path: str | Path | None = None,
    policy_path: str | Path | None = None,
) -> CatalogConfig:
    """Load both YAML contracts and validate that their model allowlists agree."""
    catalog = load_catalog(catalog_path)
    policy = load_policy(policy_path)

    catalog_relations = set(catalog.models_by_relation)
    if policy.allowed_schema.casefold() != catalog.gold_schema.casefold():
        raise CatalogConfigError(
            "data_access.allowed_schema must match semantic_catalog.gold_schema."
        )
    policy_relations = set(policy.allowed_relations).union(
        relation.casefold() for relation in policy.restricted_relations
    )
    if catalog_relations != policy_relations:
        missing_policy = sorted(catalog_relations - policy_relations)
        unknown_policy = sorted(policy_relations - catalog_relations)
        raise CatalogConfigError(
            "Catalog and policy relation sets differ; "
            f"missing from policy={missing_policy}, unknown in policy={unknown_policy}."
        )

    for relation in policy.allowed_relations:
        if not relation.startswith(f"{catalog.gold_schema.casefold()}."):
            raise CatalogConfigError(
                f"Direct allowlist relation {relation!r} is outside the Gold schema."
            )
        model = catalog.models_by_relation[relation]
        if model.query_mode != "direct_select" or model.access_class == "customer_level_restricted":
            raise CatalogConfigError(
                f"Direct allowlist relation {relation!r} is not marked direct_select."
            )
    for relation, restriction in policy.restricted_relations.items():
        relation_key = relation.casefold()
        if not relation_key.startswith(f"{catalog.gold_schema.casefold()}."):
            raise CatalogConfigError(
                f"Restricted relation {relation!r} is outside the Gold schema."
            )
        model = catalog.models_by_relation[relation_key]
        if (
            model.query_mode != "approved_aggregate_templates_only"
            or model.access_class != "customer_level_restricted"
        ):
            raise CatalogConfigError(
                f"Restricted relation {relation!r} is not marked customer-level template-only."
            )
        if not set(restriction.forbidden_output_columns).issubset(model.columns):
            raise CatalogConfigError(
                f"Policy forbidden output columns for {relation!r} are absent from the catalog."
            )

    for role in policy.roles.values():
        role_relations = set(role.allowed_relations).union(
            relation.casefold() for relation in role.restricted_relations
        )
        if not role_relations.issubset(catalog_relations):
            raise CatalogConfigError(f"Role {role.name!r} references a relation outside the catalog.")
        if set(role.allowed_relations) != set(policy.allowed_relations):
            raise CatalogConfigError(
                f"Role {role.name!r} must resolve to the configured global direct allowlist."
            )
        if set(role.restricted_relations) != set(policy.restricted_relations):
            raise CatalogConfigError(
                f"Role {role.name!r} must resolve to the configured restricted relations."
            )

    for template_id, template in policy.templates.items():
        if template.relation not in policy.restricted_relations:
            raise CatalogConfigError(
                f"Template {template_id!r} must target a restricted relation."
            )

    demographic_guard = policy.sql_validation.get("demographic_minimum_group_size")
    if not isinstance(demographic_guard, Mapping):
        raise CatalogConfigError(
            "sql_validation.demographic_minimum_group_size must be a mapping."
        )
    demographic_relation = _required_string(
        demographic_guard.get("relation"),
        field="sql_validation.demographic_minimum_group_size.relation",
    ).casefold()
    demographic_column = _required_string(
        demographic_guard.get("count_column"),
        field="sql_validation.demographic_minimum_group_size.count_column",
    ).casefold()
    demographic_model = catalog.models_by_relation.get(demographic_relation)
    if (
        demographic_model is None
        or demographic_relation not in policy.allowed_relations
        or demographic_column not in demographic_model.columns
        or demographic_guard.get("required_predicate") != ">="
        or demographic_guard.get("require_simple_row_selection") is not True
    ):
        raise CatalogConfigError(
            "The demographic minimum-size guard must target an allowlisted mart, "
            "a known count column, and require a simple >= predicate."
        )

    return CatalogConfig(catalog=catalog, policy=policy)
