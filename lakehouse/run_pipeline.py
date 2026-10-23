from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import duckdb
import pyarrow as pa
from deltalake import write_deltalake

from tableau2pbip.extract import RawExtractTable, read_hyper_tables
from tableau2pbip.parse import parse_workbook
from tableau2pbip.unpack import unpack

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKBOOK = (
    PROJECT_ROOT
    / "projects"
    / "sales-dashboard-project"
    / "Sales & Customer Dashboards.twbx"
)
LAKEHOUSE_ROOT = PROJECT_ROOT / "lakehouse" / "onelake" / "SalesCustomer"
DBT_PROJECT = PROJECT_ROOT / "lakehouse" / "dbt"

SOURCE_TABLES = (
    ("Orders", "orders"),
    ("Products", "products"),
    ("Customers", "customers"),
    ("Location", "location"),
)
SILVER_TABLES = (
    "silver_orders",
    "silver_products",
    "silver_customers",
    "silver_location",
)
GOLD_TABLES = (
    "fact_orders",
    "dim_product",
    "dim_customer",
    "dim_location",
    "dim_select_year",
    "customer_orders_by_year",
)
EXPECTED_ROW_COUNTS = {
    "bronze": {
        "orders": 9_994,
        "products": 1_894,
        "customers": 793,
        "location": 632,
    },
    "silver": {
        "silver_orders": 9_994,
        "silver_products": 1_862,
        "silver_customers": 793,
        "silver_location": 630,
    },
    "gold": {
        "fact_orders": 9_994,
        "dim_product": 1_862,
        "dim_customer": 793,
        "dim_location": 630,
        "dim_select_year": 4,
        "customer_orders_by_year": 3_172,
    },
}

_NUMERIC_TYPE = re.compile(r"^NUMERIC\((\d+),\s*(\d+)\)$", re.IGNORECASE)


def snake_case(value: str) -> str:
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()


def _arrow_type(hyper_type: str) -> pa.DataType:
    normalized = hyper_type.upper()
    simple_types = {
        "TEXT": pa.string(),
        "VARCHAR": pa.string(),
        "BOOLEAN": pa.bool_(),
        "SMALL_INT": pa.int16(),
        "INT": pa.int32(),
        "INTEGER": pa.int32(),
        "BIG_INT": pa.int64(),
        "FLOAT": pa.float32(),
        "DOUBLE": pa.float64(),
        "DATE": pa.date32(),
        "TIMESTAMP": pa.timestamp("us"),
        "TIMESTAMP_TZ": pa.timestamp("us", tz="UTC"),
    }
    if normalized in simple_types:
        return simple_types[normalized]
    numeric = _NUMERIC_TYPE.fullmatch(normalized)
    if numeric:
        return pa.decimal128(int(numeric.group(1)), int(numeric.group(2)))
    if normalized.startswith("VARCHAR("):
        return pa.string()
    raise ValueError(f"Unsupported Hyper column type {hyper_type!r}")


def _arrow_value(value: Any, hyper_type: str) -> Any:
    if value is None:
        return None
    if hyper_type.upper() == "DATE" and not isinstance(value, date):
        return date(value.year, value.month, value.day)
    if hyper_type.upper().startswith("NUMERIC(") and not isinstance(value, Decimal):
        return Decimal(str(value))
    return value


def _source_table(
    raw_table: RawExtractTable, twbx: Path, destination_name: str
) -> pa.Table:
    columns = [snake_case(column) for column in raw_table.columns]
    if len(columns) != len(set(columns)):
        raise ValueError(
            f"{raw_table.caption} has columns that collide after snake_case normalization"
        )
    arrays: dict[str, pa.Array] = {}
    for index, column in enumerate(raw_table.columns):
        hyper_type = raw_table.column_types[column]
        values = [
            _arrow_value(row[index], hyper_type) for row in raw_table.rows
        ]
        arrays[snake_case(column)] = pa.array(values, type=_arrow_type(hyper_type))

    ingested_at = datetime.now(UTC)
    row_count = len(raw_table.rows)
    arrays["_row_number"] = pa.array(range(1, row_count + 1), type=pa.int64())
    arrays["_ingested_at"] = pa.array(
        [ingested_at] * row_count, type=pa.timestamp("us", tz="UTC")
    )
    arrays["_source_file"] = pa.array(
        [f"{twbx.name}::{raw_table.hyper_table}"] * row_count,
        type=pa.string(),
    )
    return pa.table(arrays)


