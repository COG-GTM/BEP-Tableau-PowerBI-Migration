from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import yaml

from tableau2pbip import visuals as visual_builders
from tableau2pbip.ir import Dashboard


@dataclass(frozen=True, slots=True)
class LayoutConfig:
    page_background: str | None
    pages: dict[str, list[dict[str, object]]]
    bookmarks: list[dict[str, object]]
    images_dir: Path


def _mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValueError(f"{context} must be a YAML mapping with string keys")
    return value


def _unknown_keys(
    value: dict[str, object], allowed: set[str], context: str
) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"Unknown keys in {context}: {', '.join(sorted(unknown))}")


def _required_string(
    value: dict[str, object], key: str, context: str
) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise ValueError(f"{context} needs a non-empty {key!r} string")
    return item.strip()


def _optional_bool(
    value: dict[str, object], key: str, default: bool, context: str
) -> bool:
    item = value.get(key, default)
    if not isinstance(item, bool):
        raise ValueError(f"{context} {key!r} must be a boolean")
    return item


def _number(value: object, context: str) -> int | float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise ValueError(f"{context} must be a finite number")
    return value


def visual_folder_name(value: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9_]", "_", value).strip("_") or "visual"
    if len(sanitized) > 50:
        suffix = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
        sanitized = f"{sanitized[:41]}_{suffix}"
    return sanitized


def _bookmark_file_name(value: str) -> str:
    return visual_folder_name(value)


def _field_reference(
    value: object,
    model_fields: dict[str, str],
    context: str,
) -> tuple[str, str, str]:
    if not isinstance(value, str) or "." not in value:
        raise ValueError(f"{context} must use the 'Table.Column' form")
    table, _, column = value.rpartition(".")
    if not table.strip() or not column.strip():
        raise ValueError(f"{context} must use the 'Table.Column' form")
    reference = f"{table}.{column}"
    if reference not in model_fields:
        raise ValueError(f"Unknown model field {reference!r} in {context}")
    return reference, table, column


def _validate_image_path(images_dir: Path, file_name: str, context: str) -> Path:
    relative = Path(file_name)
    if relative.is_absolute():
        raise ValueError(f"{context} file must be relative to report.images_dir")
    root = images_dir.resolve()
    source = (root / relative).resolve()
    if not source.is_relative_to(root):
        raise ValueError(f"{context} file must stay inside report.images_dir")
    if not source.is_file():
        raise ValueError(f"{context} image file does not exist: {source}")
    return source


def _validate_text_paragraphs(
    value: object, context: str
) -> list[list[dict[str, object]]]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{context} paragraphs must be a non-empty list")
    result: list[list[dict[str, object]]] = []
    for paragraph_index, raw_paragraph in enumerate(value):
        paragraph_context = f"{context} paragraphs[{paragraph_index}]"
        if not isinstance(raw_paragraph, list) or not raw_paragraph:
            raise ValueError(f"{paragraph_context} must be a non-empty list of runs")
        paragraph: list[dict[str, object]] = []
        for run_index, raw_run in enumerate(raw_paragraph):
            run_context = f"{paragraph_context}[{run_index}]"
            run = _mapping(raw_run, run_context)
            _unknown_keys(
                run,
                {
                    "text",
                    "font_family",
                    "font_size",
                    "color",
                    "bold",
                    "letter_spacing",
                },
                run_context,
            )
            normalized: dict[str, object] = {
                "text": _required_string(run, "text", run_context),
                "bold": _optional_bool(run, "bold", False, run_context),
            }
            for key in ("font_family", "color"):
                if key in run:
                    normalized[key] = _required_string(run, key, run_context)
            if "font_size" in run:
                normalized["font_size"] = _number(
                    run["font_size"], f"{run_context} font_size"
                )
            if "letter_spacing" in run:
                normalized["letter_spacing"] = _number(
                    run["letter_spacing"], f"{run_context} letter_spacing"
                )
            paragraph.append(normalized)
        result.append(paragraph)
    return result


def _validate_slicer_style(value: object, context: str) -> dict[str, object]:
    style = _mapping(value, context)
    _unknown_keys(
        style,
        {
            "font_family",
            "font_size",
            "font_color",
            "background",
            "border_color",
            "header",
        },
        context,
    )
    normalized: dict[str, object] = {}
    for key in ("font_family", "font_color", "background", "border_color"):
        if key in style:
            normalized[key] = _required_string(style, key, context)
    if "font_size" in style:
        normalized["font_size"] = _number(style["font_size"], f"{context} font_size")
    if "header" in style:
        normalized["header"] = _optional_bool(style, "header", True, context)
    return normalized


