from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from tableau2pbip.calc.ast import Binary, Call, Field, Literal
from tableau2pbip.calc.dax import CalculationCompiler, generate_auto_measures
from tableau2pbip.calc.parser import parse
from tableau2pbip.extract import extract_tables
from tableau2pbip.parse import decode_field_ref, parse_workbook
from tableau2pbip.pbir import generate_pbir
from tableau2pbip.tmdl import generate_tmdl
from tableau2pbip.unpack import unpack


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_PATH = (
    ROOT
    / "projects"
    / "sales-dashboard-project"
    / "Sales & Customer Dashboards.twbx"
)


@pytest.fixture
def workbook_and_unpacked(tmp_path: Path):
    unpacked = unpack(WORKBOOK_PATH, tmp_path / "unpacked")
    return unpacked, parse_workbook(unpacked.twb_path)


def test_lexer_parser_and_field_ref_shapes() -> None:
    expression = parse("1 + 2 * 3 // comment\n")
    assert isinstance(expression, Binary)
    assert expression.operator == "+"
    assert isinstance(expression.right, Binary)
    assert isinstance(parse("'text'"), Literal)
    assert isinstance(parse("[Sales]"), Field)
    assert isinstance(parse("SUM([Sales])"), Call)

    reference = decode_field_ref(
        "[federated.x].[sum:Calculation_123:qk]",
        {"Calculation_123": "CY Sales"},
    )
    assert reference.datasource == "federated.x"
    assert reference.derivation == "sum"
    assert reference.field_internal == "Calculation_123"
    assert reference.field_caption == "CY Sales"
    assert reference.type_suffix == "qk"


@pytest.mark.parametrize(
    ("formula", "expected"),
    [
        ("SUM([Sales])", "SUM("),
        ("AVG([Sales])", "AVERAGE("),
        ("MIN([Sales])", "MIN("),
        ("MAX([Sales])", "MAX("),
        ("COUNT([Order ID])", "COUNT("),
        ("COUNTD([Order ID])", "DISTINCTCOUNT("),
        ("ATTR([Sales])", "SELECTEDVALUE("),
        ("IIF([Sales] > 0, 1, 0)", "IF("),
        ("IF [Sales] > 0 THEN 1 ELSE 0 END", "IF("),
        ("IF [Sales] > 0 THEN 1 ELSEIF [Sales] < 0 THEN -1 ELSE 0 END", "IF("),
        ("[Sales] >= 1 AND NOT ISNULL([Sales])", "&&"),
        ("[Sales] = 1 OR [Sales] = 2", "||"),
        ("CASE [Segment] WHEN 'A' THEN 1 ELSE 0 END", "SWITCH("),
        ("ZN([Sales])", "COALESCE("),
        ("ISNULL([Sales])", "ISBLANK("),
        ("IFNULL([Sales], 0)", "COALESCE("),
        ("YEAR(#2023-01-01#)", "YEAR("),
        ("MONTH(#2023-01-01#)", "MONTH("),
        ("DAY(#2023-01-01#)", "DAY("),
        ("QUARTER(#2023-01-01#)", "QUARTER("),
        ("DATEPART('year', #2023-01-01#)", "YEAR("),
        ("DATEPART('month', #2023-01-01#)", "MONTH("),
        ("DATEPART('week', #2023-01-01#)", "WEEKNUM("),
        ("DATEPART('day', #2023-01-01#)", "DAY("),
        ("DATEPART('quarter', #2023-01-01#)", "QUARTER("),
        ("LEFT('abc', 1)", "LEFT("),
        ("RIGHT('abc', 1)", "RIGHT("),
        ("MID('abc', 2, 1)", "MID("),
        ("CONTAINS('abc', 'b')", "CONTAINSSTRING("),
        ("UPPER('a')", "UPPER("),
        ("LOWER('A')", "LOWER("),
        ("LEN('abc')", "LEN("),
        ("TRIM(' abc ')", "TRIM("),
        ("ROUND(1.25, 1)", "ROUND("),
        ("ABS(-1)", "ABS("),
        ("INT(1.5)", "TRUNC("),
        ("FLOAT('1.5')", "VALUE("),
        ("STR(1.5)", "FORMAT("),
        ("1 / 2", "DIVIDE("),
        ("{ SUM([Sales]) }", "CALCULATE("),
        ("{ FIXED [Customer ID]: COUNTD([Order ID]) }", "SUMX(VALUES("),
    ],
)
def test_calculation_function_shapes(
    workbook_and_unpacked, formula: str, expected: str
) -> None:
    _, workbook = workbook_and_unpacked
    compiler = CalculationCompiler(workbook)
    dax = compiler._emit(parse(formula), row_context=False)
    assert expected in dax


def test_unsupported_function_is_reported_not_raised(workbook_and_unpacked) -> None:
    _, workbook = workbook_and_unpacked
    calc = replace(
        workbook.calcs[0],
        formula_raw="UNSUPPORTED_FUNCTION([Sales])",
    )
    translated = CalculationCompiler(workbook).compile(calc)
    assert translated.status == "unsupported"
    assert "UNSUPPORTED_FUNCTION" in translated.reason


