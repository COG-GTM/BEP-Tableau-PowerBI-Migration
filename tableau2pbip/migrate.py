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
from tableau2pbip.overrides import ModelOverrides, load_model_overrides
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
        "fact_table": workbook.fact_table,
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


def _fact_table(workbook: Workbook) -> str:
    return workbook.fact_table or (
        workbook.tables[0].caption if workbook.tables else ""
    )


def _model_field_types(
    workbook: Workbook,
    translations: dict[str, CalcTranslation],
    auto_measures: list[AutoMeasure],
    date_columns: list[AutoMeasure],
    measure_overrides: dict[str, tuple[str, str]],
    model_overrides: ModelOverrides,
    column_types: dict[str, dict[str, str]],
) -> dict[str, str]:
    fact_table = _fact_table(workbook)
    hyper_types = {
        "BIG_INT": "int64",
        "DOUBLE": "double",
        "DATE": "dateTime",
        "TEXT": "string",
        "BOOL": "boolean",
    }
    fields: dict[str, str] = {}
    for table in workbook.tables:
        for column in table.columns:
            hyper_type = column_types.get(table.caption, {}).get(column.name, "")
            fields[f"{table.caption}.{column.name}"] = hyper_types.get(
                hyper_type, column.datatype
            )
    for parameter in workbook.parameters:
        parameter_type = {
            "integer": "int64",
            "real": "double",
            "date": "dateTime",
            "string": "string",
            "boolean": "boolean",
        }.get(parameter.datatype.casefold(), parameter.datatype)
        fields[f"{parameter.caption}.{parameter.caption}"] = parameter_type
    calculations = {calc.internal_name: calc for calc in workbook.calcs}
    for internal_name, translation in translations.items():
        calc = calculations.get(internal_name)
        if (
            calc is not None
            and translation.status == "supported"
            and translation.dax is not None
        ):
            fields[f"{fact_table}.{calc.caption}"] = calc.datatype
    for measure in auto_measures:
        fields.setdefault(f"{fact_table}.{measure.name}", "double")
    for column in date_columns:
        fields.setdefault(f"{fact_table}.{column.name}", "int64")
    for caption in measure_overrides:
        fields.setdefault(f"{fact_table}.{caption}", "double")
    for column in model_overrides.calculated_columns:
        fields[f"{column.table}.{column.name}"] = column.data_type
    for table in model_overrides.calculated_tables:
        for column in table.columns:
            fields[f"{table.name}.{column.name}"] = column.data_type
    return fields


def _resolve_overrides_path(
    overrides_dir: Path | None, out_dir: Path
) -> Path | None:
    if overrides_dir is not None:
        return overrides_dir
    default_overrides = out_dir.parent / "overrides"
    return default_overrides if default_overrides.is_dir() else None


def _resolve_layout_path(
    layout_path: Path | None,
    overrides_dir: Path | None,
    out_dir: Path,
) -> Path | None:
    if layout_path is not None:
        return layout_path
    resolved_overrides = _resolve_overrides_path(overrides_dir, out_dir)
    layout_dir = resolved_overrides.parent if resolved_overrides else out_dir.parent
    default_layout = layout_dir / "layout.yml"
    return default_layout if default_layout.is_file() else None