def _validate_native_style(value: object, context: str) -> dict[str, object]:
    style = _mapping(value, context)
    _unknown_keys(
        style,
        {"font_color", "font_family", "value_color", "value_font_size"},
        context,
    )
    normalized: dict[str, object] = {}
    for key in ("font_color", "font_family", "value_color"):
        if key in style:
            normalized[key] = _required_string(style, key, context)
    if "value_font_size" in style:
        normalized["value_font_size"] = _number(
            style["value_font_size"], f"{context} value_font_size"
        )
    return normalized


def _validate_visual(
    value: object,
    context: str,
    order: int,
    model_fields: dict[str, str],
    images_dir: Path,
    dashboard_names: set[str],
) -> dict[str, object]:
    raw = _mapping(value, context)
    visual_type = _required_string(raw, "type", context)
    if visual_type not in {"deneb", "native", "slicer", "image", "shape", "textbox"}:
        raise ValueError(f"{context} has unknown visual type {visual_type!r}")
    common = {"id", "type", "x", "y", "w", "h", "z", "hidden"}
    allowed_by_type = {
        "deneb": common | {"fields", "spec", "cross_filter", "tooltips"},
        "native": common | {"visual_type", "roles", "title", "style"},
        "slicer": common
        | {"field", "mode", "single_select", "default", "sync_group", "style"},
        "image": common | {"file", "scaling", "action"},
        "shape": common | {"fill", "transparency"},
        "textbox": common | {"align", "paragraphs"},
    }
    _unknown_keys(raw, allowed_by_type[visual_type], context)
    visual_id = _required_string(raw, "id", context)
    geometry: dict[str, int | float] = {}
    for coordinate in ("x", "y", "w", "h"):
        if coordinate not in raw:
            raise ValueError(f"{context} needs a {coordinate!r} coordinate")
        geometry[coordinate] = _number(raw[coordinate], f"{context} {coordinate}")
    if geometry["w"] <= 0 or geometry["h"] <= 0:
        raise ValueError(f"{context} w and h must be greater than zero")
    z = _number(raw.get("z", order * 100), f"{context} z")
    normalized: dict[str, object] = {
        "id": visual_id,
        "folder": visual_folder_name(visual_id),
        "type": visual_type,
        **geometry,
        "z": z,
        "hidden": _optional_bool(raw, "hidden", False, context),
    }

    if visual_type == "deneb":
        raw_fields = raw.get("fields", [])
        if not isinstance(raw_fields, list):
            raise ValueError(f"{context} fields must be a list")
        fields: list[dict[str, str]] = []
        for field_index, raw_field in enumerate(raw_fields):
            field_context = f"{context} fields[{field_index}]"
            field = _mapping(raw_field, field_context)
            _unknown_keys(field, {"column", "measure", "as"}, field_context)
            kinds = [key for key in ("column", "measure") if key in field]
            if len(kinds) != 1:
                raise ValueError(
                    f"{field_context} must contain exactly one of 'column' or 'measure'"
                )
            kind = kinds[0]
            reference, _, column = _field_reference(
                field[kind], model_fields, f"{field_context} {kind}"
            )
            alias_value = field.get("as", column)
            if not isinstance(alias_value, str) or not alias_value.strip():
                raise ValueError(f"{field_context} 'as' must be a non-empty string")
            fields.append(
                {"kind": kind, "reference": reference, "alias": alias_value.strip()}
            )
        spec = _mapping(raw.get("spec"), f"{context} spec")
        _unknown_keys(spec, {"component", "params"}, f"{context} spec")
        component = _required_string(spec, "component", f"{context} spec")
        params_value = spec.get("params", {})
        params = _mapping(params_value, f"{context} spec params")
        normalized["fields"] = fields
        normalized["spec"] = {"component": component, "params": params}
        normalized["cross_filter"] = _optional_bool(
            raw, "cross_filter", True, context
        )
        normalized["tooltips"] = _optional_bool(raw, "tooltips", True, context)
    elif visual_type == "native":
        native_type = _required_string(raw, "visual_type", context)
        supported_native_types = {
            "clusteredBarChart",
            "clusteredColumnChart",
            "lineChart",
            "tableEx",
            "card",
            "pieChart",
            "donutChart",
            "pivotTable",
            "scatterChart",
        }
        if native_type not in supported_native_types:
            raise ValueError(
                f"{context} has unsupported native visual type {native_type!r}"
            )
        if native_type in {"tableEx", "card"}:
            allowed_roles = {"Values"}
        elif native_type == "pivotTable":
            allowed_roles = {"Rows", "Columns", "Values"}
        elif native_type == "scatterChart":
            allowed_roles = {"Category", "X", "Y"}
        elif native_type in {
            "clusteredBarChart",
            "clusteredColumnChart",
            "lineChart",
        }:
            allowed_roles = {"Category", "Y", "Series"}
        else:
            allowed_roles = {"Category", "Y"}
        roles_value = _mapping(raw.get("roles"), f"{context} roles")
        roles: dict[str, list[dict[str, str]]] = {}
        for role, role_fields_value in roles_value.items():
            if role not in allowed_roles:
                raise ValueError(
                    f"{context} role {role!r} is not supported by {native_type}"
                )
            if not isinstance(role_fields_value, list):
                raise ValueError(f"{context} roles.{role} must be a list")
            role_fields: list[dict[str, str]] = []
            for field_index, raw_field in enumerate(role_fields_value):
                field_context = f"{context} roles.{role}[{field_index}]"
                field = _mapping(raw_field, field_context)
                _unknown_keys(field, {"column", "measure"}, field_context)
                kinds = [key for key in ("column", "measure") if key in field]
                if len(kinds) != 1:
                    raise ValueError(
                        f"{field_context} must contain exactly one of 'column' or 'measure'"
                    )
                kind = kinds[0]
                reference, _, column = _field_reference(
                    field[kind], model_fields, f"{field_context} {kind}"
                )
                role_fields.append(
                    {
                        "kind": kind,
                        "reference": reference,
                        "display_name": column,
                    }
                )
            roles[role] = role_fields
        normalized["visual_type"] = native_type
        normalized["roles"] = roles
        if "title" in raw:
            normalized["title"] = _required_string(raw, "title", context)
        if "style" in raw:
            normalized["style"] = _validate_native_style(
                raw["style"], f"{context} style"
            )
    elif visual_type == "slicer":
        field = _mapping(raw.get("field"), f"{context} field")
        _unknown_keys(field, {"column"}, f"{context} field")
        reference, _, _ = _field_reference(
            field.get("column"), model_fields, f"{context} field column"
        )
        mode = raw.get("mode", "dropdown")
        if not isinstance(mode, str) or mode not in {"dropdown", "list"}:
            raise ValueError(f"{context} mode must be 'dropdown' or 'list'")
        normalized["field"] = reference
        normalized["mode"] = mode
        normalized["single_select"] = _optional_bool(
            raw, "single_select", False, context
        )
        if "default" in raw:
            default = raw["default"]
            if not isinstance(default, list):
                raise ValueError(f"{context} default must be a list")
            normalized["default"] = default
        if "sync_group" in raw:
            normalized["sync_group"] = _required_string(raw, "sync_group", context)
        normalized["style"] = _validate_slicer_style(
            raw.get("style", {}), f"{context} style"
        )
    elif visual_type == "image":
        file_name = _required_string(raw, "file", context)
        _validate_image_path(images_dir, file_name, context)
        scaling = raw.get("scaling", "fit")
        if not isinstance(scaling, str) or scaling not in {"fit", "fill"}:
            raise ValueError(f"{context} scaling must be 'fit' or 'fill'")
        normalized["file"] = file_name
        normalized["scaling"] = scaling
        if "action" in raw:
            action = _mapping(raw["action"], f"{context} action")
            _unknown_keys(action, {"type", "target"}, f"{context} action")
            action_type = _required_string(action, "type", f"{context} action")
            if action_type not in {"page", "bookmark"}:
                raise ValueError(
                    f"{context} action type must be 'page' or 'bookmark'"
                )
            target = _required_string(action, "target", f"{context} action")
            if action_type == "page" and target not in dashboard_names:
                raise ValueError(
                    f"{context} action targets unknown Tableau dashboard {target!r}"
                )
            normalized["action"] = {"type": action_type, "target": target}
    elif visual_type == "shape":
        fill = _required_string(raw, "fill", context)
        transparency = _number(
            raw.get("transparency", 0), f"{context} transparency"
        )
        if transparency < 0 or transparency > 100:
            raise ValueError(f"{context} transparency must be between 0 and 100")
        normalized["fill"] = fill
        normalized["transparency"] = transparency
    elif visual_type == "textbox":
        align = raw.get("align", "left")
        if not isinstance(align, str) or align not in {"left", "center", "right"}:
            raise ValueError(f"{context} align must be left, center, or right")
        normalized["align"] = align
        normalized["paragraphs"] = _validate_text_paragraphs(
            raw.get("paragraphs"), context
        )
    return normalized


