from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from tableauhyperapi import (
    Connection,
    CreateMode,
    HyperProcess,
    TableName,
    Telemetry,
)

from tableau2pbip.ir import Table, Workbook
from tableau2pbip.parse import decode_field_ref
from tableau2pbip.unpack import Unpacked


_FIELD_REF = re.compile(r"\[[^\]]+\]\.\[[^\]]+\]")
_BRACKET = re.compile(r"\[([^\]]+)\]")
_DIM_SUFFIX = re.compile(r"\s+\([^()]+\.csv\)$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class TableConflict:
    table: str
    key_column: str
    duplicate_keys: int
    conflict_columns: dict[str, int]


@dataclass(frozen=True, slots=True)
class ExtractResult:
    csv_paths: dict[str, Path]
    row_counts: dict[str, int]
    conflicts: list[TableConflict]
    column_types: dict[str, dict[str, str]]


def _plain(value: str) -> str:
    cleaned = value.strip()
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1]
    return _DIM_SUFFIX.sub("", cleaned)


def _value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _table_mapping(connection: Connection, workbook: Workbook) -> dict[str, TableName]:
    available: list[TableName] = []
    for schema in connection.catalog.get_schema_names():
        available.extend(connection.catalog.get_table_names(schema))
    mapping: dict[str, TableName] = {}
    for table in workbook.tables:
        exact = next(
            (
                candidate
                for candidate in available
                if candidate.name.unescaped == table.hyper_table
            ),
            None,
        )
        if exact is None:
            exact = next(
                (
                    candidate
                    for candidate in available
                    if candidate.name.unescaped.endswith(table.hyper_table)
                    or table.hyper_table.endswith(candidate.name.unescaped)
                ),
                None,
            )
        if exact is not None:
            mapping[table.caption] = exact
    return mapping


def _read_table(
    connection: Connection, table_name: TableName
) -> tuple[list[str], list[list[str]], dict[str, str]]:
    definition = connection.catalog.get_table_definition(table_name)
    columns = [column.name.unescaped for column in definition.columns]
    column_types = {
        _plain(column.name.unescaped): str(column.type)
        for column in definition.columns
    }
    rows: list[list[str]] = []
    with connection.execute_query(f"SELECT * FROM {table_name}") as result:
        for row in result:
            rows.append([_value(value) for value in row])
    return columns, rows, column_types


def _referenced_columns(workbook: Workbook) -> set[str]:
    referenced: set[str] = set()
    captions = {
        calc.internal_name: calc.caption for calc in workbook.calcs
    }
    for parameter in workbook.parameters:
        captions[parameter.internal_name] = parameter.caption
    for calc in workbook.calcs:
        for match in _BRACKET.finditer(calc.formula_raw):
            name = _plain(match.group(1))
            if name.casefold() not in {"parameters", "fixed"}:
                referenced.add(name)
                referenced.add(_plain(captions.get(name, name)))
    for worksheet in workbook.worksheets:
        raw_values = [worksheet.rows, worksheet.cols]
        raw_values.extend(filter_.column for filter_ in worksheet.filters)
        raw_values.extend(filter_.raw_xml for filter_ in worksheet.filters)
        for pane in worksheet.panes:
            raw_values.extend(encoding.field_ref for encoding in pane.encodings)
        for raw in raw_values:
            for field_ref in _FIELD_REF.findall(raw):
                decoded = decode_field_ref(field_ref, captions)
                referenced.add(_plain(decoded.field_internal))
                referenced.add(_plain(decoded.field_caption))
            for match in _BRACKET.finditer(raw):
                value = _plain(match.group(1))
                if value.casefold() not in {"federated", "parameters"}:
                    referenced.add(value)
    return referenced


def _dimension_relationships(workbook: Workbook) -> dict[str, str]:
    return {
        relation.to_table: relation.to_col
        for relation in workbook.relationships
        if relation.from_table.casefold() == "orders"
    }


def _deduplicate(
    table: Table,
    columns: list[str],
    rows: list[list[str]],
    key_column: str,
    used_columns: set[str],
) -> tuple[list[list[str]], TableConflict | None]:
    normalized = [_plain(name) for name in columns]
    try:
        key_index = normalized.index(_plain(key_column))
    except ValueError as error:
        raise ValueError(
            f"Relationship key {key_column!r} is not present in {table.caption!r}"
        ) from error
    groups: dict[str, list[list[str]]] = {}
    order: list[str] = []
    for row in rows:
        key = row[key_index]
        if not key.strip():
            continue
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(row)
    conflict_columns: dict[str, int] = {}
    duplicate_keys = 0
    for key in order:
        group = groups[key]
        if len(group) < 2:
            continue
        duplicate_keys += 1
        for index, column_name in enumerate(normalized):
            if index == key_index:
                continue
            if any(row[index] != group[0][index] for row in group[1:]):
                conflict_columns[column_name] = conflict_columns.get(column_name, 0) + 1
    used_casefold = {column.casefold() for column in used_columns}
    unsafe = sorted(
        column for column in conflict_columns if column.casefold() in used_casefold
    )
    if unsafe:
        raise ValueError(
            f"Conflicting duplicate keys in {table.caption!r} affect referenced "
            f"columns: {', '.join(unsafe)}"
        )
    deduplicated = [groups[key][0] for key in order]
    if duplicate_keys == 0:
        return deduplicated, None
    return deduplicated, TableConflict(
        table.caption,
        key_column,
        duplicate_keys,
        conflict_columns,
    )


def _save_csv(path: Path, columns: list[str], rows: Iterable[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = [_plain(column) for column in columns]
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(normalized)
        writer.writerows(rows)


def extract_tables(
    unpacked: Unpacked, workbook: Workbook, out_dir: Path
) -> ExtractResult:
    if not unpacked.hyper_paths:
        raise FileNotFoundError("No Tableau Hyper extract was found")
    used_columns = _referenced_columns(workbook)
    dimension_keys = _dimension_relationships(workbook)
    csv_paths: dict[str, Path] = {}
    row_counts: dict[str, int] = {}
    conflicts: list[TableConflict] = []
    column_types: dict[str, dict[str, str]] = {}
    with HyperProcess(
        telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU
    ) as hyper:
        for hyper_path in unpacked.hyper_paths:
            with Connection(
                endpoint=hyper.endpoint,
                database=str(hyper_path),
                create_mode=CreateMode.NONE,
            ) as connection:
                hyper_tables = _table_mapping(connection, workbook)
                for table in workbook.tables:
                    if table.caption not in hyper_tables or table.caption in csv_paths:
                        continue
                    columns, rows, table_column_types = _read_table(
                        connection, hyper_tables[table.caption]
                    )
                    column_types[table.caption] = table_column_types
                    if table.caption in dimension_keys:
                        rows, conflict = _deduplicate(
                            table,
                            columns,
                            rows,
                            dimension_keys[table.caption],
                            used_columns,
                        )
                        if conflict is not None:
                            conflicts.append(conflict)
                    path = out_dir / f"{table.caption}.csv"
                    _save_csv(path, columns, rows)
                    csv_paths[table.caption] = path
                    row_counts[table.caption] = len(rows)
    missing_tables = sorted(table.caption for table in workbook.tables if table.caption not in csv_paths)
    if missing_tables:
        raise ValueError(
            f"Hyper extracts did not contain expected tables: {', '.join(missing_tables)}"
        )
    return ExtractResult(csv_paths, row_counts, conflicts, column_types)
