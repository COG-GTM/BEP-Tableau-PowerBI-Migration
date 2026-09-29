from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from tableau2pbip.ir import Dashboard


def _page_name(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "", value)
    return f"ReportSection{slug or 'Page'}"


def _stable_id(value: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"tableau2pbip:{value}"))


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def generate_pbir(
    name: str, dashboards: list[Dashboard], output_dir: Path
) -> tuple[Path, Path]:
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
        definition / "report.json",
        {
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
        },
    )
    _write_json(
        definition / "version.json",
        {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
            "version": "2.0.0",
        },
    )

    dashboard_pages: list[tuple[str, Dashboard]] = []
    for dashboard in dashboards:
        page_name = _page_name(dashboard.name)
        dashboard_pages.append((page_name, dashboard))
        _write_json(
            pages_dir / page_name / "page.json",
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
                "name": page_name,
                "displayName": dashboard.name,
                "displayOption": "ActualSize",
                "height": dashboard.height,
                "width": dashboard.width,
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
    return pbip_path, report_dir