def load_layout(
    path: Path | None,
    dashboards: list[Dashboard],
    model_fields: dict[str, str],
) -> LayoutConfig:
    if path is None:
        return LayoutConfig(None, {}, [], Path.cwd())
    if not path.is_file():
        raise ValueError(f"Layout file does not exist: {path}")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    root = _mapping(loaded, str(path))
    _unknown_keys(root, {"report", "pages", "bookmarks"}, str(path))
    dashboard_names = {dashboard.name for dashboard in dashboards}

    report = _mapping(root.get("report", {}), f"{path} report")
    _unknown_keys(report, {"page_background", "images_dir"}, f"{path} report")
    page_background = report.get("page_background")
    if page_background is not None and not isinstance(page_background, str):
        raise ValueError(f"{path} report.page_background must be a string")
    images_dir_value = report.get("images_dir", ".")
    if not isinstance(images_dir_value, str) or not images_dir_value.strip():
        raise ValueError(f"{path} report.images_dir must be a non-empty path")
    if Path(images_dir_value).is_absolute():
        raise ValueError(f"{path} report.images_dir must be relative to the layout file")
    images_dir = (path.parent / images_dir_value).resolve()

    raw_pages = root.get("pages", [])
    if not isinstance(raw_pages, list):
        raise ValueError(f"{path} pages must be a list")
    pages: dict[str, list[dict[str, object]]] = {}
    for page_index, raw_page in enumerate(raw_pages):
        context = f"{path} pages[{page_index}]"
        page = _mapping(raw_page, context)
        _unknown_keys(page, {"tableau_dashboard", "visuals"}, context)
        dashboard = _required_string(page, "tableau_dashboard", context)
        if dashboard not in dashboard_names:
            raise ValueError(
                f"{context} names unknown Tableau dashboard {dashboard!r}"
            )
        if dashboard in pages:
            raise ValueError(f"{context} duplicates dashboard {dashboard!r}")
        raw_visuals = page.get("visuals", [])
        if not isinstance(raw_visuals, list):
            raise ValueError(f"{context} visuals must be a list")
        visuals: list[dict[str, object]] = []
        folder_names: set[str] = set()
        for visual_index, raw_visual in enumerate(raw_visuals):
            visual_context = f"{context} visuals[{visual_index}]"
            visual = _validate_visual(
                raw_visual,
                visual_context,
                visual_index,
                model_fields,
                images_dir,
                dashboard_names,
            )
            folder = str(visual["folder"])
            if folder in folder_names:
                raise ValueError(
                    f"{visual_context} id collides after folder-name sanitization"
                )
            folder_names.add(folder)
            visuals.append(visual)
        pages[dashboard] = visuals

    raw_bookmarks = root.get("bookmarks", [])
    if not isinstance(raw_bookmarks, list):
        raise ValueError(f"{path} bookmarks must be a list")
    bookmarks: list[dict[str, object]] = []
    bookmark_ids: set[str] = set()
    bookmark_names: set[str] = set()
    for bookmark_index, raw_bookmark in enumerate(raw_bookmarks):
        context = f"{path} bookmarks[{bookmark_index}]"
        bookmark = _mapping(raw_bookmark, context)
        _unknown_keys(
            bookmark, {"name", "page", "display_name", "hidden", "targets"}, context
        )
        name = _required_string(bookmark, "name", context)
        if name in bookmark_names:
            raise ValueError(f"{context} duplicates bookmark {name!r}")
        bookmark_names.add(name)
        bookmark_id = _bookmark_file_name(name)
        if bookmark_id in bookmark_ids:
            raise ValueError(
                f"{context} name collides after bookmark-name sanitization"
            )
        bookmark_ids.add(bookmark_id)
        page = _required_string(bookmark, "page", context)
        if page not in dashboard_names:
            raise ValueError(
                f"{context} targets unknown Tableau dashboard {page!r}"
            )
        page_visuals = pages.get(page, [])
        visual_ids = [str(visual["id"]) for visual in page_visuals]
        visual_id_set = set(visual_ids)
        targets = bookmark.get("targets", visual_ids)
        if not isinstance(targets, list) or any(
            not isinstance(item, str) for item in targets
        ):
            raise ValueError(f"{context} targets must be a list of visual ids")
        if len(targets) != len(set(targets)):
            raise ValueError(f"{context} targets must not contain duplicate ids")
        unknown_targets = set(targets) - visual_id_set
        if unknown_targets:
            raise ValueError(
                f"{context} targets unknown visual ids: "
                f"{', '.join(sorted(unknown_targets))}"
            )
        hidden = bookmark.get("hidden", [])
        if not isinstance(hidden, list) or any(
            not isinstance(item, str) for item in hidden
        ):
            raise ValueError(f"{context} hidden must be a list of visual ids")
        unknown_hidden = set(hidden) - visual_id_set
        if unknown_hidden:
            raise ValueError(
                f"{context} targets unknown visual ids: "
                f"{', '.join(sorted(unknown_hidden))}"
            )
        hidden_outside_targets = set(hidden) - set(targets)
        if hidden_outside_targets:
            raise ValueError(
                f"{context} hidden visual ids must be included in targets: "
                f"{', '.join(sorted(hidden_outside_targets))}"
            )
        normalized_bookmark: dict[str, object] = {
            "name": name,
            "bookmark_id": bookmark_id,
            "page": page,
            "targets": targets,
            "hidden": hidden,
        }
        if "display_name" in bookmark:
            normalized_bookmark["display_name"] = _required_string(
                bookmark, "display_name", context
            )
        bookmarks.append(normalized_bookmark)

    for dashboard, visuals in pages.items():
        for visual in visuals:
            action_value = visual.get("action")
            if not isinstance(action_value, dict):
                continue
            action_type = str(action_value["type"])
            target = str(action_value["target"])
            if action_type == "bookmark" and target not in bookmark_names:
                raise ValueError(
                    f"Image action on {dashboard!r} targets unknown bookmark "
                    f"{target!r}"
                )

    return LayoutConfig(page_background, pages, bookmarks, images_dir)


