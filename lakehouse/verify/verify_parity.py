from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import tempfile
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONVERTER_MODEL = (
    ROOT
    / "migrations"
    / "sales-customer-dashboards"
    / "output"
    / "Sales & Customer Dashboards.SemanticModel"
)
LAKEHOUSE_MODEL = (
    ROOT
    / "migrations"
    / "sales-customer-dashboards"
    / "lakehouse"
    / "Sales & Customer Dashboards (Lakehouse).SemanticModel"
)
RUN_DAX = Path(__file__).with_name("run_dax.ps1")
YEARS = range(2020, 2024)
GROUPINGS = {
    "none": None,
    "order_month": "'Orders'[Order Date (Month)]",
    "order_week": "'Orders'[Order Date (Week)]",
    "product_category": "'Products'[Category]",
    "product_sub_category": "'Products'[Sub-Category]",
    "location_region": "'Location'[Region]",
    "location_state": "'Location'[State]",
    "orders_per_customer": (
        "'Customer Orders by Year'[Nr of Orders per Customers]"
    ),
    "customer_name": "'Customers'[Customer Name]",
}
REL_TOLERANCE = Decimal("1e-9")
ABS_TOLERANCE = Decimal("1e-6")
_MEASURE_HEADER = re.compile(
    r"^\tmeasure\s+(?P<name>'(?:[^']|'')+'|[^\s=]+)\s*=",
    re.MULTILINE,
)


def _measure_name(token: str) -> str:
    if token.startswith("'") and token.endswith("'"):
        return token[1:-1].replace("''", "'")
    return token


def _measure_names(model: Path) -> list[str]:
    names = {
        _measure_name(match.group("name"))
        for path in sorted((model / "definition" / "tables").glob("*.tmdl"))
        for match in _MEASURE_HEADER.finditer(path.read_text(encoding="utf-8"))
    }
    return sorted(names, key=str.casefold)


def _dax_measure_reference(name: str) -> str:
    return "[" + name.replace("]", "]]") + "]"


def _dax_string(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _query(year: int, grouping: str | None, measures: list[str]) -> str:
    arguments: list[str] = []
    if grouping is not None:
        arguments.append(grouping)
    arguments.append(f"TREATAS({{{year}}}, 'Select Year'[Select Year])")
    for index, measure in enumerate(measures):
        arguments.extend(
            (_dax_string(f"metric_{index}"), _dax_measure_reference(measure))
        )
    return "EVALUATE\nSUMMARIZECOLUMNS(\n    " + ",\n    ".join(arguments) + "\n)\n"


def _write_queries(directory: Path, measures: list[str]) -> dict[str, tuple[int, str, list[str]]]:
    directory.mkdir(parents=True, exist_ok=True)
    identifiers: dict[str, tuple[int, str, list[str]]] = {}
    for year in YEARS:
        for grouping_name, grouping_column in GROUPINGS.items():
            identifier = f"{year}_{grouping_name}"
            path = directory / f"{identifier}.dax"
            path.write_text(
                _query(year, grouping_column, measures), encoding="utf-8"
            )
            identifiers[identifier] = (year, grouping_name, measures)
    return identifiers


def _run_queries(directory: Path, port: int) -> None:
    for year in YEARS:
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(RUN_DAX),
                "-Dir",
                str(directory),
                "-Port",
                str(port),
                "-Filter",
                f"{year}_*.dax",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"DAX execution failed for localhost:{port}, year {year}.\n"
                f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
            )


def _read_query_csv(
    directory: Path,
    identifier: str,
    year: int,
    grouping_name: str,
    measures: list[str],
) -> dict[tuple[int, str, str, str], str | None]:
    path = directory / f"{identifier}.csv"
    if not path.is_file():
        raise FileNotFoundError(f"DAX query output was not created: {path}")
    measure_columns = {
        f"metric_{index}": measure for index, measure in enumerate(measures)
    }
    result: dict[tuple[int, str, str, str], str | None] = {}
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None:
            raise ValueError(f"DAX output has no header: {path}")
        raw_columns = {_normalize_column_name(field): field for field in reader.fieldnames}
        missing_metrics = set(measure_columns) - set(raw_columns)
        if missing_metrics:
            raise ValueError(f"Missing measure columns in {path}: {sorted(missing_metrics)}")
        group_columns = [
            field
            for field in reader.fieldnames
            if _normalize_column_name(field) not in measure_columns
        ]
        if grouping_name == "none":
            if group_columns:
                raise ValueError(f"Unexpected grouping column in {path}: {group_columns}")
            group_column = None
        else:
            if len(group_columns) != 1:
                raise ValueError(
                    f"Expected one grouping column in {path}, found {group_columns}"
                )
            group_column = group_columns[0]
        for row in reader:
            group_value = (
                (row.get(group_column) or "").strip() if group_column is not None else ""
            )
            for alias, measure in measure_columns.items():
                key = (year, grouping_name, group_value, measure)
                value = row.get(raw_columns[alias])
                result[key] = value if value not in (None, "") else None
    return result


