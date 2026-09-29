from __future__ import annotations

import re
import shutil
import tempfile
from collections import Counter
from pathlib import Path

import yaml

from tableau2pbip.calc.dax import (
    CalcTranslation,
    CalculationCompiler,
    generate_auto_measures,
)
from tableau2pbip.ir import Dashboard, TextRun, Workbook, Worksheet, Zone
from tableau2pbip.layout import load_layout, visual_folder_name
from tableau2pbip.migrate import (
    _load_overrides,
    _model_field_types,
    _project_name,
)
from tableau2pbip.overrides import load_model_overrides
from tableau2pbip.parse import decode_field_ref, parse_workbook
from tableau2pbip.unpack import unpack


_FIELD_REFERENCE = re.compile(r"\[[^\]]+\]\.\[[^\]]+\]")
_AGGREGATIONS = {"sum", "avg", "min", "max", "cnt", "ctd", "count", "countd"}
_DATE_PARTS = {"mn", "wk", "yr", "qr", "dy", "tmn", "twk", "tyr", "tqr", "tdy"}


def _leaf_zones(zones: list[Zone]):
    for zone in zones:
        if zone.children:
            yield from _leaf_zones(zone.children)
        else:
            yield zone


def _leaf_zones_with_ancestors(zones: list[Zone], ancestors: tuple[str, ...] = ()):
    for zone in zones:
        zone_path = (*ancestors, zone.id)
        if zone.children:
            yield from _leaf_zones_with_ancestors(zone.children, zone_path)
        else:
            yield zone, zone_path


def _workbook_field_names(workbook: Workbook) -> dict[str, str]:
    names: dict[str, str] = {}
    for calc in workbook.calcs:
        names[calc.internal_name] = calc.caption
    for table in workbook.tables:
        for column in table.columns:
            names[column.name] = column.name
    for parameter in workbook.parameters:
        names[parameter.internal_name] = parameter.caption
    return names


def _is_measure_mapping(
    name: str,
    workbook: Workbook,
    translations: dict[str, CalcTranslation],
    auto_measure_names: set[str],
    date_column_names: set[str],
) -> bool:
    if name in date_column_names:
        return False
    if name in auto_measure_names:
        return True
    calc = next(
        (item for item in workbook.calcs if item.caption == name), None
    )
    if calc is None:
        return False
    translation = translations.get(calc.internal_name)
    return bool(
        translation is not None
        and translation.status == "supported"
        and (
            translation.classification in {"aggregate", "lod"}
            or not translation.is_calculated_column
        )
    )


def _resolve_field(
    raw_reference: str,
    workbook: Workbook,
    model_fields: dict[str, str],
    translations: dict[str, CalcTranslation],
    measures_map: dict[str, str],
    auto_measure_names: set[str],
    date_column_names: set[str],
    caption_map: dict[str, str],
    *,
    column_only: bool = False,
) -> tuple[str, str] | None:
    reference = decode_field_ref(raw_reference, caption_map)
    mapped_name = measures_map.get(raw_reference)
    if mapped_name:
        is_measure = _is_measure_mapping(
            mapped_name,
            workbook,
            translations,
            auto_measure_names,
            date_column_names,
        )
        kind = "measure" if is_measure else "column"
        field_name = f"{workbook.fact_table}.{mapped_name}"
        if field_name in model_fields and not (column_only and is_measure):
            return kind, field_name

    parameter = next(
        (
            item
            for item in workbook.parameters
            if reference.field_internal
            in {item.internal_name, item.caption}
        ),
        None,
    )
    if parameter is not None:
        field_name = f"{parameter.caption}.{parameter.caption}"
        return ("column", field_name) if field_name in model_fields else None

    calc = next(
        (
            item
            for item in workbook.calcs
            if reference.field_internal in {item.internal_name, item.caption}
            or reference.field_caption == item.caption
        ),
        None,
    )
    if calc is not None:
        translation = translations.get(calc.internal_name)
        if translation is None or translation.status != "supported":
            return None
        kind = (
            "measure"
            if translation.classification in {"aggregate", "lod"}
            or not translation.is_calculated_column
            else "column"
        )
        field_name = f"{workbook.fact_table}.{calc.caption}"
        return (kind, field_name) if field_name in model_fields else None

    candidates = [
        (table.caption, column.name)
        for table in workbook.tables
        for column in table.columns
        if reference.field_internal in {column.name, column.name.strip("[]")}
        or reference.field_caption == column.name
    ]
    candidates.sort(key=lambda item: item[0] != workbook.fact_table)
    for table_name, column_name in candidates:
        field_name = f"{table_name}.{column_name}"
        if field_name not in model_fields:
            continue
        if reference.derivation.casefold() in _AGGREGATIONS and not column_only:
            return "measure", field_name
        return "column", field_name
    return None


