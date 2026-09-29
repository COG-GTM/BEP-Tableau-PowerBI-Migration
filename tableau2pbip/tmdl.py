from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from tableau2pbip.calc.dax import AutoMeasure, CalcTranslation
from tableau2pbip.ir import Parameter, Table, Workbook
from tableau2pbip.overrides import CalculatedTableOverride, ModelOverrides


_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _tag(value: str) -> str:
    escaped = value.replace("'", "''")
    return value if _IDENTIFIER.fullmatch(value) else f"'{escaped}'"


def _lineage(name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"tableau2pbip:{name}"))


def _m_string(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _column_type(datatype: str) -> tuple[str, str, str]:
    normalized = datatype.strip().casefold().replace(" ", "_")
    if normalized in {"big_int", "bigint", "int64"} or any(
        token in normalized for token in ("integer", "long")
    ):
        return "Int64.Type", "int64", "0"
    if normalized in {"double", "real", "float"} or any(
        token in normalized for token in ("numeric", "decimal")
    ):
        return "type number", "double", "#,##0.00"
    if normalized in {"date", "timestamp", "datetime"} or any(
        token in normalized for token in ("date", "time")
    ):
        return "type date", "dateTime", "M/d/yyyy"
    if normalized in {"bool", "boolean"} or "bool" in normalized:
        return "type logical", "boolean", ""
    return "type text", "string", ""


def _format_string(format_spec: str, datatype: str, caption: str) -> str:
    _, dax_type, _ = _column_type(datatype)
    if dax_type in {"string", "boolean"}:
        return ""
    value = format_spec.strip()
    if dax_type == "dateTime":
        return value or "M/d/yyyy"
    if not value:
        if "%" in caption:
            return "0.0%;-0.0%;-"
        return "#,##0" if dax_type == "int64" else "#,##0.00"

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
        return "#,##0" if dax_type == "int64" else "#,##0.00"
    return result


def _table_m(table: Table, hyper_types: dict[str, str]) -> str:
    file_name = f"{table.caption}.csv"
    type_pairs = []
    for column in table.columns:
        m_type, _, _ = _column_type(hyper_types.get(column.name, column.datatype))
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
            "\t\tsummarizeBy: none",
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
            "\t\tsummarizeBy: none",
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
    datatype: str,
) -> list[str]:
    format_string = _format_string(format_spec, datatype, name)
    lines = [
        f"\tmeasure {_tag(name)} = {dax}",
    ]
    if format_string:
        lines.append(f"\t\tformatString: {format_string}")
    lines.extend(
        [
            f"\t\tdisplayFolder: {display_folder}",
            f"\t\tlineageTag: {_lineage(f'{table}.measure.{name}')}",
            "",
        ]
    )
    return lines


def _column_datatype(
    table: Table, column_name: str, hyper_types: dict[str, dict[str, str]]
) -> str:
    table_types = hyper_types.get(table.caption, {})
    if column_name in table_types:
        return table_types[column_name]
    return next(
        (
            datatype
            for name, datatype in table_types.items()
            if name.casefold() == column_name.casefold()
        ),
        next(
            (
                column.datatype
                for column in table.columns
                if column.name.casefold() == column_name.casefold()
            ),
            "string",
        ),
    )


def _auto_measure_datatype(
    measure: AutoMeasure,
    workbook: Workbook,
    hyper_types: dict[str, dict[str, str]],
) -> str:
    prefix, separator, column_name = measure.name.partition(" ")
    if separator and prefix.upper() in {"MIN", "MAX"}:
        for table in workbook.tables:
            if any(
                column.name.casefold() == column_name.casefold()
                for column in table.columns
            ):
                return _column_datatype(table, column_name, hyper_types)
    return "real"