def _literal(value: str) -> dict[str, object]:
    return {"expr": {"Literal": {"Value": value}}}


def _pbi_string(value: str) -> dict[str, object]:
    escaped = value.replace("'", "''")
    return _literal(f"'{escaped}'")


def _pbi_number(value: int | float, suffix: str = "D") -> dict[str, object]:
    return _literal(f"{value:g}{suffix}")


def _color(value: str) -> dict[str, object]:
    return {"solid": {"color": _pbi_string(value)}}


def _native_style_objects(
    style: dict[str, object], visual_type: str
) -> dict[str, object]:
    font_color = style.get("font_color")
    font_family = style.get("font_family")
    if visual_type in {"tableEx", "pivotTable"}:
        properties: dict[str, object] = {}
        if isinstance(font_color, str):
            properties["fontColor"] = _color(font_color)
        if isinstance(font_family, str):
            properties["fontFamily"] = _pbi_string(font_family)
        return {
            name: [{"properties": properties.copy()}]
            for name in ("values", "columnHeaders", "rowHeaders")
            if properties
        }
    if visual_type == "card":
        properties = {}
        value_color = style.get("value_color", font_color)
        value_font_size = style.get("value_font_size")
        if isinstance(value_color, str):
            properties["color"] = _color(value_color)
        if isinstance(value_font_size, (int, float)) and not isinstance(
            value_font_size, bool
        ):
            properties["fontSize"] = _pbi_number(value_font_size)
        if isinstance(font_family, str):
            properties["fontFamily"] = _pbi_string(font_family)
        objects: dict[str, object] = {
            "categoryLabels": [{"properties": {"show": _literal("false")}}]
        }
        if properties:
            objects["labels"] = [{"properties": properties}]
        return objects

    objects = {}
    axis_properties: dict[str, object] = {}
    if isinstance(font_color, str):
        axis_properties["labelColor"] = _color(font_color)
    if isinstance(font_family, str):
        axis_properties["fontFamily"] = _pbi_string(font_family)
    if axis_properties and visual_type in {
        "clusteredBarChart",
        "clusteredColumnChart",
        "lineChart",
        "scatterChart",
    }:
        for name in ("categoryAxis", "valueAxis"):
            objects[name] = [{"properties": axis_properties.copy()}]

    legend_properties: dict[str, object] = {}
    if isinstance(font_color, str):
        legend_properties["labelColor"] = _color(font_color)
    if isinstance(font_family, str):
        legend_properties["fontFamily"] = _pbi_string(font_family)
    if legend_properties:
        objects["legend"] = [{"properties": legend_properties}]

    label_properties: dict[str, object] = {}
    if isinstance(font_color, str):
        label_properties["color"] = _color(font_color)
    if isinstance(font_family, str):
        label_properties["fontFamily"] = _pbi_string(font_family)
    if label_properties:
        objects["dataLabels"] = [{"properties": label_properties}]
    return objects


