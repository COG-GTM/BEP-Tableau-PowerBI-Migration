from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class ModelOverrides:
    calculated_columns: list[CalculatedColumnOverride]
    calculated_tables: list[CalculatedTableOverride]
    relationships: list[RelationshipOverride]


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
    unknown = set(loaded) - {"calculated_columns", "calculated_tables", "relationships"}
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
        unknown = set(definition) - {"from", "to", "crossFilteringBehavior"}
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
        relationships.append(
            RelationshipOverride(
                from_table,
                from_column,
                to_table,
                to_column,
                str(behavior),
            )
        )

    return ModelOverrides(calculated_columns, calculated_tables, relationships)
