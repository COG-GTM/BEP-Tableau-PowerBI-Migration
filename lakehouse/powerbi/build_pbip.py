from __future__ import annotations

import json
import re
import shutil
import uuid
from pathlib import Path
from typing import Any

import yaml
from deltalake import DeltaTable

from lakehouse.powerbi.dax_from_metricflow import generate_measures
from lakehouse.run_pipeline import LAKEHOUSE_ROOT, snake_case

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
SOURCE_OUTPUT = PROJECT_ROOT / "migrations" / "sales-customer-dashboards" / "output"
OUTPUT_ROOT = PROJECT_ROOT / "migrations" / "sales-customer-dashboards" / "lakehouse"
SEMANTIC_MODELS = PROJECT_ROOT / "lakehouse" / "dbt" / "models" / "semantic_models.yml"
BINDINGS = HERE / "dax_bindings.yml"
MEASURE_SOURCES = HERE / "measure_sources.md"
NAME = "Sales & Customer Dashboards (Lakehouse)"
NAMESPACE = uuid.UUID("f94f42a5-82ee-4cb4-997c-bba168a5753e")

TABLE_FILES = {
    "Orders": ("Orders.tmdl", "fact_orders"),
    "Products": ("Products.tmdl", "dim_product"),
    "Customers": ("Customers.tmdl", "dim_customer"),
    "Location": ("Location.tmdl", "dim_location"),
    "Select Year": ("Select Year.tmdl", "dim_select_year"),
    "Customer Orders by Year": (
        "Customer Orders by Year.tmdl",
        "customer_orders_by_year",
    ),
}
CALCULATED_COLUMN_SOURCES = {
    ("Orders", "Order Date (Year)"): "order_year",
    ("Orders", "Order Date (Month)"): "order_month",
    ("Orders", "Order Date (Week)"): "order_week",
}
_COLUMN_HEADER = re.compile(
    r"^\tcolumn\s+(?P<name>'(?:[^']|'')+'|[^=]+?)(?:\s*=\s*(?P<expression>.*))?$"
)
_MEASURE_HEADER = re.compile(
    r"^\tmeasure\s+(?P<name>'(?:[^']|'')+'|[^\s=]+)\s*=\s*(?P<expression>.*)$"
)
_PARTITION_HEADER = re.compile(r"^\tpartition\s+.+ = (?:m|calculated)$")


def _tag(*parts: str) -> str:
    return str(uuid.uuid5(NAMESPACE, "/".join(parts)))


def _member_end(lines: list[str], start: int) -> int:
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if line.strip() and line.startswith("\t") and not line.startswith("\t\t"):
            return index
    return len(lines)


def _tmdl_name(token: str) -> str:
    token = token.strip()
    if token.startswith("'") and token.endswith("'"):
        return token[1:-1].replace("''", "'")
    return token


def _read_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise TypeError(f"{path} must contain a YAML mapping")
    return loaded


def _gold_columns(lake_root: Path) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for table_name, (_filename, gold_table) in TABLE_FILES.items():
        path = lake_root / "lh_gold.Lakehouse" / "Tables" / gold_table
        if not path.is_dir():
            raise FileNotFoundError(f"Gold Delta table is missing: {path}")
        result[table_name] = set(
            DeltaTable(str(path)).to_pyarrow_table().column_names
        )
    return result


def _rewrite_column_block(
    table_name: str, block: list[str], gold_columns: set[str]
) -> tuple[list[str], bool]:
    header = _COLUMN_HEADER.match(block[0])
    if header is None:
        raise ValueError(f"Invalid TMDL column definition: {block[0]}")
    token = header.group("name").strip()
    column_name = _tmdl_name(token)
    is_calculated = header.group("expression") is not None
    calculated_source = CALCULATED_COLUMN_SOURCES.get((table_name, column_name))
    if is_calculated and calculated_source is None:
        raise ValueError(f"Unexpected calculated column {table_name}[{column_name}]")
    if calculated_source is not None and not is_calculated:
        raise ValueError(
            f"Expected {table_name}[{column_name}] to be a calculated column"
        )

    source_column = calculated_source or snake_case(column_name)
    if source_column not in gold_columns:
        raise ValueError(
            f"Gold table for {table_name} is missing source column {source_column!r}"
        )

    output = [f"\tcolumn {token}" if is_calculated else block[0]]
    found_source_column = False
    for line in block[1:]:
        if line.startswith("\t\tsourceColumn: "):
            if not found_source_column:
                output.append(f"\t\tsourceColumn: {source_column}")
                found_source_column = True
        else:
            output.append(line)
    if not found_source_column:
        insertion = next(
            (
                index
                for index, line in enumerate(output)
                if line.startswith(("\t\tchangedProperty = ", "\t\tannotation "))
            ),
            len(output),
        )
        output.insert(insertion, f"\t\tsourceColumn: {source_column}")
    return output, is_calculated