def test_real_workbook_inventory_and_calculation_translation(
    workbook_and_unpacked,
) -> None:
    _, workbook = workbook_and_unpacked
    assert len(workbook.dashboards) == 2
    assert {
        dashboard.name: (dashboard.width, dashboard.height)
        for dashboard in workbook.dashboards
    } == {
        "Customer Dashboard": (1200, 800),
        "Sales Dashboard": (1200, 800),
    }
    assert len(workbook.calcs) == 33
    assert len(workbook.parameters) == 1
    assert workbook.parameters[0].caption == "Select Year"
    assert len(workbook.actions) == 4
    assert len(workbook.relationships) == 3
    tables = {table.caption: {column.name for column in table.columns} for table in workbook.tables}
    assert tables["Customers"] == {"Customer ID", "Customer Name"}
    assert tables["Location"] == {
        "Postal Code",
        "City",
        "State",
        "Region",
        "Country/Region",
    }
    assert tables["Products"] == {
        "Product ID",
        "Category",
        "Sub-Category",
        "Product Name",
    }
    assert "Customer Name" not in tables["Orders"]

    compiler = CalculationCompiler(workbook)
    by_caption = {calc.caption: calc for calc in workbook.calcs}
    translations = compiler.compile_all()
    cy_sales = translations[by_caption["CY Sales"].internal_name]
    assert cy_sales.status == "supported"
    assert "SELECTEDVALUE" in (cy_sales.dax or "")
    assert "SUMX" in (
        compiler._emit(
            parse(f"SUM([{by_caption['CY Sales'].internal_name}])"),
            row_context=False,
        )
    )

    py_customers = translations[by_caption["PY Customers"].internal_name]
    assert py_customers.status == "supported"
    assert py_customers.classification == "row"
    assert py_customers.is_calculated_column is False
    assert "SELECTEDVALUE" in (py_customers.dax or "")
    profit_difference = translations[by_caption["% Diff Profit"].internal_name]
    assert profit_difference.classification == "aggregate"
    assert "DIVIDE(" in (profit_difference.dax or "")
    assert (
        by_caption["% Diff Profit"].formula_resolved
        == "(SUM([CY Profit]) - SUM([PY Profit])) / SUM([CY Profit])"
    )
    assert "[Parameters].[Select Year]" in by_caption["CY Sales"].formula_resolved
    profit_dax = profit_difference.dax or ""
    assert profit_dax.count("= SELECTEDVALUE('Select Year'[Select Year], 2023)") == 2
    assert profit_dax.count("(SELECTEDVALUE('Select Year'[Select Year], 2023) - 1)") == 1

    sales_per_customer = translations[
        by_caption["CY Sales per Customer"].internal_name
    ]
    assert "SUMX" in (sales_per_customer.dax or "")
    assert "COUNTROWS(FILTER(DISTINCT(SELECTCOLUMNS(" in (
        sales_per_customer.dax or ""
    )
    assert "IF(" in (
        translations[by_caption["KPI CY Less PY"].internal_name].dax or ""
    )
    assert (
        translations[by_caption["Min/Max Sales"].internal_name].status
        == "table_calc"
    )
    assert (
        translations[by_caption["Nr of Orders per Customers"].internal_name].status
        == "needs_override"
    )

    table_lod = by_caption["{SUM([CY Sales])}"]
    assert table_lod.formula_resolved == "{SUM([CY Sales])}"
    lod_translation = translations[table_lod.internal_name]
    assert lod_translation.classification == "lod"
    assert "CALCULATE(" in (lod_translation.dax or "")
    assert "REMOVEFILTERS()" in (lod_translation.dax or "")
    assert lod_translation.semantics_approximated
    auto_measures, measures_map, _ = generate_auto_measures(workbook, translations)
    assert all(measure.name != table_lod.caption for measure in auto_measures)
    assert table_lod.caption in measures_map.values()


def test_hyper_extraction_deduplicates_dimension_rows(
    workbook_and_unpacked, tmp_path: Path
) -> None:
    unpacked, workbook = workbook_and_unpacked
    result = extract_tables(unpacked, workbook, tmp_path / "csv")
    assert result.row_counts == {
        "Orders": 9994,
        "Products": 1862,
        "Location": 630,
        "Customers": 793,
    }
    assert len(result.conflicts) == 2
    product_conflict = next(
        conflict for conflict in result.conflicts if conflict.table == "Products"
    )
    assert product_conflict.duplicate_keys == 32
    assert product_conflict.conflict_columns == {"Product Name": 32}
    for path in result.csv_paths.values():
        assert path.read_text(encoding="utf-8").splitlines()


def test_tmdl_and_pbir_smoke(workbook_and_unpacked, tmp_path: Path) -> None:
    _, workbook = workbook_and_unpacked
    compiler = CalculationCompiler(workbook)
    translations = compiler.compile_all()
    auto_measures, _, date_columns = generate_auto_measures(workbook, translations)
    data_dir = tmp_path / "data"
    model_dir = generate_tmdl(
        "Sales & Customer Dashboards",
        workbook,
        translations,
        auto_measures,
        date_columns,
        data_dir,
        tmp_path,
    )
    pbip_path, report_dir = generate_pbir(
        "Sales & Customer Dashboards", workbook.dashboards, tmp_path
    )
    assert (model_dir / "definition" / "expressions.tmdl").exists()
    assert "DataFolder" in (
        model_dir / "definition" / "expressions.tmdl"
    ).read_text(encoding="utf-8")
    assert (model_dir / "definition" / "relationships.tmdl").exists()
    orders = (
        model_dir / "definition" / "tables" / "Orders.tmdl"
    ).read_text(encoding="utf-8")
    assert "partition Orders = m" in orders
    assert "Csv.Document(File.Contents(DataFolder" in orders
    assert orders.index("sourceColumn:") < orders.index("partition Orders = m")
    assert (report_dir / "definition.pbir").exists()
    assert (report_dir / "definition" / "pages" / "pages.json").exists()
    assert pbip_path.exists()
    project = json.loads(pbip_path.read_text(encoding="utf-8"))
    assert project["artifacts"][0]["report"]["path"] == (
        "Sales & Customer Dashboards.Report"
    )
    report_definition = json.loads(
        (report_dir / "definition" / "report.json").read_text(encoding="utf-8")
    )
    assert "customTheme" not in report_definition["themeCollection"]