def _shelf_fields(
    worksheet: Worksheet, shelf: str
) -> list[tuple[str, str]]:
    markup = worksheet.rows if shelf == "rows" else worksheet.cols
    fields: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw in _FIELD_REFERENCE.findall(markup):
        if raw in seen:
            continue
        seen.add(raw)
        fields.append((raw, shelf))
    return fields


def _worksheet_fields(
    worksheet: Worksheet,
    workbook: Workbook,
    model_fields: dict[str, str],
    translations: dict[str, CalcTranslation],
    measures_map: dict[str, str],
    auto_measure_names: set[str],
    date_column_names: set[str],
    caption_map: dict[str, str],
) -> tuple[
    dict[str, list[dict[str, str]]],
    list[str],
    list[tuple[str, dict[str, str]]],
]:
    raw_shelves = [
        item
        for shelf in ("rows", "cols")
        for item in _shelf_fields(worksheet, shelf)
    ]
    supported_encodings = {
        "text",
        "size",
        "wedge-size",
        "color",
        "label",
        "lod",
        "detail",
    }
    raw_encodings = [
        (encoding.field_ref, encoding.kind.casefold())
        for pane in worksheet.panes
        for encoding in pane.encodings
        if encoding.kind.casefold() in supported_encodings
    ]
    resolved: dict[str, list[dict[str, str]]] = {
        "rows": [],
        "cols": [],
        **{encoding: [] for encoding in supported_encodings},
    }
    dropped: list[str] = []
    encoding_order: list[tuple[str, dict[str, str]]] = []

    def add_field(
        group: str,
        raw: str,
        origin: str,
        *,
        encoding: str = "",
    ) -> None:
        mapped = _resolve_field(
            raw,
            workbook,
            model_fields,
            translations,
            measures_map,
            auto_measure_names,
            date_column_names,
            caption_map,
        )
        if mapped is None:
            try:
                label = decode_field_ref(raw, caption_map).field_caption
            except ValueError:
                label = raw
            dropped.append(f"{label} ({origin}; unresolved)")
            return
        kind, reference = mapped
        value = {kind: reference}
        if value not in resolved[group]:
            resolved[group].append(value)
        if encoding:
            item = (encoding, value)
            if item not in encoding_order:
                encoding_order.append(item)

    for raw, shelf in raw_shelves:
        add_field(shelf, raw, f"{shelf} shelf")

    for raw, encoding in raw_encodings:
        add_field(encoding, raw, f"{encoding} encoding", encoding=encoding)
    return resolved, dropped, encoding_order


def _unique_fields(fields: list[dict[str, str]]) -> list[dict[str, str]]:
    unique: list[dict[str, str]] = []
    for field in fields:
        if field not in unique:
            unique.append(field)
    return unique


def _unique_strings(values: list[str]) -> list[str]:
    unique: list[str] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique


