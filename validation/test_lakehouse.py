from __future__ import annotations

import importlib
import re
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import pytest

from lakehouse.verify.verify_parity import _read_query_csv
from tableau2pbip.extract import _deduplicate

ROOT = Path(__file__).resolve().parents[1]
CONVERTER_OUTPUT = ROOT / "migrations" / "sales-customer-dashboards" / "output"
LAKEHOUSE_SCHEMAS = {
    "fact_orders": (
        "row_id",
        "order_id",
        "order_date",
        "ship_date",
        "ship_mode",
        "customer_id",
        "segment",
        "postal_code",
        "product_id",
        "sales",
        "quantity",
        "discount",
        "profit",
        "order_year",
        "order_month",
        "order_week",
    ),
    "dim_product": ("product_id", "category", "sub_category", "product_name"),
    "dim_customer": ("customer_id", "customer_name"),
    "dim_location": (
        "postal_code",
        "city",
        "state",
        "region",
        "country_region",
    ),
    "dim_select_year": ("select_year",),
    "customer_orders_by_year": (
        "customer_id",
        "year",
        "nr_of_orders_per_customers",
    ),
}


def _weeknum_monday(date_value: date) -> int:
    january_first = date(date_value.year, 1, 1)
    return (
        date_value.timetuple().tm_yday - 1 + january_first.isoweekday() - 1
    ) // 7 + 1


def test_order_week_matches_weeknum_two_for_every_date_in_range() -> None:
    duckdb = pytest.importorskip("duckdb")
    rows = duckdb.sql(
        """
        select
            date_value::date,
            (
                (
                    dayofyear(date_value) - 1
                    + isodow(make_date(year(date_value), 1, 1)) - 1
                ) // 7
            ) + 1
        from generate_series(
            date '2019-12-25',
            date '2024-01-07',
            interval '1 day'
        ) as dates(date_value)
        order by date_value
        """
    ).fetchall()
    expected_dates: list[date] = []
    current = date(2019, 12, 25)
    stop = date(2024, 1, 7)
    while current <= stop:
        expected_dates.append(current)
        current += timedelta(days=1)
    assert [row[0] for row in rows] == expected_dates
    assert [row[1] for row in rows] == [
        _weeknum_monday(date_value) for date_value in expected_dates
    ]


def test_dimension_deduplication_keeps_first_nonblank_key_row() -> None:
    rows = [
        ["A", "first"],
        ["A", "later"],
        ["", "empty key"],
        [" ", "whitespace key"],
        ["B", "first B"],
        ["B", "later B"],
    ]
    deduplicated, conflict = _deduplicate(
        type("TableStub", (), {"caption": "Products"})(),
        ["Product ID", "Product Name"],
        rows,
        "Product ID",
        set(),
    )

    assert deduplicated == [["A", "first"], ["B", "first B"]]
    assert conflict is not None
    assert conflict.duplicate_keys == 2


def test_parity_csv_reader_normalizes_adomd_bracketed_column_names(
    tmp_path: Path,
) -> None:
    (tmp_path / "2023_category.csv").write_text(
        "[Category],[metric_0],[metric_1]\nOffice Supplies,733.25,693\n",
        encoding="utf-8",
    )

    result = _read_query_csv(
        tmp_path,
        "2023_category",
        2023,
        "category",
        ["Total Sales", "Total Customers"],
    )

    assert result == {
        (2023, "category", "Office Supplies", "Total Sales"): "733.25",
        (2023, "category", "Office Supplies", "Total Customers"): "693",
    }


def _write_gold_schema_fixtures(
    root: Path, pyarrow: Any, write_deltalake: Any
) -> None:
    for table_name, columns in LAKEHOUSE_SCHEMAS.items():
        table_path = root / "lh_gold.Lakehouse" / "Tables" / table_name
        table_path.parent.mkdir(parents=True, exist_ok=True)
        table = pyarrow.table(
            {column: pyarrow.array(["fixture"]) for column in columns}
        )
        write_deltalake(str(table_path), table)