def _report_markdown(
    name: str,
    workbook: Workbook,
    extraction: ExtractResult,
    translations: list[dict[str, object]],
    auto_measures: list[AutoMeasure],
    measure_overrides: dict[str, tuple[str, str]],
    model_overrides: ModelOverrides,
    visuals: list[dict[str, object]],
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
    lines.extend(["", "## Lead overrides", ""])
    if not (
        measure_overrides
        or model_overrides.calculated_columns
        or model_overrides.calculated_tables
        or model_overrides.relationships
    ):
        lines.append("- None.")
    for caption, (dax, format_string) in measure_overrides.items():
        lines.append(
            f"- Measure **{caption}**: `{dax}`"
            + (f" (format `{format_string}`)" if format_string else "")
        )
    for column in model_overrides.calculated_columns:
        lines.append(
            f"- Calculated column **{column.table}.{column.name}**: `{column.dax}` "
            f"({column.data_type})"
        )
    for table in model_overrides.calculated_tables:
        columns = ", ".join(
            f"{column.name} ({column.data_type})" for column in table.columns
        )
        lines.append(
            f"- Calculated table **{table.name}**: columns {columns}; DAX `{table.dax}`"
        )
    for relationship in model_overrides.relationships:
        lines.append(
            f"- Relationship `{relationship.from_table}.{relationship.from_column}` → "
            f"`{relationship.to_table}.{relationship.to_column}` "
            f"({relationship.cross_filtering_behavior})"
        )
    lines.extend(
        [
            "",
            "## Visuals",
            "",
            "| Dashboard | ID | Type | Position | Fields |",
            "|---|---|---|---|---|",
        ]
    )
    if visuals:
        for visual in visuals:
            position = json.dumps(visual.get("position", {}), separators=(",", ":"))
            fields = json.dumps(visual.get("fields", []), ensure_ascii=False)
            lines.append(
                f"| {visual.get('page', '')} | `{visual.get('id', '')}` | "
                f"{visual.get('type', '')} | `{position}` | `{fields}` |"
            )
    else:
        lines.append("| - | - | - | - | - |")
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
    layout_path: Path | None = None,
) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    overrides_dir = _resolve_overrides_path(overrides_dir, out_dir)
    working = Path(tempfile.mkdtemp(prefix="tableau2pbip-convert-"))
    unpacked = unpack(twbx, working)
    workbook = parse_workbook(unpacked.twb_path)
    compiler = CalculationCompiler(workbook)
    translations = compiler.compile_all()
    overrides = _load_overrides(overrides_dir)
    model_overrides = load_model_overrides(overrides_dir)
    auto_measures, measures_map, date_columns = generate_auto_measures(
        workbook, translations, model_overrides, overrides
    )
    extraction = extract_tables(unpacked, workbook, out_dir / "data")
    layout_path = _resolve_layout_path(layout_path, overrides_dir, out_dir)
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
        extraction.column_types,
        model_overrides,
    )
    model_fields = _model_field_types(
        workbook,
        translations,
        auto_measures,
        date_columns,
        overrides,
        model_overrides,
        extraction.column_types,
    )
    pbip_path, report_dir, visual_inventory = generate_pbir(
        name,
        workbook.dashboards,
        out_dir,
        layout_path,
        model_fields,
    )
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
        "visuals": visual_inventory,
        "measures_map": measures_map,
        "lead_overrides": {
            "measures": [
                {"name": caption, "dax": dax, "formatString": format_string}
                for caption, (dax, format_string) in overrides.items()
            ],
            "calculated_columns": [
                {
                    "table": column.table,
                    "name": column.name,
                    "dax": column.dax,
                    "dataType": column.data_type,
                    "formatString": column.format_string,
                }
                for column in model_overrides.calculated_columns
            ],
            "calculated_tables": [
                {
                    "name": table.name,
                    "dax": table.dax,
                    "columns": [
                        {
                            "name": column.name,
                            "dataType": column.data_type,
                            "formatString": column.format_string,
                        }
                        for column in table.columns
                    ],
                }
                for table in model_overrides.calculated_tables
            ],
            "relationships": [
                {
                    "from": f"{relationship.from_table}.{relationship.from_column}",
                    "to": f"{relationship.to_table}.{relationship.to_column}",
                    "crossFilteringBehavior": relationship.cross_filtering_behavior,
                }
                for relationship in model_overrides.relationships
            ],
        },
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
        _report_markdown(
            name,
            workbook,
            extraction,
            translation_records,
            auto_measures,
            overrides,
            model_overrides,
            visual_inventory,
        ),
        encoding="utf-8",
    )
    return result
