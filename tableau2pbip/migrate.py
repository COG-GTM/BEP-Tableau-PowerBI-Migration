from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

import yaml

from tableau2pbip.calc.dax import (
    AutoMeasure,
    CalcTranslation,
    CalculationCompiler,
    generate_auto_measures,
)
from tableau2pbip.extract import ExtractResult, extract_tables
from tableau2pbip.ir import Workbook
from tableau2pbip.parse import parse_workbook
from tableau2pbip.pbir import generate_pbir
from tableau2pbip.tmdl import generate_tmdl
from tableau2pbip.unpack import unpack


def _project_name(workbook: Workbook) -> str:
    name = re.sub(r"\s+\(Dynamic\)$", "", workbook.name, flags=re.IGNORECASE)
    return name or "Tableau Migration"


def _inspection(workbook: Workbook) -> dict[str, object]:
    return {
        "name": workbook.name,
        "tables": [
            {
                "caption": table.caption,
                "hyper_table": table.hyper_table,
                "columns": [
                    {"name": column.name, "datatype": column.datatype}
                    for column in table.columns
                ],
            }
            for table in workbook.tables
        ],
        "relationships": [
            {
                "from_table": relation.from_table,
                "from_col": relation.from_col,
                "to_table": relation.to_table,
                "to_col": relation.to_col,
            }
            for relation in workbook.relationships
        ],
        "calculations": [
            {
                "internal_name": calc.internal_name,
                "caption": calc.caption,
                "formula_raw": calc.formula_raw,
                "formula_resolved": calc.formula_resolved,
                "datatype": calc.datatype,
                "role": calc.role,
                "type": calc.type,
            }
            for calc in workbook.calcs
        ],
        "parameters": [
            {
                "internal_name": parameter.internal_name,
                "caption": parameter.caption,
                "datatype": parameter.datatype,
                "members": parameter.members,
                "default": parameter.default,
                "format": parameter.format,
            }
            for parameter in workbook.parameters
        ],
        "worksheets": [worksheet.name for worksheet in workbook.worksheets],
        "dashboards": [
            {
                "name": dashboard.name,
                "width": dashboard.width,
                "height": dashboard.height,
            }
            for dashboard in workbook.dashboards
        ],
        "actions": [
            {
                "name": action.name,
                "source_dashboard": action.source_dashboard,
                "source_worksheet": action.source_worksheet,
                "command": action.command,
                "target": action.target,
            }
            for action in workbook.actions
        ],
    }


def inspect_workbook(twbx: Path) -> dict[str, object]:
    working = Path(tempfile.mkdtemp(prefix="tableau2pbip-inspect-"))
    unpacked = unpack(twbx, working)
    return _inspection(parse_workbook(unpacked.twb_path))


def _load_overrides(overrides_dir: Path | None) -> dict[str, tuple[str, str]]:
    if overrides_dir is None:
        return {}
    path = overrides_dir / "measures.yml"
    if not path.exists():
        return {}
    loaded: object = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    raw_measures: object = loaded.get("measures", loaded)
    if not isinstance(raw_measures, dict):
        raise ValueError(f"{path} measures entry must be a mapping")
    overrides: dict[str, tuple[str, str]] = {}
    for caption, definition in raw_measures.items():
        if not isinstance(caption, str):
            raise ValueError(f"Measure captions in {path} must be strings")
        if isinstance(definition, str):
            overrides[caption] = (definition, "")
            continue
        if not isinstance(definition, dict):
            raise ValueError(f"Override for {caption!r} must be a mapping or string")
        dax: object = definition.get("dax", definition.get("expression"))
        format_string: object = definition.get("formatString", "")
        if not isinstance(dax, str):
            raise ValueError(f"Override for {caption!r} needs a DAX expression")
        if not isinstance(format_string, str):
            raise ValueError(f"Override formatString for {caption!r} must be a string")
        overrides[caption] = (dax, format_string)
    return overrides