def _field_expr(kind: str, reference: str) -> dict[str, object]:
    table, _, column = reference.rpartition(".")
    return {
        kind: {
            "Expression": {"SourceRef": {"Entity": table}},
            "Property": column,
        }
    }


def _projection(
    kind: str, reference: str, alias: str, *, active: bool = False
) -> dict[str, object]:
    projection: dict[str, object] = {
        "field": _field_expr("Column" if kind == "column" else "Measure", reference),
        "queryRef": reference,
        "nativeQueryRef": alias,
        "displayName": alias,
    }
    if active:
        projection["active"] = True
    return projection


def _literal_value(value: object, datatype: str, context: str) -> dict[str, object]:
    if datatype in {"int64", "integer", "Int64.Type"}:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{context} default must be an integer")
        literal = f"{value}L"
    elif datatype in {"double", "real", "type number"}:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{context} default must be numeric")
        literal = f"{value:g}D"
    elif datatype in {"boolean", "bool"}:
        if not isinstance(value, bool):
            raise ValueError(f"{context} default must be boolean")
        literal = "true" if value else "false"
    else:
        literal = f"'{str(value).replace(chr(39), chr(39) * 2)}'"
    return {"Literal": {"Value": literal}}


def _filter_config(
    reference: str,
    default: list[object],
    datatype: str,
) -> dict[str, object]:
    table, _, column = reference.rpartition(".")
    expression = {
        "Column": {
            "Expression": {"SourceRef": {"Source": "s"}},
            "Property": column,
        }
    }
    return {
        "Version": 2,
        "From": [{"Name": "s", "Entity": table, "Type": 0}],
        "Where": [
            {
                "Condition": {
                    "In": {
                        "Expressions": [expression],
                        "Values": [
                            [_literal_value(value, datatype, reference)]
                            for value in default
                        ],
                    }
                }
            }
        ],
    }


