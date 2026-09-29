from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from tableau2pbip.calc.dax import AutoMeasure, CalcTranslation
from tableau2pbip.ir import Parameter, Relationship, Table, Workbook


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _tag(value: str) -> str:
    escaped = value.replace("'", "''")
    return value if _IDENTIFIER.fullmatch(value) else f"'{escaped}'"


def _lineage(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"tableau2pbip:{name}"))


def _m_string(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _column_type(datatype: str) -> tuple[str, str, str]:
    normalized = datatype.casefold()
    if any(token in normalized for token in ("integer", "int64", "bigint", "long")):
        return "Int64.Type", "int64", "0"
    if any(token in normalized for token in ("real", "double", "float", "numeric", "decimal")):
        return "type number", "double", "#,##0.00"
    if "date" in normalized or "timestamp" in normalized or "time" in normalized:
        return "type date", "dateTime", "Short Date"
    if "bool" in normalized:
        return "type logical", "boolean", ""
    return "type text", "string", ""


def _format_string(format_spec: str, datatype: str, caption: str) -> str:
    value = format_spec.strip()
    if not value:
        if "%" in caption:
            return "0.0%;-0.0%;-"
        return "#,##0" if datatype.casefold() in {"integer", "int", "bigint"} else "#,##0.00"

    normalized = value
    if normalized.startswith("*"):
        normalized = normalized[1:]
    if "%" in normalized:
        return "0.0%;-0.0%;-"
    sections = normalized.split(";")
    converted: list[str] = []
    for section in sections:
        section = re.sub(r"^[nNcC]", "", section)
        section = re.sub(r"^[^0-9\"$#.,-]+", "", section)
        section = section.replace(",K", ",").replace(",k", ",")
        section = section.replace("K", "").replace("k", "")
        if section:
            converted.append(section)
    result = ";".join(converted)
    if not result:
        return "#,##0" if datatype.casefold() in {"integer", "int", "bigint"} else "#,##0.00"
    return result


def _table_m(table: Table) -> str:
    file_name = f"{table.caption}.csv"
    type_pairs = []
    for column in table.columns:
        m_type, _, _ = _column_type(column.datatype)
        type_pairs.append(
            "{" + f"{_m_string(column.name)}, {m_type}" + "}"
        )
    type_list = ", ".join(type_pairs)
    lines = [
        "let",
        "    Source = Csv.Document(File.Contents(DataFolder & "
        + _m_string(f"\\{file_name}")
        + "), [Delimiter=\",\", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),",
        "    PromoteHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),",
        f"    ChangedType = Table.TransformColumnTypes(PromoteHeaders, {{{type_list}}}, \"en-US\")",
        "in",
        "    ChangedType",
    ]
    return "\n".join(lines)


def _table_reference(table: str, column: str) -> str:
    return f"{_tag(table)}.{_tag(column)}"


def _physical_column_block(table: str, column_name: str, datatype: str) -> list[str]:
    m_type, dax_type, default_format = _column_type(datatype)
    del m_type
    lines = [
        f"\tcolumn {_tag(column_name)}",
        f"\t\tdataType: {dax_type}",
    ]
    if default_format:
        lines.append(f"\t\tformatString: {default_format}")
    lines.extend(
        [
            f"\t\tlineageTag: {_lineage(f'{table}.{column_name}')}",
            f"\t\tsummarizeBy: {'sum' if dax_type in {'int64', 'double'} else 'none'}",
            f"\t\tsourceColumn: {column_name}",
        ]
    )
    if dax_type == "dateTime":
        lines.append("\t\tannotation UnderlyingDateTimeDataType = Date")
    lines.extend(
        [
            "",
            "\t\tannotation SummarizationSetBy = Automatic",
            "",
        ]
    )
    return lines


def _calculated_column_block(
    table: str, name: str, dax: str, datatype: str, format_spec: str = ""
) -> list[str]:
    _, dax_type, default_format = _column_type(datatype)
    lines = [
        f"\tcolumn {_tag(name)} = {dax}",
        f"\t\tdataType: {dax_type}",
    ]
    output_format = _format_string(format_spec, datatype, name) if format_spec else default_format
    if output_format:
        lines.append(f"\t\tformatString: {output_format}")
    lines.extend(
        [
            f"\t\tlineageTag: {_lineage(f'{table}.{name}')}",
            f"\t\tsummarizeBy: {'sum' if dax_type in {'int64', 'double'} else 'none'}",
            "",
            "\t\tannotation SummarizationSetBy = Automatic",
            "",
        ]
    )
    return lines


def _measure_block(
    table: str,
    name: str,
    dax: str,
    format_spec: str,
    display_folder: str,
) -> list[str]:
    format_string = _format_string(format_spec, "real", name)
    return [
        f"\tmeasure {_tag(name)} = {dax}",
        f"\t\tformatString: {format_string}",
        f"\t\tdisplayFolder: {display_folder}",
        f"\t\tlineageTag: {_lineage(f'{table}.measure.{name}')}",
        "",
    ]


def _tmdl_table(table: Table) -> str:
    lines = [
        f"table {_tag(table.caption)}",
        f"\tlineageTag: {_lineage(f'table.{table.caption}')}",
        "",
    ]
    for column in table.columns:
        lines.extend(_physical_column_block(table.caption, column.name, column.datatype))
    lines.extend(
        [
            f"\tpartition {_tag(table.caption)} = m",
            "\t\tmode: import",
            "\t\tsource =",
        ]
    )
    for line in _table_m(table).splitlines():
        lines.append(f"\t\t\t\t{line}")
    return "\n".join(lines)


def _parameter_table(parameter: Parameter) -> str:
    members = parameter.members or [parameter.default]
    values = ", ".join("{" + str(member) + "}" for member in members)
    name = parameter.caption
    lines = [
        f"table {_tag(name)}",
        f"\tlineageTag: {_lineage(f'table.{name}')}",
        "\tannotation PBI_IsParameterQuery = true",
        f"\tannotation PBI_ParameterDefaultValue = {parameter.default}",
        "",
        f"\tcolumn {_tag(name)}",
        "\t\tdataType: int64",
        "\t\tformatString: 0",
        f"\t\tlineageTag: {_lineage(f'{name}.{name}')}",
        "\t\tsummarizeBy: none",
        f"\t\tsourceColumn: {name}",
        "",
        "\t\tannotation SummarizationSetBy = Automatic",
        "",
        f"\tpartition {_tag(name)} = calculated",
        "\t\tmode: import",
        "\t\tsource =",
        f"\t\t\t\tDATATABLE({_m_string(name)}, INTEGER, {{{values}}})",
        "",
        "\t\tannotation PBI_ResultType = Table",
        "",
    ]
    return "\n".join(lines)


def _relationship_tmdl(relationship: Relationship) -> str:
    relation_id = _lineage(
        f"relationship.{relationship.from_table}.{relationship.from_col}."
        f"{relationship.to_table}.{relationship.to_col}"
    )
    return "\n".join(
        [
            f"relationship {relation_id}",
            "\tfromCardinality: many",
            "\ttoCardinality: one",
            "\tcrossFilteringBehavior: oneDirection",
            f"\tfromColumn: {_table_reference(relationship.from_table, relationship.from_col)}",
            f"\ttoColumn: {_table_reference(relationship.to_table, relationship.to_col)}",
            "",
        ]
    )


def generate_tmdl(
    name: str,
    workbook: Workbook,
    calculations: dict[str, CalcTranslation],
    auto_measures: list[AutoMeasure],
    date_columns: list[AutoMeasure],
    data_folder: Path,
    output_dir: Path,
    overrides: dict[str, tuple[str, str]] | None = None,
) -> Path:
    model_dir = output_dir / f"{name}.SemanticModel"
    definition = model_dir / "definition"
    tables_dir = definition / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    (model_dir / "definition.pbism").write_text(
        json.dumps({"version": "4.2", "settings": {}}, indent=2) + "\n",
        encoding="utf-8",
    )
    (model_dir / ".platform").write_text(
        json.dumps(
            {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
                "metadata": {"type": "SemanticModel", "displayName": name},
                "config": {
                    "version": "2.0",
                    "logicalId": _lineage(f"platform.semantic-model.{name}"),
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (model_dir / ".gitignore").write_text(
        ".pbi/cache.abf\n.pbi/localSettings.json\n",
        encoding="utf-8",
    )
    (definition / "database.tmdl").write_text(
        "database\n\tcompatibilityLevel: 1606\n",
        encoding="utf-8",
    )
    referenced_tables = [table.caption for table in workbook.tables]
    referenced_tables.extend(parameter.caption for parameter in workbook.parameters)
    model_lines = [
        "model Model",
        "\tculture: en-US",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tdiscourageImplicitMeasures",
        "\tsourceQueryCulture: en-US",
        "\tdataAccessOptions",
        "\t\tlegacyRedirects",
        "\t\treturnErrorValuesAsNull",
        "",
    ]
    for table_name in referenced_tables:
        model_lines.append(f"ref table {_tag(table_name)}")
    (definition / "model.tmdl").write_text(
        "\n".join(model_lines) + "\n",
        encoding="utf-8",
    )

    expressions = (
        "expression DataFolder =\n"
        f"\t{_m_string(str(data_folder.resolve()))}\n"
        "\tmeta [IsParameterQuery=true, Type=\"Text\", IsParameterQueryRequired=true]\n"
    )
    (definition / "expressions.tmdl").write_text(expressions, encoding="utf-8")

    for table in workbook.tables:
        text = _tmdl_table(table)
        (tables_dir / f"{table.caption}.tmdl").write_text(text + "\n", encoding="utf-8")
    for parameter in workbook.parameters:
        (tables_dir / f"{parameter.caption}.tmdl").write_text(
            _parameter_table(parameter), encoding="utf-8"
        )

    fact_table = next(
        (table.caption for table in workbook.tables if table.caption.casefold() == "orders"),
        workbook.tables[0].caption if workbook.tables else "Orders",
    )
    fact_file = tables_dir / f"{fact_table}.tmdl"
    fact_text = fact_file.read_text(encoding="utf-8")
    columns_text: list[str] = []
    parameter_internal_names = {
        parameter.internal_name for parameter in workbook.parameters
    }
    for calc in workbook.calcs:
        translation = calculations.get(calc.internal_name)
        if (
            translation is not None
            and translation.status == "supported"
            and translation.is_calculated_column
            and translation.dax is not None
            and calc.internal_name not in parameter_internal_names
        ):
            columns_text.extend(
                _calculated_column_block(
                    fact_table,
                    calc.caption,
                    translation.dax,
                    calc.datatype,
                    calc.format,
                )
            )
    existing_columns = {
        calc.caption for calc in workbook.calcs
    }
    for date_column in date_columns:
        if date_column.name not in existing_columns:
            columns_text.extend(
                _calculated_column_block(
                    fact_table,
                    date_column.name,
                    date_column.dax,
                    "integer",
                )
            )

    measure_specs: dict[str, tuple[str, str, str]] = {}
    for calc in workbook.calcs:
        translation = calculations.get(calc.internal_name)
        if (
            translation is not None
            and translation.status == "supported"
            and translation.dax is not None
            and translation.classification in {"aggregate", "lod"}
        ):
            measure_specs[calc.caption] = (
                translation.dax,
                calc.format,
                "Tableau calcs",
            )
    for measure in auto_measures:
        measure_specs.setdefault(
            measure.name,
            (measure.dax, "", measure.display_folder),
        )
    if overrides:
        for caption, (dax, format_string) in overrides.items():
            measure_specs[caption] = (dax, format_string, "Tableau calcs")

    measure_text: list[str] = []
    for measure_name, (dax, format_string, display_folder) in measure_specs.items():
        measure_text.extend(
            _measure_block(fact_table, measure_name, dax, format_string, display_folder)
        )
    insertion = fact_text.find("\tpartition ")
    if insertion < 0:
        fact_text = fact_text.rstrip() + "\n\n" + "".join(columns_text + measure_text)
    else:
        fact_text = (
            fact_text[:insertion]
            + "".join(columns_text + measure_text)
            + fact_text[insertion:]
        )
    fact_file.write_text(fact_text, encoding="utf-8")

    relationships_path = definition / "relationships.tmdl"
    relationships_path.write_text(
        "".join(_relationship_tmdl(item) for item in workbook.relationships),
        encoding="utf-8",
    )
    return model_dir