def _roles_for_worksheet(
    worksheet: Worksheet,
    workbook: Workbook,
    model_fields: dict[str, str],
    translations: dict[str, CalcTranslation],
    measures_map: dict[str, str],
    auto_measure_names: set[str],
    date_column_names: set[str],
    caption_map: dict[str, str],
) -> tuple[
    str,
    dict[str, list[dict[str, str]]],
    list[str],
    list[str],
]:
    shelves, dropped, encoding_order = _worksheet_fields(
        worksheet,
        workbook,
        model_fields,
        translations,
        measures_map,
        auto_measure_names,
        date_column_names,
        caption_map,
    )
    dropped = _unique_strings(dropped)
    rows = shelves["rows"]
    cols = shelves["cols"]
    row_dimensions = [field for field in rows if "column" in field]
    column_dimensions = [field for field in cols if "column" in field]
    row_measures = [field for field in rows if "measure" in field]
    column_measures = [field for field in cols if "measure" in field]
    color_dimensions = [
        field for field in shelves["color"] if "column" in field
    ]
    nominal_color_dimensions = [
        field
        for field in color_dimensions
        if model_fields.get(field["column"], "").casefold()
        in {"string", "text", "boolean", "bool"}
    ]
    color_measures = [
        field for field in shelves["color"] if "measure" in field
    ]
    encoded_dimensions = [
        field
        for encoding in ("text", "size", "wedge-size", "color", "label", "lod", "detail")
        for field in shelves[encoding]
        if "column" in field
    ]
    all_dimensions = _unique_fields(
        [
            field
            for field in rows + cols
            if "column" in field
        ]
        + encoded_dimensions
    )
    shelf_measures = _unique_fields(
        [field for field in rows + cols if "measure" in field]
    )
    measure_encodings = [
        field
        for _, field in encoding_order
        if "measure" in field
    ]
    all_measures = _unique_fields(shelf_measures + measure_encodings)
    table_values = _unique_fields(
        shelf_measures
        + [
            field
            for encoding in ("text", "size", "color")
            for field in shelves[encoding]
            if "measure" in field
        ]
    )
    mark_classes = [
        pane.mark_class.casefold().strip()
        for pane in worksheet.panes
        if pane.mark_class.strip()
    ]
    mark_class = next(
        (mark for mark in mark_classes if mark != "automatic"), "automatic"
    )
    roles: dict[str, list[dict[str, str]]] = {}
    errors: list[str] = []

    shelves_text = f"{worksheet.rows}\n{worksheet.cols}".casefold()
    is_map = "multipolygon" in mark_classes or any(
        coordinate in shelves_text
        for coordinate in ("latitude (generated)", "longitude (generated)")
    )
    if is_map:
        geographic = _unique_fields(
            [
                field
                for encoding in ("lod", "detail", "text", "label")
                for field in shelves[encoding]
                if "column" in field
            ]
        )
        if geographic and color_measures:
            roles = {"Category": geographic, "Y": color_measures}
            return (
                "clusteredBarChart",
                roles,
                dropped,
                ["map → bar (map visuals need Power BI sign-in)"],
            )
        errors.append("Map worksheet lacks a mapped geographic dimension or color measure")
    elif (
        ("line" in mark_classes or mark_class in {"line", "area"})
        and row_dimensions
        and nominal_color_dimensions
        and (column_measures or row_measures)
    ):
        roles = {
            "Category": row_dimensions,
            "Y": column_measures or row_measures,
            "Series": nominal_color_dimensions,
        }
        return "clusteredBarChart", roles, dropped, errors
    elif mark_class == "bar":
        visual_type = "clusteredBarChart"
        if row_dimensions and column_measures:
            roles = {"Category": row_dimensions, "Y": column_measures}
        elif column_dimensions and row_measures:
            roles = {"Category": column_dimensions, "Y": row_measures}
            visual_type = "clusteredColumnChart"
        else:
            errors.append("Bar worksheet lacks a dimension/measure shelf pairing")
        if roles:
            if nominal_color_dimensions:
                roles["Series"] = nominal_color_dimensions
            return visual_type, roles, dropped, errors
    elif mark_class in {"line", "area"}:
        if column_dimensions and all_measures:
            roles = {"Category": column_dimensions, "Y": all_measures}
            if nominal_color_dimensions:
                roles["Series"] = nominal_color_dimensions
            return "lineChart", roles, dropped, errors
        if row_dimensions and all_measures:
            roles = {"Category": row_dimensions, "Y": all_measures}
            if nominal_color_dimensions:
                roles["Series"] = nominal_color_dimensions
            return "clusteredBarChart", roles, dropped, errors
        errors.append("Line worksheet lacks a mapped category or measure")
    elif mark_class == "pie":
        category = color_dimensions or row_dimensions + column_dimensions
        values = [
            field for field in shelves["wedge-size"] if "measure" in field
        ] or shelf_measures
        if category and values:
            return (
                "pieChart",
                {"Category": _unique_fields(category), "Y": _unique_fields(values)},
                dropped,
                errors,
            )
        errors.append("Pie worksheet lacks a mapped category or measure")
    elif mark_class in {"text", "square", "automatic"}:
        has_dimensions = bool(all_dimensions)
        if has_dimensions and row_dimensions and column_dimensions:
            roles = {
                "Rows": row_dimensions,
                "Columns": column_dimensions,
                "Values": table_values,
            }
            if table_values:
                return "pivotTable", roles, dropped, errors
            errors.append("Pivot worksheet has no mapped measure values")
        elif has_dimensions:
            values = _unique_fields(
                rows + cols + encoded_dimensions + table_values
            )
            if values:
                return "tableEx", {"Values": values}, dropped, errors
            errors.append("Text/table worksheet has no mapped fields")
        elif all_measures:
            roles = {"Values": all_measures[:1]}
            for extra in all_measures[1:]:
                dropped.append(
                    f"{next(iter(extra.values()))} (additional card measure omitted)"
                )
            return "card", roles, dropped, errors
        else:
            errors.append("Text/table worksheet has no mapped fields")
    elif mark_class in {"circle", "shape"}:
        if row_measures and column_measures:
            detail = _unique_fields(
                [
                    field
                    for encoding in ("lod", "detail", "text")
                    for field in shelves[encoding]
                    if "column" in field
                ]
            )
            roles = {"X": column_measures, "Y": row_measures}
            if detail:
                roles["Category"] = detail
            return "scatterChart", roles, dropped, errors
        if row_dimensions and column_dimensions:
            roles = {
                "Rows": row_dimensions,
                "Columns": column_dimensions,
                "Values": table_values,
            }
            if table_values:
                return "pivotTable", roles, dropped, errors
            errors.append("Pivot worksheet has no mapped measure values")
        elif row_dimensions or column_dimensions:
            values = _unique_fields(rows + cols + table_values)
            if values:
                return "tableEx", {"Values": values}, dropped, errors
        else:
            errors.append("Circle/shape worksheet lacks mapped axes")
    else:
        errors.append(f"Unsupported mark class {mark_class or 'unknown'}")

    return "", {}, dropped, errors