def _merge_slicer_selection(
    visual_objects: dict[str, object], selection_filter: dict[str, object]
) -> None:
    general = visual_objects.setdefault("general", [])
    if not isinstance(general, list):
        raise ValueError("Internal layout error: slicer general objects are not a list")
    if general:
        first = general[0]
        if not isinstance(first, dict):
            raise ValueError("Internal layout error: slicer general entry is not a mapping")
        properties = first.get("properties")
        if not isinstance(properties, dict):
            raise ValueError("Internal layout error: slicer general properties are not a mapping")
    else:
        properties = {}
        general.append({"properties": properties})
    filter_properties = properties.setdefault("filter", {})
    if not isinstance(filter_properties, dict):
        raise ValueError("Internal layout error: slicer filter properties are not a mapping")
    filter_properties["filter"] = selection_filter


def _container_objects() -> dict[str, object]:
    disabled = [{"properties": {"show": _literal("false")}}]
    zero_padding = [
        {
            "properties": {
                side: _pbi_number(0)
                for side in ("top", "bottom", "left", "right")
            }
        }
    ]
    return {
        "title": disabled,
        "background": disabled,
        "border": disabled,
        "dropShadow": disabled,
        "visualHeader": disabled,
        "padding": zero_padding,
    }


def _slicer_objects(visual: dict[str, object]) -> dict[str, object]:
    style = visual["style"]
    if not isinstance(style, dict):
        raise ValueError("Internal layout error: slicer style is not a mapping")
    mode = "Dropdown" if visual["mode"] == "dropdown" else "Basic"
    objects: dict[str, object] = {
        "data": [{"properties": {"mode": _pbi_string(mode)}}],
        "selection": [
            {
                "properties": {
                    "singleSelect": _literal(
                        "true" if visual["single_select"] else "false"
                    )
                }
            }
        ],
    }
    header_value = style.get("header", True)
    objects["header"] = [
        {
            "properties": {
                "show": _literal("true" if header_value else "false")
            }
        }
    ]
    values: dict[str, object] = {}
    if "font_family" in style:
        values["fontFamily"] = _pbi_string(str(style["font_family"]))
    if "font_size" in style:
        values["fontSize"] = _pbi_number(_number(style["font_size"], "font_size"))
    if "font_color" in style:
        values["fontColor"] = _color(str(style["font_color"]))
    if values:
        objects["values"] = [{"properties": values}]
    if "background" in style:
        objects["background"] = [
            {
                "properties": {
                    "show": _literal("true"),
                    "color": _color(str(style["background"])),
                    "transparency": _pbi_number(0),
                }
            }
        ]
    if "border_color" in style:
        objects["border"] = [
            {
                "properties": {
                    "show": _literal("true"),
                    "color": _color(str(style["border_color"])),
                }
            }
        ]
    return objects


def _textbox_paragraphs(visual: dict[str, object]) -> list[dict[str, object]]:
    raw_paragraphs = visual["paragraphs"]
    if not isinstance(raw_paragraphs, list):
        raise ValueError("Internal layout error: textbox paragraphs are not a list")
    paragraphs: list[dict[str, object]] = []
    for raw_paragraph in raw_paragraphs:
        if not isinstance(raw_paragraph, list):
            raise ValueError("Internal layout error: textbox paragraph is not a list")
        text_runs: list[dict[str, object]] = []
        for raw_run in raw_paragraph:
            if not isinstance(raw_run, dict):
                raise ValueError("Internal layout error: textbox run is not a mapping")
            style: dict[str, str] = {}
            if "font_family" in raw_run:
                style["fontFamily"] = str(raw_run["font_family"])
            if "font_size" in raw_run:
                style["fontSize"] = f"{_number(raw_run['font_size'], 'font_size'):g}px"
            if "color" in raw_run:
                style["color"] = str(raw_run["color"])
            if raw_run.get("bold") is True:
                style["fontWeight"] = "bold"
            if "letter_spacing" in raw_run:
                style["letterSpacing"] = (
                    f"{_number(raw_run['letter_spacing'], 'letter_spacing'):g}px"
                )
            text_runs.append(
                {"value": str(raw_run["text"]), "textStyle": style}
            )
        paragraphs.append(
            {
                "textRuns": text_runs,
                "horizontalTextAlignment": str(visual["align"]),
            }
        )
    return paragraphs


