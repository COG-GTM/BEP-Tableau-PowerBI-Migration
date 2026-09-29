from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable, Mapping

from tableau2pbip.ir import (
    Action,
    Calc,
    Dashboard,
    Encoding,
    FieldRef,
    Parameter,
    Pane,
    Relationship,
    Style,
    Table,
    TableColumn,
    TextRun,
    Workbook,
    Worksheet,
    WorksheetFilter,
    Zone,
)


_FIELD_REF = re.compile(r"^\[(?P<datasource>[^\]]+)\]\.\[(?P<ref>.*)\]$")
_BRACKET_REF = re.compile(r"\[([^\]]+)\]")
_DIM_SUFFIX = re.compile(r"\s+\([^()]+\.csv\)$", re.IGNORECASE)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element if _local_name(child.tag) == name]


def _first(element: ET.Element, name: str) -> ET.Element | None:
    return next((child for child in element if _local_name(child.tag) == name), None)


def _walk(element: ET.Element, name: str) -> Iterable[ET.Element]:
    return (child for child in element.iter() if _local_name(child.tag) == name)


def _value(element: ET.Element | None, default: str = "") -> str:
    if element is None:
        return default
    return "".join(element.itertext()).strip()


def _strip_brackets(value: str) -> str:
    trimmed = value.strip()
    if trimmed.startswith("[") and trimmed.endswith("]"):
        return trimmed[1:-1]
    return trimmed


def _plain_column(value: str) -> str:
    return _DIM_SUFFIX.sub("", _strip_brackets(value))


def _type_for_column(column: ET.Element) -> str:
    calculation = _first(column, "calculation")
    if calculation is not None and column.get("datatype"):
        return column.get("datatype", "string")
    return column.get("datatype", "string")


def _caption_map(datasources: list[ET.Element]) -> dict[str, str]:
    captions: dict[str, str] = {}
    for datasource in datasources:
        for column in _walk(datasource, "column"):
            internal = _strip_brackets(column.get("name", ""))
            if not internal:
                continue
            captions[internal] = column.get("caption", _plain_column(internal))
    return captions


def decode_field_ref(
    ref: str, captions: Mapping[str, str] | None = None
) -> FieldRef:
    match = _FIELD_REF.fullmatch(ref.strip())
    if match is None:
        cleaned = _strip_brackets(ref)
        mapping = captions or {}
        return FieldRef("", "none", cleaned, mapping.get(cleaned, cleaned), "", ref)

    raw_ref = match.group("ref")
    chunks = raw_ref.split(":")
    derivation = chunks[0] if len(chunks) > 1 else "none"
    if len(chunks) > 1:
        suffix = chunks[-1] if len(chunks) > 2 else ""
        internal = ":".join(chunks[1:-1]) if len(chunks) > 2 else chunks[1]
    else:
        suffix = ""
        internal = raw_ref
    internal = _strip_brackets(internal)
    mapping = captions or {}
    caption = mapping.get(internal, mapping.get(_plain_column(internal), _plain_column(internal)))
    return FieldRef(
        match.group("datasource"),
        derivation,
        internal,
        caption,
        suffix,
        ref,
    )


