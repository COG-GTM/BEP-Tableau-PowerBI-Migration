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
) -> tuple[dict[str, list[dict[str, str]]], list[str]]:
    raw_shelves = [
        item
        for shelf in ("rows", "cols")
        for item in _shelf_fields(worksheet, shelf)
    ]
    raw_encodings = [
        (encoding.field_ref, encoding.kind.casefold())
        for pane in worksheet.panes
        for encoding in pane.encodings
    ]
    resolved: dict[str, list[dict[str, str]]] = {
        "rows": [],
        "cols": [],
        "color": [],
    }
    errors: list[str] = []
    for raw, shelf in raw_shelves:
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
            errors.append(raw)
            continue
        kind, reference = mapped
        resolved[shelf].append({kind: reference})

    for raw, encoding in raw_encodings:
        if encoding != "color":
            continue
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
            errors.append(raw)
            continue
        kind, reference = mapped
        resolved["color"].append({kind: reference})
    return resolved, errors


def _roles_for_worksheet(
    worksheet: Worksheet,
    workbook: Workbook,
    model_fields: dict[str, str],
    translations: dict[str, CalcTranslation],
    measures_map: dict[str, str],
    auto_measure_names: set[str],
    date_column_names: set[str],
    caption_map: dict[str, str],
) -> tuple[str, dict[str, list[dict[str, str]]], list[str]]:
    shelves, errors = _worksheet_fields(
        worksheet,
        workbook,
        model_fields,
        translations,
        measures_map,
        auto_measure_names,
        date_column_names,
        caption_map,
    )
    rows = shelves["rows"]
    cols = shelves["cols"]
    dimensions = [
        field for field in rows + cols if "column" in field
    ]
    measures = [field for field in rows + cols if "measure" in field]
    mark_classes = {
        pane.mark_class.casefold()
        for pane in worksheet.panes
        if pane.mark_class
    }

    if "bar" in mark_classes:
        if any("column" in field for field in rows) and any(
            "measure" in field for field in cols
        ):
            visual_type = "clusteredBarChart"
            roles = {
                "Category": [field for field in rows if "column" in field],
                "Y": [field for field in cols if "measure" in field],
            }
        elif any("column" in field for field in cols) and any(
            "measure" in field for field in rows
        ):
            visual_type = "clusteredColumnChart"
            roles = {
                "Category": [field for field in cols if "column" in field],
                "Y": [field for field in rows if "measure" in field],
            }
        else:
            return "", {}, errors + ["Bar worksheet lacks a dimension/measure shelf pairing"]
    elif "line" in mark_classes:
        visual_type = "lineChart"
        category = [
            field for field in cols + rows if "column" in field
        ]
        values = [field for field in rows + cols if "measure" in field]
        if not category or not values:
            return "", {}, errors + ["Line worksheet lacks a mapped category or measure"]
        roles = {"Category": category, "Y": values}
        if shelves["color"]:
            roles["Series"] = shelves["color"]
    elif "pie" in mark_classes:
        visual_type = "pieChart"
        category = [
            field
            for field in shelves["color"] + rows + cols
            if "column" in field
        ]
        values = [field for field in rows + cols if "measure" in field]
        if not category or not values:
            return "", {}, errors + ["Pie worksheet lacks a mapped category or measure"]
        roles = {"Category": category, "Y": values}
    elif mark_classes.intersection({"text", "square", "automatic"}):
        if dimensions:
            visual_type = "tableEx"
            roles = {"Values": rows + cols}
        elif measures:
            visual_type = "card"
            roles = {"Values": measures}
        else:
            return "", {}, errors + ["Text/table worksheet has no mapped fields"]
    else:
        mark_label = ", ".join(sorted(mark_classes)) or "unknown"
        return "", {}, errors + [f"Unsupported mark class {mark_label}"]

    if errors:
        return "", {}, errors
    if not any(roles.values()):
        return "", {}, ["Worksheet has no resolved visual fields"]
    return visual_type, roles, []


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
) -> tuple[dict[str, object] | None, str, str | None]:
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
            return (
                image_visual,
                "image",
                None,
            )
        message = f"Image file not found for zone {zone.id}: {file_name or zone.name}"
        return {**geometry, **_placeholder(message)}, "textbox", message
    if zone_kind == "text":
        paragraphs = _text_runs(zone.text_runs)
        if not any(str(run.get("text", "")) for run in paragraphs[0]):
            message = zone.friendly_name or zone.name or f"Text zone {zone.id}"
            paragraphs = _placeholder(message)["paragraphs"]
        return (
            {**geometry, "type": "textbox", "align": "left", "paragraphs": paragraphs},
            "textbox",
            None,
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
                {
                    **geometry,
                    "type": "slicer",
                    "field": {"column": mapped[1]},
                    "mode": "dropdown",
                },
                "slicer",
                None,
            )
        label = zone.name or zone.friendly_name or zone.param or f"Filter {zone.id}"
        message = f"Unmapped filter/control: {label}"
        return {**geometry, **_placeholder(message)}, "textbox", message
    if worksheet is not None:
        visual_type, roles, errors = _roles_for_worksheet(
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
                {
                    **geometry,
                    "type": "native",
                    "visual_type": visual_type,
                    "roles": roles,
                    "title": worksheet.name,
                },
                f"native:{visual_type}",
                None,
            )
        message = f"Unmapped worksheet {worksheet.name}: {'; '.join(errors)}"
        return {**geometry, **_placeholder(message)}, "textbox", message
    label = zone.name or zone.friendly_name or f"{zone_kind or 'unknown'} zone {zone.id}"
    message = f"Unmapped dashboard zone: {label}"
    return {**geometry, **_placeholder(message)}, "textbox", message


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
) -> str:
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
            f"| {record['dashboard']} | `{record['zone']}` | "
            f"{record['source']} | {record['visual_type']} |"
        )
    lines.extend(["", "## Unmapped entries", ""])
    if unmapped:
        for entry in unmapped:
            lines.append(
                f"- **{entry['dashboard']} / {entry['zone']}** "
                f"({entry['source']}): {entry['reason']}"
            )
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Calculations needing attention",
            "",
            "| Calculation | Status | Class | Source formula | Reason |",
            "|---|---|---|---|---|",
        ]
    )
    attention = [
        record
        for record in translations
        if record["status"] in {"unsupported", "needs_override"}
    ]
    for record in attention:
        lines.append(
            f"| {record['caption']} | {record['status']} | "
            f"{record['classification']} | {record.get('formula') or ''} | "
            f"{record.get('reason') or ''} |"
        )
    if not attention:
        lines.append("| - | - | - | - | - |")
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
        records: list[dict[str, str]] = []
        unmapped: list[dict[str, str]] = []
        visual_counts: dict[str, dict[str, int]] = {}

        for dashboard in workbook.dashboards:
            visuals: list[dict[str, object]] = []
            counts: Counter[str] = Counter()
            for zone_index, zone in enumerate(_leaf_zones(dashboard.zones)):
                worksheet = worksheet_by_name.get(zone.name)
                source = (
                    worksheet.name
                    if worksheet is not None
                    else zone.name or zone.friendly_name or zone.param
                )
                visual, emitted_type, reason = _zone_visual(
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
                )
                records.append(
                    {
                        "dashboard": dashboard.name,
                        "zone": zone.id,
                        "source": source or zone.type_v2 or "zone",
                        "visual_type": emitted_type,
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
                if visual is not None:
                    visuals.append(visual)
                    counts[emitted_type] += 1
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
            _report_markdown(records, unmapped, translation_records),
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
            record["status"] == "unsupported" for record in translation_records
        ),
        "needs_override_calculations": sum(
            record["status"] == "needs_override"
            for record in translation_records
        ),
        "copied_images": len(image_names),
    }
