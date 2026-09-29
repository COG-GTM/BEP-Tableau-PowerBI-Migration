from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from tableau2pbip.ir import Dashboard
from tableau2pbip.layout import emit_visual, load_layout
from tableau2pbip.schema_validation import validate_json_documents


_DENEB_ID = "deneb7E15AEF80B9E4D4F8E12924291ECE89A"


def _page_name(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "", value)
    return f"ReportSection{slug or 'Page'}"


def _stable_id(value: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"tableau2pbip:{value}"))


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _background_objects(color: str | None) -> dict[str, object]:
    if color is None:
        return {}
    properties = {
        "color": {"solid": {"color": {"expr": {"Literal": {"Value": f"'{color}'"}}}}},
        "transparency": {"expr": {"Literal": {"Value": "0D"}}},
    }
    return {
        "background": [{"properties": properties}],
        "outspace": [{"properties": properties}],
    }


def generate_pbir(
    name: str,
    dashboards: list[Dashboard],
    output_dir: Path,
    layout_path: Path | None = None,
    model_fields: dict[str, str] | None = None,
) -> tuple[Path, Path, list[dict[str, object]]]:
    model_fields = model_fields or {}
    layout = load_layout(layout_path, dashboards, model_fields)
    report_dir = output_dir / f"{name}.Report"
    definition = report_dir / "definition"
    pages_dir = definition / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    model_path = f"../{name}.SemanticModel"

    _write_json(
        report_dir / "definition.pbir",
        {
            "version": "4.0",
            "datasetReference": {"byPath": {"path": model_path}},
        },
    )
    _write_json(
        report_dir / ".platform",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {"type": "Report", "displayName": name},
            "config": {
                "version": "2.0",
                "logicalId": _stable_id(f"platform.report.{name}"),
            },
        },
    )
    _write_json(
        definition / "version.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
            "version": "2.0.0",
        },
    )

    page_names = {
        dashboard.name: _page_name(dashboard.name) for dashboard in dashboards
    }
    page_name_values = list(page_names.values())
    if len(page_name_values) != len(set(page_name_values)):
        raise ValueError("Tableau dashboard names collide after PBIR page-name generation")
    dashboard_pages = [
        (page_names[dashboard.name], dashboard) for dashboard in dashboards
    ]
    bookmark_names = {
        str(bookmark["name"]): str(bookmark["bookmark_id"])
        for bookmark in layout.bookmarks
    }
    visual_inventory: list[dict[str, object]] = []
    visual_state_info: dict[str, dict[str, tuple[str, str]]] = {}
    registered_resources: dict[str, dict[str, str]] = {}
    deneb_used = False
    for page_name, dashboard in dashboard_pages:
        page_layout = layout.pages.get(dashboard.name, [])
        page_visual_dir = pages_dir / page_name / "visuals"
        for visual_index, visual in enumerate(page_layout):
            document, inventory, uses_deneb = emit_visual(
                visual,
                dashboard.name,
                page_names,
                bookmark_names,
                layout.images_dir,
                report_dir,
                registered_resources,
                model_fields,
                visual_index,
            )
            visual_folder = str(document["name"])
            document_visual = document["visual"]
            if not isinstance(document_visual, dict):
                raise ValueError(f"Internal layout error for visual {visual_folder!r}")
            pbir_visual_type = document_visual.get("visualType")
            if not isinstance(pbir_visual_type, str):
                raise ValueError(
                    f"Internal layout error for visual type {visual_folder!r}"
                )
            visual_state_info.setdefault(dashboard.name, {})[
                str(visual["id"])
            ] = (visual_folder, pbir_visual_type)
            _write_json(
                page_visual_dir / visual_folder / "visual.json",
                document,
            )
            visual_inventory.append(inventory)
            deneb_used = deneb_used or uses_deneb
        _write_json(
            pages_dir / page_name / "page.json",
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
                "name": page_name,
                "displayName": dashboard.name,
                "displayOption": "ActualSize",
                "height": dashboard.height,
                "width": dashboard.width,
                **(
                    {"objects": _background_objects(layout.page_background)}
                    if layout.page_background is not None
                    else {}
                ),
            },
        )
    first_page = dashboard_pages[0][0] if dashboard_pages else "ReportSection"
    _write_json(
        pages_dir / "pages.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
            "pageOrder": [page_name for page_name, _ in dashboard_pages],
            "activePageName": first_page,
            "landingPageName": first_page,
        },
    )

    if layout.bookmarks:
        bookmarks_dir = definition / "bookmarks"
        bookmark_schema = (
            "https://developer.microsoft.com/json-schemas/fabric/item/report/"
            "definition/bookmark/1.0.0/schema.json"
        )
        bookmark_metadata_schema = (
            "https://developer.microsoft.com/json-schemas/fabric/item/report/"
            "definition/bookmarksMetadata/1.0.0/schema.json"
        )
        _write_json(
            bookmarks_dir / "bookmarks.json",
            {
                "$schema": bookmark_metadata_schema,
                "items": [
                    {"name": str(bookmark["bookmark_id"])}
                    for bookmark in layout.bookmarks
                ],
            },
        )
        for bookmark in layout.bookmarks:
            dashboard_name = str(bookmark["page"])
            page_name = page_names[dashboard_name]
            targets = bookmark["targets"]
            hidden = bookmark["hidden"]
            if not isinstance(targets, list) or not isinstance(hidden, list):
                raise ValueError("Internal layout error: bookmark targets are invalid")
            hidden_ids = set(hidden)
            target_visual_names: list[str] = []
            visual_states: dict[str, dict[str, object]] = {}
            for visual_id in targets:
                visual_folder, pbir_visual_type = visual_state_info[dashboard_name][
                    str(visual_id)
                ]
                target_visual_names.append(visual_folder)
                single_visual: dict[str, object] = {
                    "visualType": pbir_visual_type
                }
                if visual_id in hidden_ids:
                    single_visual["display"] = {"mode": "hidden"}
                visual_states[visual_folder] = {"singleVisual": single_visual}
            bookmark_document: dict[str, object] = {
                "$schema": bookmark_schema,
                "name": str(bookmark["bookmark_id"]),
                "options": {
                    "applyOnlyToTargetVisuals": True,
                    "targetVisualNames": target_visual_names,
                    "suppressData": True,
                    "suppressActiveSection": False,
                    "suppressDisplay": False,
                },
                "explorationState": {
                    "version": "1.0",
                    "activeSection": page_name,
                    "sections": {
                        page_name: {"visualContainers": visual_states}
                    },
                },
            }
            bookmark_document["displayName"] = str(
                bookmark.get("display_name", bookmark["name"])
            )
            _write_json(
                bookmarks_dir
                / f"{bookmark['bookmark_id']}.bookmark.json",
                bookmark_document,
            )

    report_data: dict[str, object] = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json",
        "themeCollection": {
            "baseTheme": {
                "name": "Fluent2-CY26SU08",
                "reportVersionAtImport": {
                    "visual": "2.12.0",
                    "report": "3.4.0",
                    "page": "2.3.1",
                },
                "type": "SharedResources",
            }
        },
        "objects": {
            "section": [
                {
                    "properties": {
                        "verticalAlignment": {
                            "expr": {"Literal": {"Value": "'Top'"}}
                        }
                    }
                }
            ],
            "outspacePane": [
                {
                    "properties": {
                        "expanded": {"expr": {"Literal": {"Value": "false"}}}
                    }
                }
            ],
        },
        "resourcePackages": [
            {
                "name": "SharedResources",
                "type": "SharedResources",
                "items": [
                    {
                        "name": "Fluent2-CY26SU08",
                        "path": "BaseThemes/Fluent2-CY26SU08.json",
                        "type": "BaseTheme",
                    }
                ],
            }
        ],
        "settings": {
            "useStylableVisualContainerHeader": True,
            "exportDataMode": "AllowSummarized",
            "defaultFilterActionIsDataFilter": True,
            "defaultDrillFilterOtherVisuals": True,
            "allowChangeFilterTypes": True,
            "useEnhancedTooltips": False,
            "queryLimitOption": "None",
            "customMemoryLimit": "1048576",
            "customTimeoutLimit": "225",
        },
    }
    if deneb_used:
        report_data["publicCustomVisuals"] = [_DENEB_ID]
    if registered_resources:
        items = [
            {key: value[key] for key in ("name", "path", "type")}
            for value in registered_resources.values()
        ]
        packages = report_data["resourcePackages"]
        if isinstance(packages, list):
            packages.append(
                {
                    "name": "RegisteredResources",
                    "type": "RegisteredResources",
                    "items": items,
                }
            )
    _write_json(definition / "report.json", report_data)

    pbip_path = output_dir / f"{name}.pbip"
    _write_json(
        pbip_path,
        {
            "version": "1.0",
            "artifacts": [{"report": {"path": f"{name}.Report"}}],
            "settings": {"enableAutoRecovery": True},
        },
    )
    ignore = report_dir / ".gitignore"
    ignore.write_text(".pbi/cache.abf\n.pbi/localSettings.json\n", encoding="utf-8")
    validate_json_documents(output_dir)
    return pbip_path, report_dir, visual_inventory