def _text_runs(runs: list[TextRun]) -> list[list[dict[str, object]]]:
    paragraph: list[dict[str, object]] = []
    for run in runs:
        value: dict[str, object] = {"text": run.text, "bold": run.bold}
        if run.fontname:
            value["font_family"] = run.fontname
        if run.fontcolor:
            value["color"] = run.fontcolor
        if run.fontsize:
            match = re.search(r"\d+(?:\.\d+)?", run.fontsize)
            if match:
                value["font_size"] = float(match.group())
        paragraph.append(value)
    if not paragraph:
        paragraph = [{"text": "", "bold": False}]
    return [paragraph]


def _placeholder(text: str) -> dict[str, object]:
    return {
        "type": "textbox",
        "align": "left",
        "paragraphs": [
            [
                {
                    "text": text,
                    "font_family": "Segoe UI",
                    "font_size": 9,
                }
            ]
        ],
    }


def _zone_background(zone: Zone) -> str | None:
    background = zone.style.get("background-color")
    return background if isinstance(background, str) and background else None


def _zone_visual(
    zone: Zone,
    dashboard: Dashboard,
    zone_index: int,
    workbook: Workbook,
    model_fields: dict[str, str],
    translations: dict[str, CalcTranslation],
    measures_map: dict[str, str],
    auto_measure_names: set[str],
    date_column_names: set[str],
    caption_map: dict[str, str],
    image_names: set[str],
    worksheet_by_name: dict[str, Worksheet],
    page_by_worksheet: dict[str, str],
    page_names: set[str],
    toggle_initially_hidden: bool = False,
    toggle_bookmark_prefix: str | None = None,
) -> tuple[
    list[dict[str, object]],
    str,
    str | None,
    list[str],
    list[str],
]:
    zone_kind = zone.type_v2.casefold().strip()
    worksheet = worksheet_by_name.get(zone.name)
    prefix = f"z_{zone_index}_{zone.id or 'zone'}"
    visual_id = visual_folder_name(prefix)[:50]
    geometry = {
        "id": visual_id,
        "x": zone.x,
        "y": zone.y,
        "w": max(zone.w, 1),
        "h": max(zone.h, 1),
    }
    if zone.hidden_by_user:
        geometry["hidden"] = True

    if zone.button is not None:
        image_files = [
            image.replace("\\", "/").strip("/")
            for image in zone.button.images
        ]
        if zone.button.kind == "toggle":
            if len(image_files) < 2:
                message = f"Toggle button {zone.id} does not have two visual states"
                return (
                    [{**geometry, **_placeholder(message)}],
                    "textbox",
                    message,
                    [],
                    [],
                )
            shown_id = visual_folder_name(f"{visual_id}_shown")[:50]
            hidden_id = visual_folder_name(f"{visual_id}_hidden")[:50]
            bookmark_prefix = toggle_bookmark_prefix or zone.id
            shown = {
                **geometry,
                "id": shown_id,
                "type": "image",
                "file": image_files[0],
                "scaling": "fit",
                "action": {
                    "type": "bookmark",
                    "target": f"{bookmark_prefix}_hidden",
                },
                "hidden": zone.hidden_by_user or toggle_initially_hidden,
            }
            hidden = {
                **geometry,
                "id": hidden_id,
                "type": "image",
                "file": image_files[1],
                "scaling": "fit",
                "action": {
                    "type": "bookmark",
                    "target": f"{bookmark_prefix}_shown",
                },
                "hidden": zone.hidden_by_user or not toggle_initially_hidden,
            }
            if any(file_name not in image_names for file_name in image_files[:2]):
                missing = [
                    file_name
                    for file_name in image_files[:2]
                    if file_name not in image_names
                ]
                message = f"Button image file not found for zone {zone.id}: {', '.join(missing)}"
                return (
                    [{**geometry, **_placeholder(message)}],
                    "textbox",
                    message,
                    [],
                    [],
                )
            return [shown, hidden], "image", None, [], []

        if not image_files:
            message = f"Button zone {zone.id} has no image state"
            return (
                [{**geometry, **_placeholder(message)}],
                "textbox",
                message,
                [],
                [],
            )
        active_state = zone.button.active_state
        image_index = (
            active_state
            if 0 <= active_state < len(image_files)
            else 0
        )
        file_name = image_files[image_index]
        if file_name not in image_names:
            message = f"Button image file not found for zone {zone.id}: {file_name}"
            return (
                [{**geometry, **_placeholder(message)}],
                "textbox",
                message,
                [],
                [],
            )
        image_visual: dict[str, object] = {
            **geometry,
            "type": "image",
            "file": file_name,
            "scaling": "fit",
        }
        substitutions: list[str] = []
        if zone.button.kind == "goto":
            target = workbook.window_ids.get(zone.button.target_window_id)
            if target in page_names:
                image_visual["action"] = {"type": "page", "target": target}
            else:
                substitutions.append(
                    f"Button {zone.id}: unresolved page target "
                    f"{zone.button.target_window_id or '(missing window ID)'}"
                )
        elif zone.button.kind == "export":
            export_type = f" ({zone.button.export_type})" if zone.button.export_type else ""
            substitutions.append(
                f"Button {zone.id}{export_type}: Power BI: File > Export"
            )
        else:
            substitutions.append(
                f"Button {zone.id}: emitted as an image without an action"
            )
        return [image_visual], "image", None, [], substitutions

    background = _zone_background(zone)
    if zone_kind == "empty":
        if background:
            return (
                [{**geometry, "type": "shape", "fill": background}],
                "shape",
                None,
                [],
                [],
            )
        return [], "dropped: empty zone", None, [], []
    if zone.friendly_name.casefold() in {"divider", "divier"} and not background:
        return [], "dropped: divider", None, [], []
    if (
        zone_kind in {"dashboard-object", "layout-basic", "layout-flow"}
        and worksheet is None
        and not zone.text_runs
        and not zone.name
        and not zone.friendly_name
        and not zone.param
        and not background
    ):
        return [], "dropped: empty container", None, [], []

    if zone_kind in {"bitmap", "image"}:
        file_name = zone.param.replace("\\", "/").strip("/")
        if file_name in image_names:
            action: dict[str, str] | None = None
            for workbook_action in workbook.actions:
                command = workbook_action.command.casefold()
                if not any(token in command for token in ("goto", "go-to", "navigation")):
                    continue
                if (
                    workbook_action.source_dashboard
                    and workbook_action.source_dashboard != dashboard.name
                ):
                    continue
                target = workbook_action.target
                zone_labels = {
                    zone.name,
                    zone.friendly_name,
                    zone.param,
                }
                if workbook_action.source_worksheet:
                    if workbook_action.source_worksheet not in zone_labels:
                        continue
                elif (
                    workbook_action.name not in zone_labels
                    and target not in zone_labels
                ):
                    continue
                target_page = (
                    target
                    if target in page_names
                    else page_by_worksheet.get(target)
                )
                if target_page is not None:
                    action = {"type": "page", "target": target_page}
                    break
            image_visual: dict[str, object] = {
                **geometry,
                "type": "image",
                "file": file_name,
                "scaling": "fit",
            }
            if action is not None:
                image_visual["action"] = action
            return [image_visual], "image", None, [], []
        message = f"Image file not found for zone {zone.id}: {file_name or zone.name}"
        return [{**geometry, **_placeholder(message)}], "textbox", message, [], []
    if zone_kind == "text":
        paragraphs = _text_runs(zone.text_runs)
        if not any(str(run.get("text", "")) for run in paragraphs[0]):
            message = zone.friendly_name or zone.name or f"Text zone {zone.id}"
            paragraphs = _placeholder(message)["paragraphs"]
        return (
            [
                {
                    **geometry,
                    "type": "textbox",
                    "align": "left",
                    "paragraphs": paragraphs,
                }
            ],
            "textbox",
            None,
            [],
            [],
        )
    if zone_kind in {"filter", "paramctrl", "parameter-control", "parameter_control"}:
        raw_references = _FIELD_REFERENCE.findall(zone.param)
        if raw_references:
            mapped = _resolve_field(
                raw_references[0],
                workbook,
                model_fields,
                translations,
                measures_map,
                auto_measure_names,
                date_column_names,
                caption_map,
                column_only=True,
            )
        else:
            mapped = None
        if mapped is not None and mapped[0] == "column":
            return (
                [
                    {
                        **geometry,
                        "type": "slicer",
                        "field": {"column": mapped[1]},
                        "mode": "dropdown",
                    }
                ],
                "slicer",
                None,
                [],
                [],
            )
        label = zone.name or zone.friendly_name or zone.param or f"Filter {zone.id}"
        message = f"Unmapped filter/control: {label}"
        return [{**geometry, **_placeholder(message)}], "textbox", message, [], []
    if worksheet is not None:
        visual_type, roles, dropped, substitutions = _roles_for_worksheet(
            worksheet,
            workbook,
            model_fields,
            translations,
            measures_map,
            auto_measure_names,
            date_column_names,
            caption_map,
        )
        if visual_type:
            return (
                [
                    {
                        **geometry,
                        "type": "native",
                        "visual_type": visual_type,
                        "roles": roles,
                        "title": worksheet.name,
                    }
                ],
                f"native:{visual_type}",
                None,
                dropped,
                substitutions,
            )
        message = (
            f"Unmapped worksheet {worksheet.name}: {'; '.join(substitutions)}"
            if substitutions
            else "Unmapped worksheet"
        )
        return (
            [{**geometry, **_placeholder(message)}],
            "textbox",
            message,
            dropped,
            [],
        )
    label = zone.name or zone.friendly_name or f"{zone_kind or 'unknown'} zone {zone.id}"
    message = f"Unmapped dashboard zone: {label}"
    return [{**geometry, **_placeholder(message)}], "textbox", message, [], []