def _translation_records(
    workbook: Workbook, translations: dict[str, CalcTranslation]
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for calc in workbook.calcs:
        translation = translations[calc.internal_name]
        records.append(
            {
                "internal_name": calc.internal_name,
                "caption": calc.caption,
                "formula_raw": calc.formula_raw,
                "formula_resolved": calc.formula_resolved,
                "datatype": calc.datatype,
                "role": calc.role,
                "type": calc.type,
                "classification": translation.classification,
                "status": translation.status,
                "dax": translation.dax,
                "is_calculated_column": translation.is_calculated_column,
                "reason": translation.reason,
                "semantics_approximated": translation.semantics_approximated,
            }
        )
    return records


def _report_markdown(
    name: str,
    workbook: Workbook,
    extraction: ExtractResult,
    translations: list[dict[str, object]],
    auto_measures: list[AutoMeasure],
) -> str:
    lines = [
        f"# Tableau migration report: {name}",
        "",
        "## Tables and extracted rows",
        "",
        "| Table | Hyper table | Rows | Columns |",
        "|---|---|---:|---:|",
    ]
    for table in workbook.tables:
        lines.append(
            f"| {table.caption} | `{table.hyper_table}` | "
            f"{extraction.row_counts.get(table.caption, 0)} | {len(table.columns)} |"
        )
    lines.extend(["", "## Relationships", ""])
    for relation in workbook.relationships:
        lines.append(
            f"- `{relation.from_table}.{relation.from_col}` → "
            f"`{relation.to_table}.{relation.to_col}`"
        )
    lines.extend(
        [
            "",
            "## Calculations",
            "",
            "| Caption | Class | Status | DAX / reason |",
            "|---|---|---|---|",
        ]
    )
    for record in translations:
        dax = record["dax"] or record["reason"] or ""
        escaped = str(dax).replace("|", "\\|").replace("\n", " ")
        status = str(record["status"])
        if record["semantics_approximated"]:
            status = f"{status} (semantics approximated)"
        lines.append(
            f"| {record['caption']} | {record['classification']} | "
            f"{status} | `{escaped}` |"
        )
    lines.extend(["", "## Auto measures", ""])
    for measure in auto_measures:
        lines.append(f"- **{measure.name}**: `{measure.dax}`")
    lines.extend(["", "## Duplicate-key conflicts", ""])
    if extraction.conflicts:
        for conflict in extraction.conflicts:
            column_detail = ", ".join(
                f"{column} ({count} duplicate-key groups)"
                for column, count in conflict.conflict_columns.items()
            ) or "no conflicting non-key columns"
            lines.append(
                f"- {conflict.table}.{conflict.key_column}: "
                f"{conflict.duplicate_keys} duplicate-key groups; {column_detail}."
            )
    else:
        lines.append("- None.")
    lines.append("")
    return "\n".join(lines)


def convert_workbook(
    twbx: Path,
    out_dir: Path,
    overrides_dir: Path | None = None,
) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    working = Path(tempfile.mkdtemp(prefix="tableau2pbip-convert-"))
    unpacked = unpack(twbx, working)
    workbook = parse_workbook(unpacked.twb_path)
    compiler = CalculationCompiler(workbook)
    translations = compiler.compile_all()
    auto_measures, measures_map, date_columns = generate_auto_measures(
        workbook, translations
    )
    extraction = extract_tables(unpacked, workbook, out_dir / "data")
    overrides = _load_overrides(overrides_dir)
    name = _project_name(workbook)
    model_dir = generate_tmdl(
        name,
        workbook,
        translations,
        auto_measures,
        date_columns,
        out_dir / "data",
        out_dir,
        overrides,
    )
    pbip_path, report_dir = generate_pbir(name, workbook.dashboards, out_dir)
    translation_records = _translation_records(workbook, translations)
    result: dict[str, object] = {
        "name": name,
        "pbip_path": str(pbip_path),
        "report_dir": str(report_dir),
        "semantic_model_dir": str(model_dir),
        "tables": [
            {
                "caption": table.caption,
                "hyper_table": table.hyper_table,
                "row_count": extraction.row_counts[table.caption],
                "columns": [column.name for column in table.columns],
            }
            for table in workbook.tables
        ],
        "relationships": [
            {
                "from_table": relation.from_table,
                "from_col": relation.from_col,
                "to_table": relation.to_table,
                "to_col": relation.to_col,
            }
            for relation in workbook.relationships
        ],
        "calculations": translation_records,
        "auto_measures": [
            {"name": measure.name, "dax": measure.dax, "tableau_ref": measure.tableau_ref}
            for measure in auto_measures
        ],
        "date_columns": [
            {"name": column.name, "dax": column.dax, "tableau_ref": column.tableau_ref}
            for column in date_columns
        ],
        "measures_map": measures_map,
        "conflicts": [
            {
                "table": conflict.table,
                "key_column": conflict.key_column,
                "duplicate_keys": conflict.duplicate_keys,
                "conflict_columns": conflict.conflict_columns,
            }
            for conflict in extraction.conflicts
        ],
        "overrides": sorted(overrides),
    }
    (out_dir / "measures_map.json").write_text(
        json.dumps(measures_map, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / "migration_report.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out_dir / "migration_report.md").write_text(
        _report_markdown(name, workbook, extraction, translation_records, auto_measures),
        encoding="utf-8",
    )
    return result
