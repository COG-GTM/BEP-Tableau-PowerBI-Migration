from __future__ import annotations

import json
import re
import textwrap
import uuid
from pathlib import Path

from tableau2pbip.calc.dax import AutoMeasure, CalcTranslation
from tableau2pbip.ir import Parameter, Table, Workbook
from tableau2pbip.overrides import (
    CalculatedTableOverride,
    ModelOverrides,
    ParameterTableOverride,
    TableSourceOverride,
)


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
    lines = _expression_assignment(
        f"\tcolumn {_tag(name)}", dax, property_indent=1
    )
    lines.append(f"\t\tdataType: {dax_type}")
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
    lines = _expression_assignment(
        f"\tmeasure {_tag(name)}", dax, property_indent=1
    )
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


def _tmdl_table(
    table: Table,
    hyper_types: dict[str, str],
    source_override: TableSourceOverride | None = None,
    hidden: bool = False,
) -> str:
    lines = [
        f"table {_tag(table.caption)}",
        f"\tlineageTag: {_lineage(f'table.{table.caption}')}",
        "",
    ]
    if hidden:
        lines.insert(1, "\tisHidden")
    for column in table.columns:
        datatype = hyper_types.get(column.name, column.datatype)
        lines.extend(_physical_column_block(table.caption, column.name, datatype))
    lines.extend(
        [
            f"\tpartition {_tag(table.caption)} = m",
            f"\t\tmode: {source_override.mode if source_override else 'import'}",
            "\t\tsource =",
        ]
    )
    m_source = source_override.m if source_override else _table_m(table, hyper_types)
    lines.extend(_expression_body(m_source, property_indent=2))
    return "\n".join(lines)


def _parameter_table(
    parameter: Parameter,
    override: ParameterTableOverride | None = None,
) -> str:
    data_type = override.data_type if override else parameter.datatype.casefold()
    members = override.values if override else (parameter.members or [parameter.default])
    if data_type in {"integer", "int", "number"}:
        dax_type = "INTEGER"
        values = ", ".join("{" + str(int(member)) + "}" for member in members)
        column_type = "int64"
    elif data_type in {"date", "datetime"}:
        dax_type = "DATETIME"
        values = ", ".join(
            "{DATE("
            + ", ".join(str(int(value)) for value in str(member)[:10].split("-"))
            + ")}"
            for member in members
        )
        column_type = "dateTime"
    else:
        dax_type = "STRING"
        values = ", ".join("{" + json.dumps(str(member)) + "}" for member in members)
        column_type = "string"
    name = parameter.caption
    lines = [
        f"table {_tag(name)}",
        f"\tlineageTag: {_lineage(f'table.{name}')}",
        "",
        f"\tcolumn {_tag(name)}",
        f"\t\tdataType: {column_type}",
    ]
    if column_type == "int64":
        lines.append("\t\tformatString: 0")
    lines.extend(
        [
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
        f"\t\t\tDATATABLE({_m_string(name)}, {dax_type}, {{{values}}})",
        "",
        "\t\tannotation PBI_ResultType = Table",
        "",
        ]
    )
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