def _resolve_formula(formula: str, captions: Mapping[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        raw = match.group(1)
        if raw.casefold() == "parameters":
            return "[Parameters]"
        if raw == "Parameter 1":
            return "[Select Year]"
        return f"[{captions.get(raw, captions.get(_plain_column(raw), _plain_column(raw)))}]"

    resolved = _BRACKET_REF.sub(replace, formula)
    return resolved.replace("[Parameters].[Parameters].", "[Parameters].")


def _table_columns(
    datasource: ET.Element, caption: str, source_name: str
) -> list[TableColumn]:
    columns: list[TableColumn] = []
    connection = _first(datasource, "connection")
    metadata_records = next(_walk(connection, "metadata-records"), None) if connection is not None else None
    if metadata_records is not None:
        for record in _children(metadata_records, "metadata-record"):
            if record.get("class") != "column":
                continue
            parent_name = _strip_brackets(_value(_first(record, "parent-name")))
            if parent_name and parent_name != source_name:
                continue
            column_name = _value(_first(record, "remote-name")) or _value(
                _first(record, "local-name")
            )
            if not column_name:
                continue
            datatype = (
                _value(_first(record, "local-type"))
                or _value(_first(record, "remote-type"))
                or "string"
            )
            columns.append(TableColumn(_plain_column(column_name), datatype))
    if columns:
        return columns

    seen: set[str] = set()
    source_basename = Path(source_name).name
    for column in _walk(datasource, "column"):
        internal = _strip_brackets(column.get("name", ""))
        if not internal or column.find("calculation") is not None:
            continue
        belongs_to_table = (
            internal.endswith(f" ({source_basename})")
            or internal.startswith(f"{source_basename}#")
            or (source_basename.casefold() == "orders.csv" and "(" not in internal)
        )
        if not belongs_to_table:
            continue
        plain = _plain_column(column.get("caption", internal))
        if plain not in seen:
            seen.add(plain)
            columns.append(TableColumn(plain, _type_for_column(column)))
    return columns


def _parse_tables(datasources: list[ET.Element]) -> tuple[list[Table], dict[str, str]]:
    tables: list[Table] = []
    object_captions: dict[str, str] = {}
    for datasource in datasources:
        if datasource.get("name") == "Parameters":
            continue
        connection = _first(datasource, "connection")
        relation = next(
            (
                child
                for child in _walk(connection, "relation")
                if child.get("type") == "collection"
            ),
            None,
        ) if connection is not None else None
        if relation is None:
            continue
        for obj in _walk(datasource, "object"):
            caption = obj.get("caption", obj.get("id", ""))
            object_id = obj.get("id", "")
            table_relation = next(
                (
                    child
                    for child in _walk(obj, "relation")
                    if child.get("type") == "table"
                    and child.get("name") != ""
                    and child.get("table", "").startswith("[Extract].")
                ),
                None,
            )
            if table_relation is None:
                table_relation = next(_walk(obj, "relation"), None)
            if table_relation is None:
                continue
            hyper_table = table_relation.get("name", "")
            source_name = next(
                (
                    child.get("name", "")
                    for child in _walk(obj, "relation")
                    if child.get("connection", "").startswith("textscan.")
                ),
                f"{caption}.csv",
            )
            tables.append(
                Table(
                    caption,
                    hyper_table,
                    _table_columns(datasource, caption, source_name),
                )
            )
            object_captions[object_id] = caption
    return tables, object_captions


def _parse_relationships(
    datasources: list[ET.Element], object_captions: Mapping[str, str]
) -> list[Relationship]:
    relationships: list[Relationship] = []
    for datasource in datasources:
        for group in _walk(datasource, "relationships"):
            for relation in _children(group, "relationship"):
                expression = _first(relation, "expression")
                endpoints = _children(relation, "first-end-point") + _children(
                    relation, "second-end-point"
                )
                fields = _children(expression, "expression") if expression is not None else []
                if len(endpoints) != 2 or len(fields) != 2:
                    continue
                first_id = endpoints[0].get("object-id", "")
                second_id = endpoints[1].get("object-id", "")
                first_field = _plain_column(fields[0].get("op", ""))
                second_field = _plain_column(fields[1].get("op", ""))
                if first_id in object_captions and second_id in object_captions:
                    relationships.append(
                        Relationship(
                            object_captions[first_id],
                            first_field,
                            object_captions[second_id],
                            second_field,
                        )
                    )
    return relationships


def _parse_parameters(datasources: list[ET.Element]) -> list[Parameter]:
    parameters: list[Parameter] = []
    for datasource in datasources:
        if datasource.get("name") != "Parameters":
            continue
        for column in _walk(datasource, "column"):
            if not column.get("param-domain-type"):
                continue
            members: list[str] = []
            member_root = _first(column, "members")
            if member_root is not None:
                for member in _children(member_root, "member"):
                    members.append(
                        member.get("value", _value(member))
                    )
            parameters.append(
                Parameter(
                    _strip_brackets(column.get("name", "")),
                    column.get("caption", column.get("name", "")),
                    column.get("datatype", "string"),
                    members,
                    column.get("value", ""),
                    column.get("default-format", ""),
                )
            )
    return parameters


def _parse_calcs(
    datasources: list[ET.Element],
    captions: Mapping[str, str],
    parameters: list[Parameter],
) -> list[Calc]:
    parameter_names = {param.internal_name for param in parameters}
    calculations: list[Calc] = []
    for datasource in datasources:
        if datasource.get("name") == "Parameters":
            continue
        for column in _walk(datasource, "column"):
            calculation = _first(column, "calculation")
            if calculation is None or column.get("name", "") in parameter_names:
                continue
            formula = calculation.get("formula", "")
            internal = _strip_brackets(column.get("name", ""))
            calculations.append(
                Calc(
                    internal,
                    column.get("caption", internal),
                    formula,
                    _resolve_formula(formula, captions),
                    column.get("datatype", "string"),
                    column.get("role", ""),
                    column.get("type", ""),
                    column.get("default-format", ""),
                )
            )
    return calculations


def _parse_worksheet(element: ET.Element) -> Worksheet:
    shelves: dict[str, str] = {}
    for shelf in ("rows", "cols"):
        node = next(_walk(element, shelf), None)
        shelves[shelf] = ET.tostring(node, encoding="unicode") if node is not None else ""

    panes: list[Pane] = []
    for pane in _walk(element, "pane"):
        mark = next(_walk(pane, "mark"), None)
        encodings: list[Encoding] = []
        for encoding_root in _walk(pane, "encodings"):
            for encoding in encoding_root:
                field_ref = encoding.get("column", encoding.get("field", ""))
                if not field_ref:
                    field_node = next(_walk(encoding, "field"), None)
                    if field_node is not None:
                        field_ref = field_node.get("name", field_node.get("column", ""))
                if field_ref:
                    encodings.append(Encoding(_local_name(encoding.tag), field_ref))
        panes.append(Pane(mark.get("class", "") if mark is not None else "", encodings))

    filters = [
        WorksheetFilter(
            item.get("class", ""),
            item.get("column", ""),
            ET.tostring(item, encoding="unicode"),
        )
        for item in _walk(element, "filter")
    ]
    styles: list[Style] = []
    for style in _walk(element, "style"):
        for format_element in _walk(style, "format"):
            styles.append(
                Style(
                    _local_name(style.tag),
                    format_element.get("attr", ""),
                    format_element.get("value", ""),
                    format_element.get("field", ""),
                )
            )
    return Worksheet(
        element.get("name", ""),
        shelves["rows"],
        shelves["cols"],
        panes,
        filters,
        styles,
    )


def _zone(element: ET.Element, width: int, height: int) -> Zone:
    raw_x = int(float(element.get("x", "0")))
    raw_y = int(float(element.get("y", "0")))
    raw_w = int(float(element.get("w", "0")))
    raw_h = int(float(element.get("h", "0")))
    style: dict[str, str] = {}
    zone_style = _first(element, "zone-style")
    if zone_style is not None:
        for item in _children(zone_style, "format"):
            style[item.get("attr", "")] = item.get("value", "")

    text_runs = [
        TextRun(
            run.get("fontname", ""),
            run.get("fontsize", ""),
            run.get("fontcolor", ""),
            run.get("bold", "").casefold() == "true",
            _value(run),
        )
        for run in _walk(element, "run")
    ]
    children = [
        _zone(child, width, height)
        for child in _children(element, "zone")
    ]
    return Zone(
        element.get("id", ""),
        element.get("type-v2", ""),
        element.get("name", ""),
        element.get("param", ""),
        element.get("friendly-name", ""),
        round(raw_x * width / 100000, 2),
        round(raw_y * height / 100000, 2),
        round(raw_w * width / 100000, 2),
        round(raw_h * height / 100000, 2),
        raw_x,
        raw_y,
        raw_w,
        raw_h,
        style,
        element.get("is-fixed", "").casefold() == "true",
        text_runs,
        children,
    )


def _parse_dashboards(root: ET.Element) -> list[Dashboard]:
    dashboards: list[Dashboard] = []
    for element in _walk(root, "dashboard"):
        size = next(_walk(element, "size"), None)
        width = int(size.get("maxwidth", size.get("minwidth", "1200"))) if size is not None else 1200
        height = int(size.get("maxheight", size.get("minheight", "800"))) if size is not None else 800
        zones_root = next(_walk(element, "zones"), None)
        zones = (
            [_zone(zone, width, height) for zone in _children(zones_root, "zone")]
            if zones_root is not None
            else []
        )
        dashboards.append(Dashboard(element.get("name", ""), width, height, zones))
    by_name = {dashboard.name: dashboard for dashboard in dashboards}
    window_order = [
        element.get("name", "")
        for element in _walk(root, "window")
        if element.get("class") == "dashboard"
    ]
    ordered = [by_name[name] for name in window_order if name in by_name]
    ordered_names = {dashboard.name for dashboard in ordered}
    ordered.extend(
        dashboard for dashboard in dashboards if dashboard.name not in ordered_names
    )
    return ordered


def _parse_actions(root: ET.Element) -> list[Action]:
    actions: list[Action] = []
    for element in _walk(root, "action"):
        source = _first(element, "source")
        command_node = _first(element, "command")
        target = next(
            (
                param.get("value", "")
                for param in _walk(command_node, "param")
                if param.get("name") == "target"
            ),
            "",
        ) if command_node is not None else ""
        actions.append(
            Action(
                element.get("caption", element.get("name", "")),
                source.get("dashboard", "") if source is not None else "",
                source.get("worksheet", "") if source is not None else "",
                command_node.get("command", "") if command_node is not None else "",
                target,
            )
        )
    return actions


def parse_workbook(twb: Path) -> Workbook:
    root = ET.parse(twb).getroot()
    datasources = list(_walk(root, "datasource"))
    captions = _caption_map(datasources)
    tables, object_captions = _parse_tables(datasources)
    relationships = _parse_relationships(datasources, object_captions)
    parameters = _parse_parameters(datasources)
    calcs = _parse_calcs(datasources, captions, parameters)
    worksheets = [
        _parse_worksheet(element) for element in _walk(root, "worksheet")
    ]
    return Workbook(
        Path(twb).stem,
        tables,
        relationships,
        calcs,
        parameters,
        worksheets,
        _parse_dashboards(root),
        _parse_actions(root),
    )