def _copy_workbook_images(
    source_paths: list[Path], source_root: Path, images_dir: Path, force: bool
) -> set[str]:
    names: set[str] = set()
    for source in source_paths:
        relative = source.relative_to(source_root)
        if relative.is_absolute() or ".." in relative.parts:
            continue
        destination = images_dir / relative
        if not destination.exists() or force:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        names.add(relative.as_posix())
    return names


def _report_markdown(
    records: list[dict[str, str]],
    unmapped: list[dict[str, str]],
    translations: list[dict[str, object]],
    dropped_fields: list[str],
    substitutions: list[str],
) -> str:
    def cell(value: object) -> str:
        return str(value).replace("|", "\\|").replace("\r\n", "<br>")

    lines = [
        "# Tableau scaffold report",
        "",
        "## Dashboard zones",
        "",
        "| Dashboard | Zone | Source | Emitted type |",
        "|---|---|---|---|",
    ]
    for record in records:
        lines.append(
            f"| {cell(record['dashboard'])} | `{cell(record['zone'])}` | "
            f"{cell(record['source'])} | {cell(record['visual_type'])} |"
        )
    lines.extend(["", "## Unmapped entries", ""])
    if unmapped:
        for entry in unmapped:
            lines.append(
                f"- **{cell(entry['dashboard'])} / {cell(entry['zone'])}** "
                f"({cell(entry['source'])}): {cell(entry['reason'])}"
            )
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Dropped fields / substitutions",
            "",
            "### Dropped fields",
        ]
    )
    if dropped_fields:
        lines.extend(f"- {item}" for item in dropped_fields)
    else:
        lines.append("- None.")
    lines.extend(["", "### Substitutions"])
    if substitutions:
        lines.extend(f"- {item}" for item in substitutions)
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Calculation translation status",
            "",
            "| Calculation | Status | Class | Source formula | Reason | DAX |",
            "|---|---|---|---|---|---|",
        ]
    )
    for record in translations:
        lines.append(
            f"| {cell(record['caption'])} | {cell(record['status'])} | "
            f"{cell(record['classification'])} | {cell(record.get('formula') or '')} | "
            f"{cell(record.get('reason') or '')} | {cell(record.get('dax') or '')} |"
        )
    if not translations:
        lines.append("| - | - | - | - | - | - |")
    lines.append("")
    return "\n".join(lines)