def _expression_body(expression: str, property_indent: int) -> list[str]:
    """Return a TMDL-indented body for a multiline expression property."""
    text = textwrap.dedent(expression).strip()
    body_indent = "\t" * (property_indent + 1)
    result: list[str] = []
    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        leading = raw_line[: len(raw_line) - len(raw_line.lstrip(" \t"))]
        tabs = leading.count("\t")
        spaces = leading.count(" ")
        relative_indent = "\t" * tabs + "\t" * (spaces // 4) + " " * (spaces % 4)
        result.append(body_indent + relative_indent + raw_line.lstrip(" \t").rstrip())
    if not result:
        raise ValueError("TMDL expression cannot be empty")
    return result


def _expression_assignment(
    property_name: str, expression: str, property_indent: int
) -> list[str]:
    """Emit an assignment with a valid TMDL multiline body when needed."""
    text = expression.strip()
    if "\n" not in text and "\r" not in text:
        return [f"{property_name} = {text}"]
    return [f"{property_name} ="] + _expression_body(text, property_indent)


def _format_dax_expression(expression: str) -> list[str]:
    return _expression_body(expression, property_indent=2)


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
    from_cardinality: str = "many",
    to_cardinality: str = "one",
    security_filtering_behavior: str = "oneDirection",
    role_tables: set[str] | None = None,
) -> str:
    if from_cardinality == "one" and to_cardinality == "many":
        from_table, to_table = to_table, from_table
        from_column, to_column = to_column, from_column
        from_cardinality, to_cardinality = "many", "one"
    if (
        security_filtering_behavior == "bothDirections"
        and role_tables
        and (
            from_table.casefold() in role_tables
            or to_table.casefold() in role_tables
        )
    ):
        security_filtering_behavior = "oneDirection"
    relation_id = _lineage(
        f"relationship.{from_table}.{from_column}.{to_table}.{to_column}"
    )
    lines = [f"relationship {relation_id}"]
    if not (from_cardinality == "many" and to_cardinality == "one"):
        lines.extend(
            [
                f"\tfromCardinality: {from_cardinality}",
                f"\ttoCardinality: {to_cardinality}",
            ]
        )
    lines.extend(
        [
            f"\tcrossFilteringBehavior: {cross_filtering_behavior}",
            f"\tsecurityFilteringBehavior: {security_filtering_behavior}",
            f"\tfromColumn: {_table_reference(from_table, from_column)}",
            f"\ttoColumn: {_table_reference(to_table, to_column)}",
            "",
        ]
    )
    return "\n".join(lines)


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

    for table in overrides.hidden_tables:
        if table.casefold() not in table_names:
            raise ValueError(f"Hidden table {table!r} is not in the model")

    for relationship in overrides.relationships:
        for side, table, column in (
            ("from", relationship.from_table, relationship.from_column),
            ("to", relationship.to_table, relationship.to_column),
        ):
            if (table.casefold(), column.casefold()) not in fields:
                raise ValueError(
                    f"Override relationship {side} field {table}.{column} is not in the model"
                )
    for relationship in overrides.ignored_relationships:
        for side, table, column in (
            ("from", relationship[0], relationship[1]),
            ("to", relationship[2], relationship[3]),
        ):
            field_exists = (table.casefold(), column.casefold()) in fields
            suffix = f" ({table})"
            if not field_exists and column.casefold().endswith(suffix.casefold()):
                base_column = column[: -len(suffix)]
                field_exists = (table.casefold(), base_column.casefold()) in fields
            if not field_exists:
                raise ValueError(
                    f"Ignored relationship {side} field {table}.{column} is not in the model"
                )
    for source in overrides.table_sources:
        if source.table.casefold() not in physical_tables:
            raise ValueError(
                f"Table source override references unknown table {source.table!r}"
            )
    source_names = [source.table.casefold() for source in overrides.table_sources]
    if len(source_names) != len(set(source_names)):
        raise ValueError("Table source overrides must have unique table names")
    for role in overrides.roles:
        for role_table, _ in role.filters:
            if role_table.casefold() not in table_names:
                raise ValueError(
                    f"Role {role.name!r} references unknown table {role_table!r}"
                )
    parameter_names = {
        parameter.caption.casefold() for parameter in workbook.parameters
    }
    for parameter in overrides.parameter_tables:
        if parameter.name.casefold() not in parameter_names:
            raise ValueError(
                f"Parameter table override references unknown parameter "
                f"{parameter.name!r}"
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


def _validate_measure_names(
    measure_specs: dict[str, tuple[str, str, str, str]],
    duplicate_measure_names: set[str],
    column_names: set[str],
) -> None:
    collisions = {
        name for name in measure_specs if name.casefold() in column_names
    }
    if not collisions and not duplicate_measure_names:
        return
    details: list[str] = []
    if collisions:
        details.append(
            "measures conflict with columns: "
            + ", ".join(sorted(collisions, key=str.casefold))
        )
    if duplicate_measure_names:
        details.append(
            "duplicate measures: "
            + ", ".join(sorted(duplicate_measure_names, key=str.casefold))
        )
    raise ValueError("Invalid model names: " + "; ".join(details))


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
    ignored_parameters = {
        name.casefold() for name in model_overrides.ignored_parameters
    }
    referenced_tables = [table.caption for table in workbook.tables]
    referenced_tables.extend(
        parameter.caption
        for parameter in workbook.parameters
        if parameter.caption.casefold() not in ignored_parameters
    )
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

    source_overrides = {
        source.table.casefold(): source for source in model_overrides.table_sources
    }
    expressions = ""
    if any(
        table.caption.casefold() not in source_overrides for table in workbook.tables
    ):
        expressions = (
            "expression DataFolder =\n"
            f"\t{_m_string(str(data_folder.resolve()))}\n"
            "\tmeta [IsParameterQuery=true, Type=\"Text\", IsParameterQueryRequired=true]\n"
        )
    for parameter in model_overrides.m_parameters:
        if parameter.data_type == "Number":
            value = parameter.value
        elif parameter.data_type == "Date":
            value = (
                f"#date({int(parameter.value[:4])}, "
                f"{int(parameter.value[5:7])}, {int(parameter.value[8:10])})"
            )
        else:
            value = _m_string(parameter.value)
        expressions += (
            f"\nexpression {_tag(parameter.name)} =\n"
            f"\t{value}\n"
            f"\tmeta [IsParameterQuery=true, Type=\"{parameter.data_type}\", "
            "IsParameterQueryRequired=true]\n"
        )
    (definition / "expressions.tmdl").write_text(expressions, encoding="utf-8")

    for table in workbook.tables:
        text = _tmdl_table(
            table,
            hyper_types.get(table.caption, {}),
            source_overrides.get(table.caption.casefold()),
            table.caption.casefold()
            in {name.casefold() for name in model_overrides.hidden_tables},
        )
        (tables_dir / f"{table.caption}.tmdl").write_text(text + "\n", encoding="utf-8")
    parameter_overrides = {
        parameter.name.casefold(): parameter
        for parameter in model_overrides.parameter_tables
    }
    for parameter in workbook.parameters:
        if parameter.caption.casefold() in ignored_parameters:
            continue
        (tables_dir / f"{parameter.caption}.tmdl").write_text(
            _parameter_table(
                parameter, parameter_overrides.get(parameter.caption.casefold())
            ),
            encoding="utf-8",
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
        parameter.internal_name
        for parameter in workbook.parameters
        if parameter.caption.casefold() not in ignored_parameters
    }
    ignored_calculations = {
        name.casefold() for name in model_overrides.ignored_calculations
    }
    for calc in workbook.calcs:
        translation = calculations.get(calc.internal_name)
        if (
            translation is not None
            and calc.internal_name.casefold() not in ignored_calculations
            and calc.caption.casefold() not in ignored_calculations
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
    measure_keys: dict[str, str] = {}
    duplicate_measure_names: set[str] = set()
    for calc in workbook.calcs:
        translation = calculations.get(calc.internal_name)
        if (
            translation is not None
            and translation.status == "supported"
            and translation.dax is not None
            and translation.classification in {"aggregate", "lod", "table_calc"}
        ):
            key = calc.caption.casefold()
            if key in measure_keys:
                duplicate_measure_names.update(
                    {measure_keys[key], calc.caption}
                )
            else:
                measure_keys[key] = calc.caption
                measure_specs[calc.caption] = (
                    translation.dax,
                    calc.format,
                    "Tableau calcs",
                    calc.datatype,
                )
    for measure in auto_measures:
        datatype = _auto_measure_datatype(measure, workbook, hyper_types)
        format_spec = "M/d/yyyy" if _column_type(datatype)[1] == "dateTime" else ""
        key = measure.name.casefold()
        if key in measure_keys:
            duplicate_measure_names.update({measure_keys[key], measure.name})
        else:
            measure_keys[key] = measure.name
            measure_specs[measure.name] = (
                measure.dax,
                format_spec,
                measure.display_folder,
                datatype,
            )
    overridden_measure_keys: set[str] = set()
    if overrides:
        for caption, (dax, format_string) in overrides.items():
            key = caption.casefold()
            if key in overridden_measure_keys:
                duplicate_measure_names.update({measure_keys[key], caption})
            overridden_measure_keys.add(key)
            measure_name = measure_keys.get(key, caption)
            measure_keys.setdefault(key, measure_name)
            measure_specs[measure_name] = (
                dax,
                format_string,
                "Overrides",
                "real",
            )

    column_names = {
        column.name.casefold()
        for table in workbook.tables
        if table.caption.casefold() == fact_table.casefold()
        for column in table.columns
    }
    ignored_calculations = {
        name.casefold() for name in model_overrides.ignored_calculations
    }
    column_names.update(
        calc.caption.casefold()
        for calc in workbook.calcs
        if (
            (translation := calculations.get(calc.internal_name)) is not None
            and calc.internal_name.casefold() not in ignored_calculations
            and calc.caption.casefold() not in ignored_calculations
            and translation.status == "supported"
            and translation.is_calculated_column
            and translation.dax is not None
            and calc.internal_name not in parameter_internal_names
            and calc.caption.casefold() not in overridden_measure_keys
        )
    )
    column_names.update(column.name.casefold() for column in date_columns)
    column_names.update(
        column.name.casefold()
        for column in model_overrides.calculated_columns
        if column.table.casefold() == fact_table.casefold()
    )
    column_names.update(
        column.name.casefold()
        for table in model_overrides.calculated_tables
        if table.name.casefold() == fact_table.casefold()
        for column in table.columns
    )
    _validate_measure_names(measure_specs, duplicate_measure_names, column_names)

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
    relationship_overrides = {
        (
            item.from_table.casefold(),
            item.from_column.casefold(),
            item.to_table.casefold(),
            item.to_column.casefold(),
        ): item
        for item in model_overrides.relationships
    }
    ignored_relationships = {
        tuple(value.casefold() for value in relationship)
        for relationship in model_overrides.ignored_relationships
    }
    role_tables = {
        table.casefold()
        for role in model_overrides.roles
        for table, _ in role.filters
    }
    relationships = []
    for item in workbook.relationships:
        key = (
            item.from_table.casefold(),
            item.from_col.casefold(),
            item.to_table.casefold(),
            item.to_col.casefold(),
        )
        if key in ignored_relationships:
            ignored_relationships.remove(key)
            continue
        override = relationship_overrides.pop(key, None)
        if override is None:
            relationships.append(
                _relationship_tmdl(
                    item.from_table,
                    item.from_col,
                    item.to_table,
                    item.to_col,
                    role_tables=role_tables,
                )
            )
        else:
            relationships.append(
                _relationship_tmdl(
                    override.from_table,
                    override.from_column,
                    override.to_table,
                    override.to_column,
                    override.cross_filtering_behavior,
                    override.from_cardinality,
                    override.to_cardinality,
                    override.security_filtering_behavior,
                    role_tables,
                )
            )
    relationships.extend(
        _relationship_tmdl(
            item.from_table,
            item.from_column,
            item.to_table,
            item.to_column,
            item.cross_filtering_behavior,
            item.from_cardinality,
            item.to_cardinality,
            item.security_filtering_behavior,
            role_tables,
        )
        for item in relationship_overrides.values()
    )
    relationships_path.write_text(
        "".join(relationships),
        encoding="utf-8",
    )
    if model_overrides.roles:
        role_lines = []
        for role in model_overrides.roles:
            role_lines.extend(
                [f"role {_tag(role.name)}", "\tmodelPermission: read"]
            )
            role_lines.extend(
                f"\ttablePermission {_tag(table)} = {expression}"
                for table, expression in role.filters
            )
            role_lines.append("")
        (definition / "roles.tmdl").write_text(
            "\n".join(role_lines), encoding="utf-8"
        )
    return model_dir