def _tmdl_columns(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    column_name: str | None = None
    sources: dict[str, str] = {}
    for line in lines:
        if line.startswith("\tcolumn "):
            token = line.removeprefix("\tcolumn ").split(" =", 1)[0].strip()
            column_name = token[1:-1].replace("''", "'") if token.startswith("'") else token
        elif column_name is not None and line.startswith("\t\tsourceColumn: "):
            sources[column_name] = line.removeprefix("\t\tsourceColumn: ")
            column_name = None
    return sources


def _report_files(directory: Path) -> dict[str, bytes]:
    return {
        path.relative_to(directory).as_posix(): path.read_bytes()
        for path in directory.rglob("*")
        if path.is_file()
        and ".pbi" not in path.relative_to(directory).parts
        and path.name != "definition.pbir"
    }


def test_build_pbip_rewrites_real_converter_model_to_gold_delta() -> None:
    pytest.importorskip("duckdb")
    delta_module = pytest.importorskip("deltalake")
    pyarrow = pytest.importorskip("pyarrow")
    build_pbip = importlib.import_module(
        "lakehouse.powerbi.build_pbip"
    ).build_pbip
    with TemporaryDirectory(prefix="lhpbip") as temporary:
        temporary_root = Path(temporary)
        lake_root = temporary_root / "l"
        _write_gold_schema_fixtures(
            lake_root, pyarrow, delta_module.write_deltalake
        )
        output_root = temporary_root / "o"
        measure_sources = temporary_root / "m.md"

        pbip = build_pbip(
            source_output=CONVERTER_OUTPUT,
            output_root=output_root,
            lake_root=lake_root,
            measure_sources_path=measure_sources,
        )

        model = output_root / "Sales & Customer Dashboards (Lakehouse).SemanticModel"
        report = output_root / "Sales & Customer Dashboards (Lakehouse).Report"
        assert pbip.is_file()
        assert model.is_dir()
        assert report.is_dir()

        source_report = CONVERTER_OUTPUT / "Sales & Customer Dashboards.Report"
        assert _report_files(source_report) == _report_files(report)
        definition_pbir = report / "definition.pbir"
        assert (
            json_load(definition_pbir)["datasetReference"]["byPath"]["path"]
            == "../Sales & Customer Dashboards (Lakehouse).SemanticModel"
        )

        table_directory = model / "definition" / "tables"
        model_text = "\n".join(
            path.read_text(encoding="utf-8") for path in table_directory.glob("*.tmdl")
        )
        assert "Csv.Document" not in model_text
        assert "DataFolder" not in model_text
        assert "LakehouseRoot" in model_text

        expected_columns = {
            "Orders.tmdl": {
                "Row ID": "row_id",
                "Order ID": "order_id",
                "Order Date": "order_date",
                "Ship Date": "ship_date",
                "Ship Mode": "ship_mode",
                "Customer ID": "customer_id",
                "Segment": "segment",
                "Postal Code": "postal_code",
                "Product ID": "product_id",
                "Sales": "sales",
                "Quantity": "quantity",
                "Discount": "discount",
                "Profit": "profit",
                "Order Date (Year)": "order_year",
                "Order Date (Month)": "order_month",
                "Order Date (Week)": "order_week",
            },
            "Products.tmdl": {
                "Product ID": "product_id",
                "Category": "category",
                "Sub-Category": "sub_category",
                "Product Name": "product_name",
            },
            "Customers.tmdl": {
                "Customer ID": "customer_id",
                "Customer Name": "customer_name",
            },
            "Location.tmdl": {
                "Postal Code": "postal_code",
                "City": "city",
                "State": "state",
                "Region": "region",
                "Country/Region": "country_region",
            },
            "Select Year.tmdl": {"Select Year": "select_year"},
            "Customer Orders by Year.tmdl": {
                "Customer ID": "customer_id",
                "Year": "year",
                "Nr of Orders per Customers": "nr_of_orders_per_customers",
            },
        }
        for filename, expected in expected_columns.items():
            assert _tmdl_columns(table_directory / filename) == expected

        for filename, partition_name in (
            ("Select Year.tmdl", "Select Year"),
            ("Customer Orders by Year.tmdl", "Customer Orders by Year"),
        ):
            text = (table_directory / filename).read_text(encoding="utf-8")
            assert f"partition '{partition_name}' = m" in text
            assert f"partition '{partition_name}' = calculated" not in text
            assert "isNameInferred" not in text
            assert "DeltaLake.Table(Folder.Contents(LakehouseRoot & " in text

        measures = {
            match.group(1): match.group(2)
            for match in re.finditer(
                r"^\tmeasure '((?:[^']|'')+)' = (.+)$",
                (table_directory / "Orders.tmdl").read_text(encoding="utf-8"),
                re.MULTILINE,
            )
        }
        assert measures["Total Sales"] == "SUM('Orders'[Sales])"
        assert measures["Total Profit"] == "SUM('Orders'[Profit])"
        assert measures["Total Quantity"] == "SUM('Orders'[Quantity])"
        assert measures["Total Customers"] == "DISTINCTCOUNT('Orders'[Customer ID])"
        assert measures["Total Orders"] == "DISTINCTCOUNT('Orders'[Order ID])"
        assert measures["Sales per Customer"] == (
            "DIVIDE([Total Sales], [Total Customers])"
        )
        assert measures["CY Sales"] == (
            "VAR y = SELECTEDVALUE('Select Year'[Select Year], 2023) RETURN "
            "CALCULATE([Total Sales], KEEPFILTERS('Orders'[Order Date (Year)] = y))"
        )
        assert measures["PY Sales"] == (
            "VAR y = SELECTEDVALUE('Select Year'[Select Year], 2023) RETURN "
            "CALCULATE([Total Sales], KEEPFILTERS('Orders'[Order Date (Year)] = y - 1))"
        )
        assert measures["% Diff Sales"] == (
            "DIVIDE([CY Sales] - [PY Sales], [PY Sales])"
        )
        assert measures["% Diff Profit"] == (
            "DIVIDE([CY Profit] - [PY Profit], [CY Profit])"
        )
        assert measure_sources.read_text(encoding="utf-8").count("| Orders |") > 6


def json_load(path: Path) -> dict[str, object]:
    import json

    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value