def _resolve_registered_image(
    file_name: str,
    images_dir: Path,
    report_dir: Path,
    resource_items: dict[str, dict[str, str]],
) -> str:
    source = _validate_image_path(images_dir, file_name, "image visual")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    resource_name = source.name
    previous = resource_items.get(resource_name)
    if previous is not None and previous["digest"] != digest:
        path = Path(resource_name)
        resource_name = (
            f"{path.stem}_{digest[:8]}{path.suffix}"
        )
    if resource_name not in resource_items:
        destination_dir = report_dir / "StaticResources" / "RegisteredResources"
        destination_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination_dir / resource_name)
        resource_items[resource_name] = {
            "name": resource_name,
            "path": resource_name,
            "type": "Image",
            "digest": digest,
        }
    return resource_name


def emit_visual(
    visual: dict[str, object],
    dashboard: str,
    page_names: dict[str, str],
    bookmark_names: dict[str, str],
    images_dir: Path,
    report_dir: Path,
    resource_items: dict[str, dict[str, str]],
    model_fields: dict[str, str],
    tab_order: int,
) -> tuple[dict[str, object], dict[str, object], bool]:
    visual_type = str(visual["type"])
    visual_id = str(visual["id"])
    folder = str(visual["folder"])
    width = _number(visual["w"], f"{visual_id} w")
    height = _number(visual["h"], f"{visual_id} h")
    position = {
        "x": visual["x"],
        "y": visual["y"],
        "z": visual["z"],
        "height": height,
        "width": width,
        "tabOrder": tab_order,
    }
    visual_objects: dict[str, object] = {}
    document_visual: dict[str, object] = {
        "visualType": visual_type,
        "visualContainerObjects": _container_objects(),
    }
    field_inventory: list[dict[str, str]] = []
    deneb_used = False

    if visual_type == "deneb":
        spec_config = visual["spec"]
        fields = visual["fields"]
        if not isinstance(spec_config, dict) or not isinstance(fields, list):
            raise ValueError(f"Internal layout error for Deneb visual {visual_id!r}")
        component = str(spec_config["component"])
        params_value = spec_config["params"]
        if not isinstance(params_value, dict):
            raise ValueError(f"Internal layout error for Deneb params {visual_id!r}")
        spec = visual_builders.build_spec(
            component,
            params_value,
            float(width),
            float(height),
        )
        if not isinstance(spec, dict):
            raise ValueError(f"Deneb builder for {component!r} must return a mapping")
        projections: list[dict[str, object]] = []
        for field in fields:
            if not isinstance(field, dict):
                raise ValueError(f"Internal layout error for Deneb field {visual_id!r}")
            kind = str(field["kind"])
            reference = str(field["reference"])
            alias = str(field["alias"])
            projections.append(_projection(kind, reference, alias))
            field_inventory.append({"field": reference, "as": alias})
        spec_text = json.dumps(spec, indent=2, ensure_ascii=False)
        document_visual["visualType"] = (
            "deneb7E15AEF80B9E4D4F8E12924291ECE89A"
        )
        document_visual["query"] = {
            "queryState": {"dataset": {"projections": projections}}
        }
        visual_objects["vega"] = [
            {
                "properties": {
                    "provider": _pbi_string("vega"),
                    "version": _pbi_string("6.4.3"),
                    "renderMode": _pbi_string("svg"),
                    "jsonSpec": _pbi_string(spec_text),
                    "jsonConfig": _pbi_string("{}"),
                    "enableSelection": _literal("true"),
                    "selectionMode": _pbi_string("simple"),
                    "enableTooltips": _literal(
                        "true" if visual["tooltips"] else "false"
                    ),
                    "enableHighlight": _literal("false"),
                    "enableContextMenu": _literal("true"),
                }
            }
        ]
        visual_objects["stateManagement"] = [
            {
                "properties": {
                    "denebMetaVersion": _pbi_string("2"),
                    "viewportWidth": _pbi_number(width),
                    "viewportHeight": _pbi_number(height),
                }
            }
        ]
        document_visual["drillFilterOtherVisuals"] = bool(visual["cross_filter"])
        deneb_used = True
    elif visual_type == "native":
        roles = visual["roles"]
        if not isinstance(roles, dict):
            raise ValueError(f"Internal layout error for native roles {visual_id!r}")
        query_state: dict[str, object] = {}
        for role, raw_fields in roles.items():
            if not isinstance(raw_fields, list):
                raise ValueError(f"Internal layout error for role {role!r}")
            projections: list[dict[str, object]] = []
            for field in raw_fields:
                if not isinstance(field, dict):
                    raise ValueError(
                        f"Internal layout error for native field {visual_id!r}"
                    )
                kind = str(field["kind"])
                reference = str(field["reference"])
                display_name = str(field["display_name"])
                projections.append(
                    _projection(kind, reference, reference, active=True)
                    | {"displayName": display_name}
                )
                field_inventory.append({"role": role, "field": reference})
            query_state[str(role)] = {"projections": projections}
        document_visual["visualType"] = str(visual["visual_type"])
        document_visual["query"] = {"queryState": query_state}
        title = visual.get("title")
        if isinstance(title, str):
            container_objects = document_visual["visualContainerObjects"]
            if isinstance(container_objects, dict):
                container_objects["title"] = [
                    {
                        "properties": {
                            "show": _literal("true"),
                            "text": _pbi_string(title),
                        }
                    }
                ]
        style = visual.get("style")
        if isinstance(style, dict):
            visual_objects.update(
                _native_style_objects(style, str(visual["visual_type"]))
            )
    elif visual_type == "slicer":
        reference = str(visual["field"])
        field_inventory.append({"field": reference})
        column = reference.rpartition(".")[2]
        projection = _projection("column", reference, column, active=True)
        document_visual["query"] = {
            "queryState": {"Values": {"projections": [projection]}}
        }
        visual_objects = _slicer_objects(visual)
        if "sync_group" in visual:
            document_visual["syncGroup"] = {
                "groupName": str(visual["sync_group"]),
                "fieldChanges": True,
                "filterChanges": True,
            }
        if "default" in visual:
            default = visual["default"]
            if not isinstance(default, list):
                raise ValueError(f"Internal layout error for slicer {visual_id!r}")
            _merge_slicer_selection(
                visual_objects,
                _filter_config(
                    reference,
                    default,
                    model_fields.get(reference, "string"),
                ),
            )
    elif visual_type == "image":
        file_name = str(visual["file"])
        resource_name = _resolve_registered_image(
            file_name, images_dir, report_dir, resource_items
        )
        visual_objects["general"] = [
            {
                "properties": {
                    "imageUrl": {
                        "expr": {
                            "ResourcePackageItem": {
                                "PackageName": "RegisteredResources",
                                "PackageType": 1,
                                "ItemName": resource_name,
                            }
                        }
                    },
                    "scaling": _pbi_string(
                        "Fit" if visual["scaling"] == "fit" else "Fill"
                    ),
                }
            }
        ]
        action = visual.get("action")
        if isinstance(action, dict):
            action_type = str(action["type"])
            target = str(action["target"])
            link_properties: dict[str, object] = {
                "show": _literal("true"),
                "type": _pbi_string(
                    "PageNavigation" if action_type == "page" else "Bookmark"
                ),
            }
            if action_type == "page":
                link_properties["navigationSection"] = _pbi_string(
                    page_names[target]
                )
            else:
                link_properties["bookmark"] = _pbi_string(bookmark_names[target])
            container = document_visual["visualContainerObjects"]
            if isinstance(container, dict):
                container["visualLink"] = [{"properties": link_properties}]
    elif visual_type == "shape":
        visual_objects = {
            "shape": [
                {"properties": {"tileShape": _pbi_string("rectangle")}}
            ],
            "fill": [
                {
                    "properties": {
                        "show": _literal("true"),
                        "fillColor": _color(str(visual["fill"])),
                        "transparency": _pbi_number(
                            _number(visual["transparency"], "transparency")
                        ),
                    },
                    "selector": {"id": "default"},
                }
            ],
            "outline": [
                {"properties": {"show": _literal("false")}}
            ],
        }
    elif visual_type == "textbox":
        visual_objects = {
            "general": [
                {"properties": {"paragraphs": _textbox_paragraphs(visual)}}
            ]
        }

    document_visual["objects"] = visual_objects
    document_visual["drillFilterOtherVisuals"] = document_visual.get(
        "drillFilterOtherVisuals", True
    )
    document: dict[str, object] = {
        "$schema": (
            "https://developer.microsoft.com/json-schemas/fabric/item/report/"
            "definition/visualContainer/2.1.0/schema.json"
        ),
        "name": folder,
        "position": position,
        "visual": document_visual,
    }
    if visual["hidden"]:
        document["isHidden"] = True
    inventory: dict[str, object] = {
        "page": dashboard,
        "id": visual_id,
        "type": visual_type,
        "position": {
            "x": visual["x"],
            "y": visual["y"],
            "w": width,
            "h": height,
            "z": visual["z"],
        },
        "fields": field_inventory,
    }
    return document, inventory, deneb_used