def _table_path(layer: str, table: str) -> Path:
    return LAKEHOUSE_ROOT / f"lh_{layer}.Lakehouse" / "Tables" / table


def _write_bronze_tables(twbx: Path) -> dict[str, int]:
    row_counts: dict[str, int] = {}
    with TemporaryDirectory(prefix="tableau-lakehouse-") as temp_dir:
        unpacked = unpack(twbx, Path(temp_dir))
        workbook = parse_workbook(unpacked.twb_path)
        raw_tables = read_hyper_tables(unpacked, workbook)
        for caption, table_name in SOURCE_TABLES:
            if caption not in raw_tables:
                raise ValueError(f"Hyper extract is missing source table {caption!r}")
            table = _source_table(raw_tables[caption], twbx, table_name)
            destination = _table_path("bronze", table_name)
            destination.parent.mkdir(parents=True, exist_ok=True)
            write_deltalake(
                str(destination),
                table,
                mode="overwrite",
                schema_mode="overwrite",
            )
            row_counts[table_name] = table.num_rows
    return row_counts


def _build_dbt() -> None:
    executable_name = "dbt.exe" if os.name == "nt" else "dbt"
    dbt_executable = Path(sys.executable).with_name(executable_name)
    if not dbt_executable.is_file():
        raise FileNotFoundError(f"dbt executable was not found next to {sys.executable}")
    command = [
        str(dbt_executable),
        "build",
        "--project-dir",
        str(DBT_PROJECT),
        "--profiles-dir",
        str(DBT_PROJECT),
        "--vars",
        json.dumps({"lake_root": LAKEHOUSE_ROOT.as_posix()}),
    ]
    environment = os.environ.copy()
    environment["PYTHONIOENCODING"] = "utf-8"
    subprocess.run(command, cwd=DBT_PROJECT, env=environment, check=True)


def _publish_models(
    model_names: tuple[str, ...],
    layer: str,
    connection: duckdb.DuckDBPyConnection,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for model_name in model_names:
        table = connection.execute(
            f'SELECT * FROM main."{model_name}"'
    ).to_arrow_table()
        destination = _table_path(layer, model_name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        write_deltalake(
            str(destination),
            table,
            mode="overwrite",
            schema_mode="overwrite",
        )
        counts[model_name] = table.num_rows
    return counts


def _assert_counts(row_counts: dict[str, dict[str, int]]) -> None:
    mismatches = {
        layer: {
            table: (row_counts.get(layer, {}).get(table), expected)
            for table, expected in expected_counts.items()
            if row_counts.get(layer, {}).get(table) != expected
        }
        for layer, expected_counts in EXPECTED_ROW_COUNTS.items()
    }
    mismatches = {layer: values for layer, values in mismatches.items() if values}
    if mismatches:
        raise ValueError(f"Lakehouse row counts differ from expected counts: {mismatches}")


def run_pipeline(twbx: Path = DEFAULT_WORKBOOK) -> dict[str, dict[str, int]]:
    if not twbx.is_file():
        raise FileNotFoundError(f"Tableau workbook does not exist: {twbx}")
    row_counts: dict[str, dict[str, int]] = {
        "bronze": _write_bronze_tables(twbx),
        "silver": {},
        "gold": {},
    }
    _build_dbt()
    database = DBT_PROJECT / "target" / "lakehouse.duckdb"
    if not database.is_file():
        raise FileNotFoundError(f"dbt did not create the DuckDB target: {database}")
    connection = duckdb.connect(str(database), read_only=True)
    try:
        row_counts["silver"] = _publish_models(SILVER_TABLES, "silver", connection)
        row_counts["gold"] = _publish_models(GOLD_TABLES, "gold", connection)
    finally:
        connection.close()
    _assert_counts(row_counts)
    for layer, counts in row_counts.items():
        print(f"{layer.title()} row counts:")
        for table_name, count in counts.items():
            print(f"  {table_name}: {count:,}")
    return row_counts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--twbx", type=Path, default=DEFAULT_WORKBOOK)
    args = parser.parse_args()
    run_pipeline(args.twbx)


if __name__ == "__main__":
    main()