def _normalize_column_name(name: str) -> str:
    if name.startswith("[") and name.endswith("]"):
        return name[1:-1]
    return name


def _as_decimal(value: str | None) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def _compare_values(
    left: str | None, right: str | None
) -> tuple[bool, str | None, str | None]:
    left_number = _as_decimal(left)
    right_number = _as_decimal(right)
    if left_number is None or right_number is None:
        equal = left == right or (
            left_number is not None and right_number is not None and left_number == right_number
        )
        return equal, None, None
    absolute = abs(left_number - right_number)
    scale = max(abs(left_number), abs(right_number))
    relative = absolute / scale if scale else Decimal(0)
    equal = absolute <= max(ABS_TOLERANCE, REL_TOLERANCE * scale)
    return equal, str(absolute), str(relative)


def _read_model_results(
    directory: Path,
    identifiers: dict[str, tuple[int, str, list[str]]],
) -> dict[tuple[int, str, str, str], str | None]:
    results: dict[tuple[int, str, str, str], str | None] = {}
    for identifier, (year, grouping_name, measures) in identifiers.items():
        results.update(
            _read_query_csv(directory, identifier, year, grouping_name, measures)
        )
    return results


def _compare_models(
    converter: dict[tuple[int, str, str, str], str | None],
    lakehouse: dict[tuple[int, str, str, str], str | None],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in sorted(set(converter) | set(lakehouse)):
        converter_present = key in converter
        lakehouse_present = key in lakehouse
        left = converter.get(key)
        right = lakehouse.get(key)
        equal, absolute, relative = _compare_values(left, right)
        equal = equal and converter_present == lakehouse_present
        year, grouping, group_value, measure = key
        rows.append(
            {
                "year": year,
                "grouping": grouping,
                "group_value": group_value,
                "measure": measure,
                "converter_value": left,
                "lakehouse_value": right,
                "converter_row_present": converter_present,
                "lakehouse_row_present": lakehouse_present,
                "equal": equal,
                "absolute_difference": absolute,
                "relative_difference": relative,
            }
        )
    return rows


def verify_parity(
    converter_port: int,
    lakehouse_port: int,
    converter_model: Path = CONVERTER_MODEL,
    lakehouse_model: Path = LAKEHOUSE_MODEL,
    output_dir: Path = Path(__file__).with_name("out"),
) -> dict[str, Any]:
    measures = _measure_names(converter_model)
    if not measures:
        raise ValueError(f"No measures were found in {converter_model}")
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="sales_lakehouse_parity_") as temporary:
        work = Path(temporary)
        converter_queries = work / "converter"
        lakehouse_queries = work / "lakehouse"
        identifiers = _write_queries(converter_queries, measures)
        _write_queries(lakehouse_queries, measures)
        _run_queries(converter_queries, converter_port)
        _run_queries(lakehouse_queries, lakehouse_port)
        converter_results = _read_model_results(converter_queries, identifiers)
        lakehouse_results = _read_model_results(lakehouse_queries, identifiers)

    comparisons = _compare_models(converter_results, lakehouse_results)
    csv_path = output_dir / "parity_values.csv"
    json_path = output_dir / "parity_summary.json"
    columns = (
        "year",
        "grouping",
        "group_value",
        "measure",
        "converter_value",
        "lakehouse_value",
        "converter_row_present",
        "lakehouse_row_present",
        "equal",
        "absolute_difference",
        "relative_difference",
    )
    with csv_path.open("w", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=columns)
        writer.writeheader()
        writer.writerows(comparisons)

    differences = [comparison for comparison in comparisons if not comparison["equal"]]
    summary: dict[str, Any] = {
        "converter_port": converter_port,
        "lakehouse_port": lakehouse_port,
        "converter_model": str(converter_model),
        "lakehouse_model": str(lakehouse_model),
        "years": list(YEARS),
        "groupings": list(GROUPINGS),
        "measures": measures,
        "tolerance": {
            "relative": str(REL_TOLERANCE),
            "absolute": str(ABS_TOLERANCE),
        },
        "values_compared": len(comparisons),
        "differences": len(differences),
        "difference_examples": differences[:100],
        "csv": str(csv_path),
        "summary_json": str(json_path),
    }
    json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare converter and lakehouse PBIP measures over local AS."
    )
    parser.add_argument("--converter-port", type=int, required=True)
    parser.add_argument("--lakehouse-port", type=int, required=True)
    parser.add_argument("--converter-model", type=Path, default=CONVERTER_MODEL)
    parser.add_argument("--lakehouse-model", type=Path, default=LAKEHOUSE_MODEL)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).with_name("out"))
    arguments = parser.parse_args()
    summary = verify_parity(
        arguments.converter_port,
        arguments.lakehouse_port,
        arguments.converter_model,
        arguments.lakehouse_model,
        arguments.output_dir,
    )
    print(json.dumps(summary, indent=2))
    if summary["differences"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