def scaffold_workbook(
    twbx: Path,
    out_dir: Path,
    *,
    force: bool = False,
) -> dict[str, object]:
    twbx = Path(twbx)
    out_dir = Path(out_dir)
    layout_path = out_dir / "layout.yml"
    if layout_path.exists() and not force:
        raise FileExistsError(
            f"Refusing to overwrite {layout_path}; pass --force to replace it"
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    overrides_dir = out_dir / "overrides"
    overrides_dir.mkdir(parents=True, exist_ok=True)
    measures_path = overrides_dir / "measures.yml"
    if not measures_path.exists():
        measures_path.write_text("measures: {}\n", encoding="utf-8")
    model_path = overrides_dir / "model.yml"
    if not model_path.exists():
        model_path.write_text(
            "calculated_columns: []\ncalculated_tables: []\nrelationships: []\n",
            encoding="utf-8",
        )

    with tempfile.TemporaryDirectory(prefix="tableau2pbip-scaffold-") as temporary:
        working = Path(temporary)
        unpacked = unpack(twbx, working)
        workbook = parse_workbook(unpacked.twb_path)
        translations_by_name = CalculationCompiler(workbook).compile_all()
        auto_measures, measures_map, date_columns = generate_auto_measures(
            workbook, translations_by_name
        )
        measure_overrides = _load_overrides(overrides_dir)
        model_overrides = load_model_overrides(overrides_dir)
        model_fields = _model_field_types(
            workbook,
            translations_by_name,
            auto_measures,
            date_columns,
            measure_overrides,
            model_overrides,
            {},
        )
        images_dir = out_dir / "images"
        image_names = _copy_workbook_images(
            unpacked.image_paths, unpacked.twb_path.parent, images_dir, force
        )
        worksheet_by_name = {item.name: item for item in workbook.worksheets}
        page_by_worksheet: dict[str, str] = {}
        for dashboard in workbook.dashboards:
            for zone in _leaf_zones(dashboard.zones):
                if zone.name in worksheet_by_name:
                    page_by_worksheet[zone.name] = dashboard.name
        page_names = {dashboard.name for dashboard in workbook.dashboards}
        caption_map = _workbook_field_names(workbook)
        auto_measure_names = {measure.name for measure in auto_measures}
        date_column_names = {column.name for column in date_columns}
        layout_pages: list[dict[str, object]] = []
        layout_bookmarks: list[dict[str, object]] = []
        records: list[dict[str, str]] = []
        unmapped: list[dict[str, str]] = []
        dropped_fields: list[str] = []
        substitutions: list[str] = []
        visual_counts: dict[str, dict[str, int]] = {}
        toggle_bookmark_names: set[str] = set()

        for dashboard in workbook.dashboards:
            visuals: list[dict[str, object]] = []
            counts: Counter[str] = Counter()
            leaf_entries = list(_leaf_zones_with_ancestors(dashboard.zones))
            zone_by_id: dict[str, Zone] = {}
            for root_zone in dashboard.zones:
                pending = [root_zone]
                while pending:
                    current = pending.pop()
                    zone_by_id[current.id] = current
                    pending.extend(current.children)
            zone_visual_ids: dict[str, list[str]] = {}
            toggle_buttons: list[
                tuple[Zone, list[dict[str, object]], str]
            ] = []
            for zone_index, (zone, ancestors) in enumerate(leaf_entries):
                worksheet = worksheet_by_name.get(zone.name)
                source = (
                    worksheet.name
                    if worksheet is not None
                    else zone.name
                    or zone.friendly_name
                    or (
                        f"{zone.button.kind} button"
                        if zone.button is not None
                        else zone.param
                    )
                )
                toggle_initially_hidden = bool(
                    zone.button is not None
                    and zone.button.kind == "toggle"
                    and any(
                        zone_by_id.get(target_id) is not None
                        and zone_by_id[target_id].hidden_by_user
                        for target_id in zone.button.toggle_zone_ids
                    )
                )
                bookmark_prefix = zone.id
                if zone.button is not None and zone.button.kind == "toggle":
                    bookmark_prefix = zone.id or visual_folder_name(
                        f"{dashboard.name}_{zone_index}"
                    )
                    if f"{bookmark_prefix}_shown" in toggle_bookmark_names:
                        dashboard_prefix = re.sub(
                            r"[^A-Za-z0-9_]+", "_", dashboard.name
                        ).strip("_")
                        bookmark_prefix = f"{dashboard_prefix}_{bookmark_prefix}"
                    suffix = 2
                    base_prefix = bookmark_prefix
                    while f"{bookmark_prefix}_shown" in toggle_bookmark_names:
                        bookmark_prefix = f"{base_prefix}_{suffix}"
                        suffix += 1
                    toggle_bookmark_names.update(
                        {
                            f"{bookmark_prefix}_shown",
                            f"{bookmark_prefix}_hidden",
                        }
                    )
                zone_visuals, emitted_type, reason, dropped, replaced = _zone_visual(
                    zone,
                    dashboard,
                    zone_index,
                    workbook,
                    model_fields,
                    translations_by_name,
                    measures_map,
                    auto_measure_names,
                    date_column_names,
                    caption_map,
                    image_names,
                    worksheet_by_name,
                    page_by_worksheet,
                    page_names,
                    toggle_initially_hidden,
                    bookmark_prefix,
                )
                if zone.button is not None and zone.button.kind == "toggle":
                    toggle_buttons.append((zone, zone_visuals, bookmark_prefix))
                records.append(
                    {
                        "dashboard": dashboard.name,
                        "zone": zone.id,
                        "source": source or zone.type_v2 or "zone",
                        "visual_type": (
                            f"{emitted_type} (x{len(zone_visuals)})"
                            if len(zone_visuals) > 1
                            else emitted_type
                        ),
                    }
                )
                if reason:
                    unmapped.append(
                        {
                            "dashboard": dashboard.name,
                            "zone": zone.id,
                            "source": source or zone.type_v2 or "zone",
                            "reason": reason,
                        }
                    )
                for item in dropped:
                    dropped_fields.append(
                        f"{dashboard.name} / {source or zone.id}: {item}"
                    )
                for item in replaced:
                    if item.startswith("map → bar"):
                        item = f"{worksheet.name if worksheet is not None else source}: {item}"
                    substitutions.append(f"{dashboard.name}: {item}")
                visuals.extend(zone_visuals)
                for item in zone_visuals:
                    item_type = str(item.get("type", "unknown"))
                    count_name = (
                        f"native:{item.get('visual_type', 'unknown')}"
                        if item_type == "native"
                        else item_type
                    )
                    counts[count_name] += 1
                emitted_ids = [
                    str(item["id"]) for item in zone_visuals if item.get("id")
                ]
                for ancestor_id in ancestors:
                    zone_visual_ids.setdefault(ancestor_id, []).extend(emitted_ids)

            for zone, button_visuals, bookmark_prefix in toggle_buttons:
                if len(button_visuals) != 2 or zone.button is None:
                    continue
                shown_id = str(button_visuals[0]["id"])
                hidden_id = str(button_visuals[1]["id"])
                container_ids = _unique_strings(
                    [
                        visual_id
                        for target_id in zone.button.toggle_zone_ids
                        for visual_id in zone_visual_ids.get(target_id, [])
                    ]
                )
                targets = _unique_strings(
                    [*container_ids, shown_id, hidden_id]
                )
                layout_bookmarks.extend(
                    [
                        {
                            "name": f"{bookmark_prefix}_shown",
                            "page": dashboard.name,
                            "targets": targets,
                            "hidden": [hidden_id],
                        },
                        {
                            "name": f"{bookmark_prefix}_hidden",
                            "page": dashboard.name,
                            "targets": targets,
                            "hidden": [*container_ids, shown_id],
                        },
                    ]
                )
            page: dict[str, object] = {
                "tableau_dashboard": dashboard.name,
                "visuals": visuals,
            }
            layout_pages.append(page)
            visual_counts[dashboard.name] = dict(counts)

        report: dict[str, object] = {"images_dir": "images"}
        background = next(
            (
                dashboard.page_background
                for dashboard in workbook.dashboards
                if dashboard.page_background
            ),
            None,
        )
        if background is not None:
            report["page_background"] = background
        layout_document = {"report": report, "pages": layout_pages}
        if layout_bookmarks:
            layout_document["bookmarks"] = layout_bookmarks
        layout_path.write_text(
            yaml.safe_dump(
                layout_document,
                sort_keys=False,
                allow_unicode=True,
                width=120,
            ),
            encoding="utf-8",
        )

        translation_records = [
            {
                "caption": calc.caption,
                "status": translations_by_name[calc.internal_name].status,
                "classification": translations_by_name[
                    calc.internal_name
                ].classification,
                "reason": translations_by_name[calc.internal_name].reason,
                "dax": translations_by_name[calc.internal_name].dax,
                "formula": calc.formula_raw,
            }
            for calc in workbook.calcs
        ]
        (out_dir / "SCAFFOLD_REPORT.md").write_text(
            _report_markdown(
                records,
                unmapped,
                translation_records,
                dropped_fields,
                substitutions,
            ),
            encoding="utf-8",
        )
        load_layout(layout_path, workbook.dashboards, model_fields)

    return {
        "workbook": _project_name(workbook),
        "layout": str(layout_path),
        "report": str(out_dir / "SCAFFOLD_REPORT.md"),
        "pages": len(layout_pages),
        "visual_counts": visual_counts,
        "unmapped_count": len(unmapped),
        "unsupported_calculations": sum(
            record["status"] in {"unsupported", "table_calc"}
            for record in translation_records
        ),
        "needs_override_calculations": sum(
            record["status"] == "needs_override"
            for record in translation_records
        ),
        "copied_images": len(image_names),
    }
