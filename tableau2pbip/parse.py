from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Iterable, Mapping

from tableau2pbip.ir import (
    Action,
    Button,
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
_TABLE_EXTENSION = re.compile(r"\.(?:csv|txt|tsv|xlsx|xls|hyper)$", re.IGNORECASE)


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
        mapping = captions or {}
        payload = chunks[1:]
        internal = ""
        suffix = ""
        for length in range(len(payload), 0, -1):
            candidate = ":".join(payload[:length])
            if candidate in mapping:
                internal = candidate
                suffix = ":".join(payload[length:])
                break
        if not internal:
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
    datasource: ET.Element,
    caption: str,
    source_name: str,
    relation: ET.Element | None = None,
) -> list[TableColumn]:
    columns: list[TableColumn] = []
    relation_columns = _first(relation, "columns") if relation is not None else None
    if relation_columns is not None:
        for column in _children(relation_columns, "column"):
            column_name = column.get("name", "")
            if column_name:
                columns.append(
                    TableColumn(_plain_column(column_name), _type_for_column(column))
                )
    if columns:
        return columns

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
        objects = list(_walk(datasource, "object"))
        if not objects:
            continue
        for obj in objects:
            caption = _TABLE_EXTENSION.sub(
                "", obj.get("caption", obj.get("id", ""))
            )
            object_id = obj.get("id", "")
            relations = [
                child
                for child in _walk(obj, "relation")
                if child.get("type") == "table" and child.get("name")
            ]
            table_relation = next(
                (
                    relation
                    for relation in relations
                    if relation.get("table", "").startswith("[Extract].")
                ),
                None,
            )
            if table_relation is None:
                table_relation = next(iter(relations), None)
            if table_relation is None:
                continue
            hyper_table = table_relation.get("name", "")
            source_relation = next(
                (
                    relation
                    for relation in relations
                    if relation.get("connection", "").startswith(
                        ("textscan.", "excel.")
                    )
                ),
                None,
            )
            column_relation = next(
                (
                    relation
                    for relation in relations
                    if _first(relation, "columns") is not None
                ),
                (
                    source_relation
                    if source_relation is not None
                    else table_relation
                ),
            )
            source_name = (
                source_relation.get("name", "")
                if source_relation is not None
                else f"{caption}.csv"
            )
            tables.append(
                Table(
                    caption,
                    hyper_table,
                    _table_columns(
                        datasource, caption, source_name, column_relation
                    ),
                )
            )
            object_captions[object_id] = caption
    return tables, object_captions


def _infer_fact_table(
    tables: list[Table], relationships: list[Relationship]
) -> str:
    if relationships:
        counts = Counter(relationship.from_table for relationship in relationships)
        return max(counts, key=counts.get)
    return tables[0].caption if tables else ""


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
        [
            TextRun(
                run.get("fontname", ""),
                run.get("fontsize", ""),
                run.get("fontcolor", ""),
                run.get("bold", "").casefold() == "true",
                _value(run),
            )
            for label in _walk(element, "customized-label")
            for run in _walk(label, "run")
        ],
    )


def _zone(
    element: ET.Element,
    width: int,
    height: int,
    hidden_by_ancestor: bool = False,
) -> Zone:
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
    hidden_by_user = hidden_by_ancestor or (
        element.get("hidden-by-user", "").casefold() == "true"
    )
    children = [
        _zone(child, width, height, hidden_by_user)
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
        hidden_by_user,
        _parse_button(element),
        element.get("show-title", "true").casefold() != "false",
    )


def _parse_button(element: ET.Element) -> Button | None:
    button = _first(element, "button")
    if button is None:
        return None
    action = button.get("action", "")
    toggle_action = next(_walk(button, "toggle-action"), None)
    export_action = next(
        (
            item
            for item in button.iter()
            if _local_name(item.tag).casefold().endswith("export-button-action")
        ),
        None,
    )
    export_metadata = next(
        (
            value
            for key, value in button.attrib.items()
            if "button-click-action-metadata" in key.casefold()
        ),
        "",
    )
    export_text = _value(export_action)
    export_match = re.search(
        r"""dashboard-button-export-type=["']([^"']+)["']""",
        export_text,
        re.IGNORECASE,
    )
    export_type = export_match.group(1) if export_match is not None else export_metadata
    if toggle_action is not None:
        kind = "toggle"
        action_text = _value(toggle_action)
    elif export_action is not None or export_type:
        kind = "export"
        action_text = export_text
    elif "goto-sheet" in action.casefold():
        kind = "goto"
        action_text = action
    else:
        kind = "other"
        action_text = action
    window_match = re.search(
        r"""window-id\s*=\s*["']?(\{[^}]+\}|[^\s"']+)""",
        action_text,
        re.IGNORECASE,
    )
    toggle_match = re.search(
        r"zone-ids\s*=\s*\[([^\]]*)\]", action_text, re.IGNORECASE
    )
    toggle_zone_ids = (
        [
            item.strip().strip("'\"")
            for item in toggle_match.group(1).split(",")
            if item.strip().strip("'\"")
        ]
        if toggle_match is not None
        else []
    )
    try:
        active_state = int(button.get("active-visual-state-index", "0"))
    except ValueError:
        active_state = 0
    return Button(
        kind=kind,
        target_window_id=window_match.group(1) if window_match is not None else "",
        toggle_zone_ids=toggle_zone_ids,
        images=[
            _value(image)
            for image in _walk(button, "image-path")
            if _value(image)
        ],
        active_state=active_state,
        export_type=export_type,
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
        page_background = next(
            (
                item.get("value")
                for style in _children(element, "style")
                for item in _walk(style, "format")
                if item.get("attr", "").casefold() == "background-color"
                and item.get("value")
            ),
            None,
        )
        dashboards.append(
            Dashboard(
                element.get("name", ""),
                width,
                height,
                zones,
                page_background,
            )
        )
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


def _parse_window_ids(root: ET.Element) -> dict[str, str]:
    result: dict[str, str] = {}
    for window in _walk(root, "window"):
        if window.get("class") != "dashboard":
            continue
        simple_id = _first(window, "simple-id")
        if simple_id is None:
            continue
        window_id = simple_id.get("uuid", "")
        name = window.get("name", "")
        if window_id and name:
            result[window_id] = name
    return result


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
        _parse_start_of_week(root),
        _infer_fact_table(tables, relationships),
        _parse_window_ids(root),
        *_parse_default_style(root),
    )


def _parse_default_style(root: ET.Element) -> tuple[str, str]:
    defaults: dict[str, str] = {}
    for style in _children(root, "style"):
        for rule in _children(style, "style-rule"):
            if rule.get("element", "").casefold() != "all":
                continue
            for format_element in _children(rule, "format"):
                attr = format_element.get("attr", "").casefold()
                value = format_element.get("value", "")
                if attr in {"font-family", "color"} and value:
                    defaults[attr] = value
    return defaults.get("font-family", ""), defaults.get("color", "")


def _parse_start_of_week(root: ET.Element) -> str:
    date_options = next(root.iter("date-options"), None)
    value = (
        date_options.get("start-of-week", "sunday")
        if date_options is not None
        else "sunday"
    ).casefold()
    if value not in {"monday", "sunday"}:
        raise ValueError(f"Unsupported Tableau start-of-week value {value!r}")
    return value
