from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True, slots=True)
class CalculatedColumnOverride:
    table: str
    name: str
    dax: str
    data_type: str
    format_string: str


@dataclass(frozen=True, slots=True)
class CalculatedTableColumn:
    name: str
    data_type: str
    format_string: str


@dataclass(frozen=True, slots=True)
class CalculatedTableOverride:
    name: str
    dax: str
    columns: list[CalculatedTableColumn]


@dataclass(frozen=True, slots=True)
class RelationshipOverride:
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    cross_filtering_behavior: str
    from_cardinality: str = "many"
    to_cardinality: str = "one"
    security_filtering_behavior: str = "oneDirection"


@dataclass(frozen=True, slots=True)
class TableSourceOverride:
    table: str
    mode: str
    m: str


@dataclass(frozen=True, slots=True)
class MParameterOverride:
    name: str
    value: str
    data_type: str


@dataclass(frozen=True, slots=True)
class RoleOverride:
    name: str
    filters: list[tuple[str, str]]


@dataclass(frozen=True, slots=True)
class ParameterTableOverride:
    name: str
    data_type: str
    values: list[str]


@dataclass(frozen=True, slots=True)
class ModelOverrides:
    calculated_columns: list[CalculatedColumnOverride]
    calculated_tables: list[CalculatedTableOverride]
    relationships: list[RelationshipOverride]
    table_sources: list[TableSourceOverride] = field(default_factory=list)
    m_parameters: list[MParameterOverride] = field(default_factory=list)
    roles: list[RoleOverride] = field(default_factory=list)
    parameter_tables: list[ParameterTableOverride] = field(default_factory=list)
    ignored_parameters: list[str] = field(default_factory=list)
    ignored_calculations: list[str] = field(default_factory=list)
    ignored_relationships: list[tuple[str, str, str, str]] = field(default_factory=list)


def _mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValueError(f"{context} must be a YAML mapping with string keys")
    return value


def _required_string(
    mapping: dict[str, object], key: str, context: str
) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{context} needs a non-empty {key!r} string")
    return value.strip()


def _format_string(mapping: dict[str, object], context: str) -> str:
    value = mapping.get("formatString", "")
    if not isinstance(value, str):
        raise ValueError(f"{context} formatString must be a string")
    return value


def _field_reference(value: str, context: str) -> tuple[str, str]:
    table, separator, column = value.rpartition(".")
    if not separator or not table.strip() or not column.strip():
        raise ValueError(f"{context} must use the 'Table.Column' form")
    return table.strip(), column.strip()