def _tmdl_table(table: Table, hyper_types: dict[str, str]) -> str:
    lines = [
        f"table {_tag(table.caption)}",
        f"\tlineageTag: {_lineage(f'table.{table.caption}')}",
        "",
    ]
    for column in table.columns:
        datatype = hyper_types.get(column.name, column.datatype)
        lines.extend(_physical_column_block(table.caption, column.name, datatype))
    lines.extend(
        [
            f"\tpartition {_tag(table.caption)} = m",
            "\t\tmode: import",
            "\t\tsource =",
        ]
    )
    for line in _table_m(table, hyper_types).splitlines():
        lines.append(f"\t\t\t\t{line}")
    return "\n".join(lines)


def _parameter_table(parameter: Parameter) -> str:
    members = parameter.members or [parameter.default]
    values = ", ".join("{" + str(member) + "}" for member in members)
    name = parameter.caption
    lines = [
        f"table {_tag(name)}",
        f"\tlineageTag: {_lineage(f'table.{name}')}",
        "",
        f"\tcolumn {_tag(name)}",
        "\t\tdataType: int64",
        "\t\tformatString: 0",
        f"\t\tlineageTag: {_lineage(f'{name}.{name}')}",
        "\t\tsummarizeBy: none",
        "\t\tisNameInferred",
        f"\t\tsourceColumn: [{name}]",
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


def _calculated_table_column_block(
    table: str, column_name: str, datatype: str, format_spec: str
) -> list[str]:
    _, dax_type, default_format = _column_type(datatype)
    format_string = (
        _format_string(format_spec, datatype, column_name) if format_spec else default_format
    )
    lines = [
        f"\tcolumn {_tag(column_name)}",
        f"\t\tdataType: {dax_type}",
    ]
    if format_string:
        lines.append(f"\t\tformatString: {format_string}")
    lines.extend(
        [
            f"\t\tlineageTag: {_lineage(f'{table}.{column_name}')}",
            "\t\tsummarizeBy: none",
            "\t\tisNameInferred",
            f"\t\tsourceColumn: [{column_name}]",
            "",
            "\t\tannotation SummarizationSetBy = Automatic",
            "",
        ]
    )
    return lines


def _format_dax_expression(expression: str) -> list[str]:
    text = expression.strip()
    lines: list[str] = []
    depth = 0
    current = "\t\t\t"
    quote: str | None = None

    def flush() -> None:
        nonlocal current
        if current.strip():
            lines.append(current.rstrip())
        current = "\t" * (3 + depth)

    index = 0
    while index < len(text):
        character = text[index]
        if quote is not None:
            current += character
            if character == quote:
                if index + 1 < len(text) and text[index + 1] == quote:
                    current += text[index + 1]
                    index += 2
                    continue
                quote = None
            index += 1
            continue
        if character in {"'", '"'}:
            quote = character
            current += character
        elif character == "(":
            current += character
            depth += 1
            flush()
        elif character == ",":
            current += character
            flush()
        elif character == ")":
            if current.strip():
                flush()
            depth = max(0, depth - 1)
            current = "\t" * (3 + depth) + ")"
        elif character.isspace():
            if current.strip():
                next_index = index
                while next_index < len(text) and text[next_index].isspace():
                    next_index += 1
                keyword = next(
                    (
                        value
                        for value in ("VAR", "RETURN")
                        if text.startswith(value + " ", next_index)
                    ),
                    None,
                )
                if keyword is not None:
                    flush()
                    current = "\t" * (3 + depth) + keyword
                    index = next_index + len(keyword)
                    continue
                current += character
        else:
            current += character
        index += 1
    if current.strip():
        lines.append(current.rstrip())
    return lines


def _calculated_table_tmdl(table: CalculatedTableOverride) -> str:
    lines = [
        f"table {_tag(table.name)}",
        f"\tlineageTag: {_lineage(f'table.{table.name}')}",
        "",
    ]
    for column in table.columns:
        lines.extend(
            _calculated_table_column_block(
                table.name, column.name, column.data_type, column.format_string
            )
        )
    lines.extend(
        [
            f"\tpartition {_tag(table.name)} = calculated",
            "\t\tmode: import",
            "\t\tsource =",
        ]
    )
    lines.extend(_format_dax_expression(table.dax))
    lines.extend(["", "\t\tannotation PBI_ResultType = Table", ""])
    return "\n".join(lines)


def _relationship_tmdl(
    from_table: str,
    from_column: str,
    to_table: str,
    to_column: str,
    cross_filtering_behavior: str = "oneDirection",
) -> str:
    relation_id = _lineage(
        f"relationship.{from_table}.{from_column}.{to_table}.{to_column}"
    )
    return "\n".join(
        [
            f"relationship {relation_id}",
            "\tfromCardinality: many",
            "\ttoCardinality: one",
            f"\tcrossFilteringBehavior: {cross_filtering_behavior}",
            f"\tfromColumn: {_table_reference(from_table, from_column)}",
            f"\ttoColumn: {_table_reference(to_table, to_column)}",
            "",
        ]
    )


def _validate_data_type(data_type: str, context: str) -> None:
    normalized = data_type.strip().casefold().replace(" ", "_")
    supported = {
        "int64",
        "integer",
        "int",
        "big_int",
        "bigint",
        "long",
        "double",
        "real",
        "float",
        "date",
        "datetime",
        "timestamp",
        "string",
        "text",
        "bool",
        "boolean",
    }
    if normalized not in supported:
        raise ValueError(f"{context} has unsupported dataType {data_type!r}")


def _validate_model_overrides(workbook: Workbook, overrides: ModelOverrides) -> None:
    physical_tables = {table.caption.casefold(): table.caption for table in workbook.tables}
    fields = {
        (table.caption.casefold(), column.name.casefold())
        for table in workbook.tables
        for column in table.columns
    }
    for parameter in workbook.parameters:
        fields.add((parameter.caption.casefold(), parameter.caption.casefold()))
    for column in overrides.calculated_columns:
        table = physical_tables.get(column.table.casefold())
        if table is None:
            raise ValueError(
                f"Calculated column {column.table}.{column.name} references an unknown table"
            )
        key = (table.casefold(), column.name.casefold())
        if key in fields:
            raise ValueError(
                f"Calculated column override {column.table}.{column.name} duplicates a model field"
            )
        _validate_data_type(column.data_type, f"Calculated column {column.table}.{column.name}")
        fields.add(key)

    table_names = set(physical_tables)
    table_names.update(parameter.caption.casefold() for parameter in workbook.parameters)
    for table in overrides.calculated_tables:
        if table.name.casefold() in table_names:
            raise ValueError(f"Calculated table {table.name!r} duplicates a model table")
        table_names.add(table.name.casefold())
        for column in table.columns:
            key = (table.name.casefold(), column.name.casefold())
            if key in fields:
                raise ValueError(
                    f"Calculated table {table.name!r} has duplicate column {column.name!r}"
                )
            _validate_data_type(
                column.data_type, f"Calculated table {table.name}.{column.name}"
            )
            fields.add(key)

    for relationship in overrides.relationships:
        for side, table, column in (
            ("from", relationship.from_table, relationship.from_column),
            ("to", relationship.to_table, relationship.to_column),
        ):
            if (table.casefold(), column.casefold()) not in fields:
                raise ValueError(
                    f"Override relationship {side} field {table}.{column} is not in the model"
                )


def _insert_table_additions(text: str, additions: list[str]) -> str:
    if not additions:
        return text
    insertion = text.find("\tpartition ")
    if insertion < 0:
        raise ValueError("Cannot add calculated fields to a table without a partition")
    return (
        text[:insertion]
        + "\n".join(additions)
        + "\n"
        + text[insertion:]
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
    column_types: dict[str, dict[str, str]] | None = None,
    model_overrides: ModelOverrides | None = None,
) -> Path:
    hyper_types = column_types or {}
    model_overrides = model_overrides or ModelOverrides([], [], [])
    _validate_model_overrides(workbook, model_overrides)
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
    referenced_tables.extend(table.name for table in model_overrides.calculated_tables)
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
        text = _tmdl_table(table, hyper_types.get(table.caption, {}))
        (tables_dir / f"{table.caption}.tmdl").write_text(text + "\n", encoding="utf-8")
    for parameter in workbook.parameters:
        (tables_dir / f"{parameter.caption}.tmdl").write_text(
            _parameter_table(parameter), encoding="utf-8"
        )
    for table in model_overrides.calculated_tables:
        (tables_dir / f"{table.name}.tmdl").write_text(
            _calculated_table_tmdl(table), encoding="utf-8"
        )

    fact_table = workbook.fact_table or (
        workbook.tables[0].caption if workbook.tables else ""
    )
    columns_by_table: dict[str, list[str]] = {
        table.caption: [] for table in workbook.tables
    }
    override_column_keys = {
        (column.table.casefold(), column.name.casefold())
        for column in model_overrides.calculated_columns
    }
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
            and (fact_table.casefold(), calc.caption.casefold())
            not in override_column_keys
        ):
            columns_by_table[fact_table].extend(
                _calculated_column_block(
                    fact_table,
                    calc.caption,
                    translation.dax,
                    calc.datatype,
                    calc.format,
                )
            )
    existing_columns = {calc.caption.casefold() for calc in workbook.calcs}
    for date_column in date_columns:
        if (
            date_column.name.casefold() not in existing_columns
            and (fact_table.casefold(), date_column.name.casefold())
            not in override_column_keys
        ):
            columns_by_table[fact_table].extend(
                _calculated_column_block(
                    fact_table,
                    date_column.name,
                    date_column.dax,
                    "integer",
                )
            )
    table_names = {table.caption.casefold(): table.caption for table in workbook.tables}
    for column in model_overrides.calculated_columns:
        table_name = table_names[column.table.casefold()]
        columns_by_table[table_name].extend(
            _calculated_column_block(
                table_name,
                column.name,
                column.dax,
                column.data_type,
                column.format_string,
            )
        )

    measure_specs: dict[str, tuple[str, str, str, str]] = {}
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
                calc.datatype,
            )
    for measure in auto_measures:
        datatype = _auto_measure_datatype(measure, workbook, hyper_types)
        format_spec = "M/d/yyyy" if _column_type(datatype)[1] == "dateTime" else ""
        measure_specs.setdefault(
            measure.name,
            (measure.dax, format_spec, measure.display_folder, datatype),
        )
    if overrides:
        for caption, (dax, format_string) in overrides.items():
            measure_specs[caption] = (dax, format_string, "Overrides", "real")

    measure_text: list[str] = []
    for measure_name, (dax, format_string, display_folder, datatype) in measure_specs.items():
        measure_text.extend(
            _measure_block(
                fact_table, measure_name, dax, format_string, display_folder, datatype
            )
        )
    for table_name, additions in columns_by_table.items():
        if table_name == fact_table:
            additions.extend(measure_text)
        table_file = tables_dir / f"{table_name}.tmdl"
        table_text = table_file.read_text(encoding="utf-8")
        table_text = _insert_table_additions(table_text, additions)
        table_file.write_text(table_text, encoding="utf-8")

    relationships_path = definition / "relationships.tmdl"
    relationships = [
        _relationship_tmdl(
            item.from_table, item.from_col, item.to_table, item.to_col
        )
        for item in workbook.relationships
    ]
    relationships.extend(
        _relationship_tmdl(
            item.from_table,
            item.from_column,
            item.to_table,
            item.to_column,
            item.cross_filtering_behavior,
        )
        for item in model_overrides.relationships
    )
    relationships_path.write_text(
        "".join(relationships),
        encoding="utf-8",
    )
    return model_dir