def _rewrite_columns(table_name: str, text: str, gold_columns: set[str]) -> str:
    lines = text.splitlines()
    output: list[str] = []
    calculated_columns: set[str] = set()
    index = 0
    while index < len(lines):
        if not lines[index].startswith("\tcolumn "):
            output.append(lines[index])
            index += 1
            continue
        end = _member_end(lines, index)
        block, is_calculated = _rewrite_column_block(
            table_name, lines[index:end], gold_columns
        )
        if is_calculated:
            header = _COLUMN_HEADER.match(lines[index])
            assert header is not None
            calculated_columns.add(_tmdl_name(header.group("name")))
        output.extend(block)
        index = end

    expected_calculated = {
        column for table, column in CALCULATED_COLUMN_SOURCES if table == table_name
    }
    if calculated_columns != expected_calculated:
        raise ValueError(
            f"{table_name} calculated columns {sorted(calculated_columns)} do not "
            f"match expected {sorted(expected_calculated)}"
        )
    return "\n".join(output).rstrip() + "\n"


def _rewrite_partition(table_name: str, gold_table: str, text: str) -> str:
    lines = text.splitlines()
    partitions = [
        index
        for index, line in enumerate(lines)
        if _PARTITION_HEADER.match(line)
    ]
    if len(partitions) != 1:
        raise ValueError(
            f"Expected one importable partition for {table_name}, found {len(partitions)}"
        )
    start = partitions[0]
    end = _member_end(lines, start)
    source_is_calculated = lines[start].endswith("= calculated")
    table_definition = lines[:start]
    if source_is_calculated:
        table_definition = [
            line for line in table_definition if line != "\t\tisNameInferred"
        ]
    partition_name = lines[start].rsplit("=", 1)[0].rstrip()
    relative_path = rf"lh_gold.Lakehouse\Tables\{gold_table}"
    partition = [
        f"{partition_name} = m",
        "\t\tmode: import",
        "\t\tsource =",
        (
            "\t\t\tlet Source = DeltaLake.Table("
            f'Folder.Contents(LakehouseRoot & "{relative_path}")) in Source'
        ),
        "",
    ]
    return "\n".join(table_definition + partition + lines[end:]).rstrip() + "\n"


def _year_comparison_measures(
    bindings_path: Path, base_measure_names: set[str]
) -> tuple[dict[str, str], set[str]]:
    bindings = _read_yaml(bindings_path)
    comparison = bindings.get("year_comparison")
    if not isinstance(comparison, dict):
        raise TypeError(f"{bindings_path} must define year_comparison")
    metrics = comparison.get("metrics")
    select_year = comparison.get("select_year")
    order_year = comparison.get("order_year")
    default_year = comparison.get("default_year")
    if (
        not isinstance(metrics, dict)
        or not isinstance(select_year, str)
        or not isinstance(order_year, str)
        or not isinstance(default_year, int)
    ):
        raise TypeError(f"{bindings_path} has an invalid year_comparison mapping")

    generated: dict[str, str] = {}
    wrapper_names: set[str] = set()
    for metric_name, metric in metrics.items():
        if not isinstance(metric, dict):
            raise TypeError(f"year_comparison metric {metric_name!r} must be a mapping")
        base_measure = metric.get("base_measure")
        current = metric.get("current_measure")
        previous = metric.get("previous_measure")
        difference = metric.get("difference_measure")
        difference_denominator = metric.get("difference_denominator", "previous")
        if not all(
            isinstance(value, str)
            for value in (base_measure, current, previous, difference)
        ):
            raise TypeError(f"year_comparison metric {metric_name!r} is incomplete")
        if difference_denominator not in {"current", "previous"}:
            raise ValueError(
                f"year_comparison metric {metric_name!r} has invalid "
                f"difference_denominator {difference_denominator!r}"
            )
        if base_measure not in base_measure_names:
            raise ValueError(
                f"year_comparison metric {metric_name!r} references unknown base "
                f"measure {base_measure!r}"
            )

        year = f"SELECTEDVALUE({select_year}, {default_year})"
        generated[current] = (
            f"VAR y = {year} RETURN CALCULATE([{base_measure}], "
            f"KEEPFILTERS({order_year} = y))"
        )
        generated[previous] = (
            f"VAR y = {year} RETURN CALCULATE([{base_measure}], "
            f"KEEPFILTERS({order_year} = y - 1))"
        )
        denominator = (
            current if difference_denominator == "current" else previous
        )
        generated[difference] = (
            f"DIVIDE([{current}] - [{previous}], [{denominator}])"
        )
        wrapper_names.update((current, previous, difference))
    return generated, wrapper_names