def load_model_overrides(overrides_dir: Path | None) -> ModelOverrides:
    empty = ModelOverrides([], [], [])
    if overrides_dir is None:
        return empty
    path = overrides_dir / "model.yml"
    if not path.exists():
        return empty
    loaded = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), str(path))
    unknown = set(loaded) - {
        "calculated_columns",
        "calculated_tables",
        "relationships",
        "table_sources",
        "m_parameters",
        "roles",
        "parameter_tables",
        "ignored_parameters",
        "ignored_calculations",
        "ignored_relationships",
    }
    if unknown:
        raise ValueError(f"Unknown keys in {path}: {', '.join(sorted(unknown))}")

    raw_columns = loaded.get("calculated_columns", [])
    if not isinstance(raw_columns, list):
        raise ValueError(f"{path} calculated_columns must be a list")
    calculated_columns: list[CalculatedColumnOverride] = []
    for index, raw in enumerate(raw_columns):
        context = f"{path} calculated_columns[{index}]"
        definition = _mapping(raw, context)
        unknown = set(definition) - {"table", "name", "dax", "dataType", "formatString"}
        if unknown:
            raise ValueError(f"Unknown keys in {context}: {', '.join(sorted(unknown))}")
        calculated_columns.append(
            CalculatedColumnOverride(
                table=_required_string(definition, "table", context),
                name=_required_string(definition, "name", context),
                dax=_required_string(definition, "dax", context),
                data_type=_required_string(definition, "dataType", context),
                format_string=_format_string(definition, context),
            )
        )

    raw_tables = loaded.get("calculated_tables", [])
    if not isinstance(raw_tables, list):
        raise ValueError(f"{path} calculated_tables must be a list")
    calculated_tables: list[CalculatedTableOverride] = []
    for index, raw in enumerate(raw_tables):
        context = f"{path} calculated_tables[{index}]"
        definition = _mapping(raw, context)
        unknown = set(definition) - {"name", "dax", "columns"}
        if unknown:
            raise ValueError(f"Unknown keys in {context}: {', '.join(sorted(unknown))}")
        raw_table_columns = definition.get("columns")
        if not isinstance(raw_table_columns, list) or not raw_table_columns:
            raise ValueError(f"{context} columns must be a non-empty list")
        table_columns: list[CalculatedTableColumn] = []
        for column_index, raw_column in enumerate(raw_table_columns):
            column_context = f"{context} columns[{column_index}]"
            column = _mapping(raw_column, column_context)
            unknown = set(column) - {"name", "dataType", "formatString"}
            if unknown:
                raise ValueError(
                    f"Unknown keys in {column_context}: {', '.join(sorted(unknown))}"
                )
            table_columns.append(
                CalculatedTableColumn(
                    name=_required_string(column, "name", column_context),
                    data_type=_required_string(column, "dataType", column_context),
                    format_string=_format_string(column, column_context),
                )
            )
        calculated_tables.append(
            CalculatedTableOverride(
                name=_required_string(definition, "name", context),
                dax=_required_string(definition, "dax", context),
                columns=table_columns,
            )
        )

    raw_relationships = loaded.get("relationships", [])
    if not isinstance(raw_relationships, list):
        raise ValueError(f"{path} relationships must be a list")
    relationships: list[RelationshipOverride] = []
    for index, raw in enumerate(raw_relationships):
        context = f"{path} relationships[{index}]"
        definition = _mapping(raw, context)
        unknown = set(definition) - {
            "from",
            "to",
            "crossFilteringBehavior",
            "fromCardinality",
            "toCardinality",
            "securityFilteringBehavior",
        }
        if unknown:
            raise ValueError(f"Unknown keys in {context}: {', '.join(sorted(unknown))}")
        from_table, from_column = _field_reference(
            _required_string(definition, "from", context), f"{context} from"
        )
        to_table, to_column = _field_reference(
            _required_string(definition, "to", context), f"{context} to"
        )
        behavior = definition.get("crossFilteringBehavior", "oneDirection")
        if not isinstance(behavior, str) or behavior not in {
            "oneDirection",
            "bothDirections",
        }:
            raise ValueError(
                f"{context} crossFilteringBehavior must be "
                "'oneDirection' or 'bothDirections'"
            )
        from_cardinality = definition.get("fromCardinality", "many")
        to_cardinality = definition.get("toCardinality", "one")
        security_behavior = definition.get("securityFilteringBehavior", "oneDirection")
        if from_cardinality not in {"one", "many"}:
            raise ValueError(f"{context} fromCardinality must be 'one' or 'many'")
        if to_cardinality not in {"one", "many"}:
            raise ValueError(f"{context} toCardinality must be 'one' or 'many'")
        if security_behavior not in {"oneDirection", "bothDirections"}:
            raise ValueError(
                f"{context} securityFilteringBehavior must be "
                "'oneDirection' or 'bothDirections'"
            )
        relationships.append(
            RelationshipOverride(
                from_table,
                from_column,
                to_table,
                to_column,
                str(behavior),
                str(from_cardinality),
                str(to_cardinality),
                str(security_behavior),
            )
        )

    table_sources: list[TableSourceOverride] = []
    raw_sources = loaded.get("table_sources", [])
    if not isinstance(raw_sources, list):
        raise ValueError(f"{path} table_sources must be a list")
    for index, raw in enumerate(raw_sources):
        context = f"{path} table_sources[{index}]"
        definition = _mapping(raw, context)
        unknown = set(definition) - {"table", "mode", "m"}
        if unknown:
            raise ValueError(f"Unknown keys in {context}: {', '.join(sorted(unknown))}")
        mode = _required_string(definition, "mode", context)
        if mode not in {"import", "directQuery"}:
            raise ValueError(f"{context} mode must be 'import' or 'directQuery'")
        table_sources.append(
            TableSourceOverride(
                _required_string(definition, "table", context),
                mode,
                _required_string(definition, "m", context),
            )
        )

    m_parameters: list[MParameterOverride] = []
    raw_m_parameters = loaded.get("m_parameters", [])
    if not isinstance(raw_m_parameters, list):
        raise ValueError(f"{path} m_parameters must be a list")
    for index, raw in enumerate(raw_m_parameters):
        context = f"{path} m_parameters[{index}]"
        definition = _mapping(raw, context)
        unknown = set(definition) - {"name", "value", "dataType"}
        if unknown:
            raise ValueError(f"Unknown keys in {context}: {', '.join(sorted(unknown))}")
        data_type = definition.get("dataType", "Text")
        if data_type not in {"Text", "Number", "Date"}:
            raise ValueError(f"{context} dataType must be Text, Number, or Date")
        m_parameters.append(
            MParameterOverride(
                _required_string(definition, "name", context),
                _required_string(definition, "value", context),
                str(data_type),
            )
        )

    roles: list[RoleOverride] = []
    raw_roles = loaded.get("roles", [])
    if not isinstance(raw_roles, list):
        raise ValueError(f"{path} roles must be a list")
    for index, raw in enumerate(raw_roles):
        context = f"{path} roles[{index}]"
        definition = _mapping(raw, context)
        unknown = set(definition) - {"name", "table", "expression", "filters"}
        if unknown:
            raise ValueError(f"Unknown keys in {context}: {', '.join(sorted(unknown))}")
        role_name = _required_string(definition, "name", context)
        if "filters" in definition:
            if "table" in definition or "expression" in definition:
                raise ValueError(
                    f"{context} must use either filters or table/expression"
                )
            raw_filters = definition["filters"]
            if not isinstance(raw_filters, list) or not raw_filters:
                raise ValueError(f"{context} filters must be a non-empty list")
            role_filters: list[tuple[str, str]] = []
            for filter_index, raw_filter in enumerate(raw_filters):
                filter_context = f"{context} filters[{filter_index}]"
                role_filter = _mapping(raw_filter, filter_context)
                unknown = set(role_filter) - {"table", "expression"}
                if unknown:
                    raise ValueError(
                        f"Unknown keys in {filter_context}: {', '.join(sorted(unknown))}"
                    )
                role_filters.append(
                    (
                        _required_string(role_filter, "table", filter_context),
                        _required_string(role_filter, "expression", filter_context),
                    )
                )
        else:
            role_filters = [
                (
                    _required_string(definition, "table", context),
                    _required_string(definition, "expression", context),
                )
            ]
        if len({table.casefold() for table, _ in role_filters}) != len(role_filters):
            raise ValueError(f"{context} filters must reference unique tables")
        roles.append(
            RoleOverride(
                role_name,
                role_filters,
            )
        )

    parameter_tables: list[ParameterTableOverride] = []
    raw_parameter_tables = loaded.get("parameter_tables", [])
    if not isinstance(raw_parameter_tables, list):
        raise ValueError(f"{path} parameter_tables must be a list")
    for index, raw in enumerate(raw_parameter_tables):
        context = f"{path} parameter_tables[{index}]"
        definition = _mapping(raw, context)
        unknown = set(definition) - {"name", "dataType", "values"}
        if unknown:
            raise ValueError(f"Unknown keys in {context}: {', '.join(sorted(unknown))}")
        data_type = definition.get("dataType", "integer")
        values = definition.get("values")
        if data_type not in {"integer", "date", "string"}:
            raise ValueError(f"{context} dataType must be integer, date, or string")
        if not isinstance(values, list) or not values or any(
            not isinstance(value, (str, int, float)) for value in values
        ):
            raise ValueError(f"{context} values must be a non-empty scalar list")
        parameter_tables.append(
            ParameterTableOverride(
                _required_string(definition, "name", context),
                str(data_type),
                [str(value) for value in values],
            )
        )

    ignored_parameters = loaded.get("ignored_parameters", [])
    if not isinstance(ignored_parameters, list) or any(
        not isinstance(value, str) or not value.strip()
        for value in ignored_parameters
    ):
        raise ValueError(f"{path} ignored_parameters must be a list of names")
    ignored_calculations = loaded.get("ignored_calculations", [])
    if not isinstance(ignored_calculations, list) or any(
        not isinstance(value, str) or not value.strip()
        for value in ignored_calculations
    ):
        raise ValueError(f"{path} ignored_calculations must be a list of names")
    ignored_relationships: list[tuple[str, str, str, str]] = []
    raw_ignored_relationships = loaded.get("ignored_relationships", [])
    if not isinstance(raw_ignored_relationships, list):
        raise ValueError(f"{path} ignored_relationships must be a list")
    for index, raw in enumerate(raw_ignored_relationships):
        context = f"{path} ignored_relationships[{index}]"
        definition = _mapping(raw, context)
        unknown = set(definition) - {"from", "to"}
        if unknown:
            raise ValueError(f"Unknown keys in {context}: {', '.join(sorted(unknown))}")
        from_table, from_column = _field_reference(
            _required_string(definition, "from", context), f"{context} from"
        )
        to_table, to_column = _field_reference(
            _required_string(definition, "to", context), f"{context} to"
        )
        ignored_relationships.append(
            (
                from_table,
                from_column,
                to_table,
                to_column,
            )
        )

    return ModelOverrides(
        calculated_columns,
        calculated_tables,
        relationships,
        table_sources,
        m_parameters,
        roles,
        parameter_tables,
        ignored_parameters,
        ignored_calculations,
        ignored_relationships,
    )