def _model_symbols(table_directory: Path) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    columns: dict[str, list[str]] = {}
    measures: dict[str, list[str]] = {}
    for path in sorted(table_directory.glob("*.tmdl")):
        table_name = path.stem
        lines = path.read_text(encoding="utf-8").splitlines()
        for line in lines:
            column_match = _COLUMN_HEADER.match(line)
            if column_match is not None:
                columns.setdefault(_tmdl_name(column_match.group("name")), []).append(
                    table_name
                )
            measure_match = _MEASURE_HEADER.match(line)
            if measure_match is not None:
                measures.setdefault(_tmdl_name(measure_match.group("name")), []).append(
                    table_name
                )
    return columns, measures


def _check_base_measure_names(
    generated: dict[str, str], table_directory: Path
) -> None:
    columns, measures = _model_symbols(table_directory)
    collisions: dict[str, list[str]] = {}
    for name in generated:
        matching_columns = [
            f"{table}[{column}]"
            for column, tables in columns.items()
            if column.casefold() == name.casefold()
            for table in tables
        ]
        matching_measures = [
            f"{table}[{measure}]"
            for measure, tables in measures.items()
            if measure.casefold() == name.casefold()
            for table in tables
        ]
        if matching_columns or matching_measures:
            collisions[name] = matching_columns + matching_measures
    if collisions:
        raise ValueError(
            "MetricFlow base measure names collide case-insensitively with existing "
            f"model columns or measures: {collisions}"
        )


def _rewrite_measures_and_add_metricflow(
    table_directory: Path,
    generated: dict[str, str],
    wrappers: dict[str, str],
    metric_names: dict[str, str],
) -> set[str]:
    _check_base_measure_names(generated, table_directory)
    expected_wrappers = set(wrappers)
    found_wrappers: set[str] = set()
    for path in sorted(table_directory.glob("*.tmdl")):
        lines = path.read_text(encoding="utf-8").splitlines()
        output: list[str] = []
        index = 0
        while index < len(lines):
            match = _MEASURE_HEADER.match(lines[index])
            if match is None:
                output.append(lines[index])
                index += 1
                continue
            end = _member_end(lines, index)
            name = _tmdl_name(match.group("name"))
            block = lines[index:end]
            replacement = wrappers.get(name)
            if replacement is None:
                output.extend(block)
            else:
                prefix = lines[index].split("=", 1)[0].rstrip()
                output.append(f"{prefix} = {replacement}")
                output.extend(block[1:])
                found_wrappers.add(name)
            index = end
        path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")

    missing_wrappers = expected_wrappers - found_wrappers
    if missing_wrappers:
        raise ValueError(
            f"Year-comparison measures were not found in the converter model: "
            f"{sorted(missing_wrappers)}"
        )

    orders_file = table_directory / "Orders.tmdl"
    lines = orders_file.read_text(encoding="utf-8").splitlines()
    insertion = next(
        (index for index, line in enumerate(lines) if line.startswith("\tpartition ")),
        len(lines),
    )
    additions: list[str] = []
    for label, expression in generated.items():
        metric_name = metric_names[label]
        quoted_label = label.replace("'", "''")
        additions.extend(
            [
                f"\tmeasure '{quoted_label}' = {expression}",
                "\t\tdisplayFolder: MetricFlow",
                f"\t\tlineageTag: {_tag('metricflow', metric_name)}",
                f'\t\tannotation MetricFlowSource = "metricflow:{metric_name}"',
                "",
            ]
        )
    lines[insertion:insertion] = additions
    orders_file.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return set(generated)


def _write_lakehouse_parameter(semantic_model: Path, lake_root: Path) -> None:
    default_root = str(lake_root.resolve()) + "\\"
    expression = (
        f'expression LakehouseRoot = "{default_root}" meta '
        '[IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n'
        f"\tlineageTag: {_tag('expression', 'LakehouseRoot')}\n\n"
        "\tannotation PBI_ResultType = Text\n"
    )
    (semantic_model / "definition" / "expressions.tmdl").write_text(
        expression, encoding="utf-8"
    )


def _clear_generated_contents(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for child in directory.iterdir():
        if child.name == ".pbi":
            continue
        if child.is_dir():
            _clear_generated_contents(child)
            if not any(child.iterdir()):
                child.rmdir()
        else:
            child.unlink()


def _copy_without_pbi(source: Path, destination: Path) -> None:
    shutil.copytree(
        source,
        destination,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(".pbi", "cache.abf", "localSettings.json"),
    )


def _write_measure_sources(
    table_directory: Path,
    metricflow_names: set[str],
    wrapper_names: set[str],
    metric_names: dict[str, str],
    destination: Path,
) -> None:
    rows = [
        "# Generated Power BI measure sources",
        "",
        "| Table | Measure | Source |",
        "| --- | --- | --- |",
    ]
    for path in sorted(table_directory.glob("*.tmdl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            match = _MEASURE_HEADER.match(line)
            if match is None:
                continue
            name = _tmdl_name(match.group("name"))
            if name in metricflow_names:
                source = f"MetricFlow metric `{metric_names[name]}`"
            elif name in wrapper_names:
                source = "year_comparison binding"
            else:
                source = "retained Power BI DAX"
            rows.append(f"| {path.stem} | {name} | {source} |")
    destination.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _assert_no_legacy_sources(semantic_model: Path) -> None:
    for path in (semantic_model / "definition").rglob("*"):
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "Csv.Document" in content or "DataFolder" in content:
            raise AssertionError(f"Legacy CSV source reference remains in {path}")


def _build_model(
    source_model: Path,
    semantic_model: Path,
    lake_root: Path,
    semantic_models_path: Path,
    bindings_path: Path,
) -> tuple[set[str], set[str], dict[str, str]]:
    _clear_generated_contents(semantic_model)
    _copy_without_pbi(source_model, semantic_model)
    table_directory = semantic_model / "definition" / "tables"
    gold_columns = _gold_columns(lake_root)
    for table_name, (filename, gold_table) in TABLE_FILES.items():
        path = table_directory / filename
        text = path.read_text(encoding="utf-8")
        text = _rewrite_columns(table_name, text, gold_columns[table_name])
        text = _rewrite_partition(table_name, gold_table, text)
        path.write_text(text, encoding="utf-8")

    _write_lakehouse_parameter(semantic_model, lake_root)
    generated = generate_measures(semantic_models_path, bindings_path)
    loaded = _read_yaml(semantic_models_path)
    metrics = loaded.get("metrics")
    if not isinstance(metrics, list):
        raise TypeError(f"{semantic_models_path} must define a metrics list")
    metric_names = {
        metric["label"]: metric["name"]
        for metric in metrics
        if isinstance(metric, dict)
        and isinstance(metric.get("label"), str)
        and isinstance(metric.get("name"), str)
    }
    if set(generated) != set(metric_names):
        raise ValueError("Generated measures do not match MetricFlow metric labels")
    wrappers, wrapper_names = _year_comparison_measures(
        bindings_path, set(generated)
    )
    metricflow_names = _rewrite_measures_and_add_metricflow(
        table_directory, generated, wrappers, metric_names
    )
    _assert_no_legacy_sources(semantic_model)
    return metricflow_names, wrapper_names, metric_names


def _build_report(source_report: Path, report: Path) -> None:
    _clear_generated_contents(report)
    _copy_without_pbi(source_report, report)
    definition_pbir = report / "definition.pbir"
    contents = json.loads(definition_pbir.read_text(encoding="utf-8"))
    contents["datasetReference"]["byPath"]["path"] = f"../{NAME}.SemanticModel"
    definition_pbir.write_text(
        json.dumps(contents, indent=2) + "\n", encoding="utf-8"
    )


def build_pbip(
    source_output: Path = SOURCE_OUTPUT,
    output_root: Path = OUTPUT_ROOT,
    lake_root: Path = LAKEHOUSE_ROOT,
    semantic_models_path: Path = SEMANTIC_MODELS,
    bindings_path: Path = BINDINGS,
    measure_sources_path: Path = MEASURE_SOURCES,
) -> Path:
    source_model = source_output / "Sales & Customer Dashboards.SemanticModel"
    source_report = source_output / "Sales & Customer Dashboards.Report"
    if not source_model.is_dir() or not source_report.is_dir():
        raise FileNotFoundError(f"Converter PBIP artifacts were not found under {source_output}")

    output_root.mkdir(parents=True, exist_ok=True)
    semantic_model = output_root / f"{NAME}.SemanticModel"
    report = output_root / f"{NAME}.Report"
    metricflow_names, wrapper_names, metric_names = _build_model(
        source_model,
        semantic_model,
        lake_root,
        semantic_models_path,
        bindings_path,
    )
    _build_report(source_report, report)

    pbip = {
        "version": "1.0",
        "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
        "settings": {"enableAutoRecovery": True},
    }
    (output_root / f"{NAME}.pbip").write_text(
        json.dumps(pbip, indent=2) + "\n", encoding="utf-8"
    )
    (output_root / ".gitignore").write_text(
        "**/.pbi/cache.abf\n**/.pbi/localSettings.json\n", encoding="utf-8"
    )
    _write_measure_sources(
        semantic_model / "definition" / "tables",
        metricflow_names,
        wrapper_names,
        metric_names,
        measure_sources_path,
    )
    return output_root / f"{NAME}.pbip"


def main() -> None:
    print(build_pbip())


if __name__ == "__main__":
    main()
