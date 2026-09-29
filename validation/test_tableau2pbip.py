from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from tableau2pbip import visuals as visual_builders
from tableau2pbip.calc.ast import Binary, Call, Field, Literal
from tableau2pbip.calc.dax import (
    AutoMeasure,
    CalculationCompiler,
    generate_auto_measures,
)
from tableau2pbip.calc.parser import parse
from tableau2pbip.extract import extract_tables
from tableau2pbip.ir import (
    Calc,
    Dashboard,
    FieldRef,
    Table,
    TableColumn,
    Workbook,
    Worksheet,
    Zone,
)
from tableau2pbip.layout import (
    _merge_slicer_selection,
    load_layout,
    visual_folder_name,
)
from tableau2pbip.migrate import (
    _load_overrides,
    _model_field_types,
    _report_markdown,
    _resolve_layout_path,
    _resolve_overrides_path,
    _translation_records,
    convert_workbook,
)
from tableau2pbip.overrides import load_model_overrides
from tableau2pbip.parse import decode_field_ref, parse_workbook
from tableau2pbip.pbir import generate_pbir
from tableau2pbip.schema_validation import validate_json_documents
from tableau2pbip.scaffold import (
    _report_markdown as _scaffold_report_markdown,
    _zone_background,
    scaffold_workbook,
)
from tableau2pbip.tmdl import generate_tmdl
from tableau2pbip.unpack import unpack
from tableau2pbip.visuals.trends import step_trends


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_PATH = (
    ROOT
    / "projects"
    / "sales-dashboard-project"
    / "Sales & Customer Dashboards.twbx"
)
HR_WORKBOOK_PATH = ROOT / "projects" / "hr-dashboard-project" / "HR Dashboard.twbx"
LAYOUT_FIXTURE_PATH = ROOT / "validation" / "tableau2pbip_layout_fixture.yml"
LAYOUT_FIXTURE_IMAGE = ROOT / "validation" / "tableau2pbip_fixture.svg"
LAYOUT_MODEL_FIELDS = {
    "Orders.Order Date (Month)": "int64",
    "Orders.CY Sales": "double",
    "Select Year.Select Year": "int64",
}


def _all_zones(zones: list[Zone]):
    for zone in zones:
        yield zone
        yield from _all_zones(zone.children)


@pytest.fixture
def workbook_and_unpacked(tmp_path: Path):
    unpacked = unpack(WORKBOOK_PATH, tmp_path / "unpacked")
    return unpacked, parse_workbook(unpacked.twb_path)


def _synthetic_measure_workbook(
    column_names: list[str],
    raw_refs: list[str],
    calcs: list[Calc] | None = None,
    column_types: dict[str, str] | None = None,
) -> Workbook:
    return Workbook(
        "Synthetic",
        [
            Table(
                "Employees",
                "Extract.Extract",
                [
                    TableColumn(name, (column_types or {}).get(name, "real"))
                    for name in column_names
                ],
            )
        ],
        [],
        calcs or [],
        [],
        [Worksheet("Synthetic", " ".join(raw_refs), "", [], [], [])],
        [],
        [],
        fact_table="Employees",
    )


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


def test_if_without_else_emits_blank_result(workbook_and_unpacked) -> None:
    _, workbook = workbook_and_unpacked
    dax = CalculationCompiler(workbook)._emit(
        parse("IF [Sales] > 0 THEN 'positive' END"), row_context=False
    )
    assert dax == 'IF((\'Orders\'[Sales] > 0), "positive")'


def test_week_start_defaults_to_sunday(tmp_path: Path) -> None:
    workbook_path = tmp_path / "no-week-start.twb"
    workbook_path.write_text("<workbook/>", encoding="utf-8")

    assert parse_workbook(workbook_path).start_of_week == "sunday"


@pytest.mark.parametrize(
    ("start_of_week", "return_type"),
    [("sunday", 1), ("monday", 2)],
)
def test_week_start_controls_weeknum_emission(
    workbook_and_unpacked,
    start_of_week: str,
    return_type: int,
) -> None:
    _, workbook = workbook_and_unpacked
    compiler = CalculationCompiler(
        replace(workbook, start_of_week=start_of_week)
    )

    datepart = compiler._emit(
        parse("DATEPART('week', #2023-01-01#)"), row_context=False
    )
    assert datepart == f"WEEKNUM(DATE(2023, 1, 1), {return_type})"

    week_reference = FieldRef(
        "federated.test", "wk", "Order Date", "Order Date", "date"
    )
    date_part_column = compiler.emit_aggregation(week_reference, "wk:Order Date")
    assert date_part_column is not None
    assert date_part_column.dax == (
        f"WEEKNUM('Orders'[Order Date], {return_type})"
    )


@pytest.mark.parametrize(
    ("part", "interval"),
    [
        ("year", "YEAR"),
        ("quarter", "QUARTER"),
        ("month", "MONTH"),
        ("week", "WEEK"),
        ("day", "DAY"),
        ("hour", "HOUR"),
        ("minute", "MINUTE"),
        ("second", "SECOND"),
    ],
)
def test_datediff_emits_dax_intervals(
    workbook_and_unpacked, part: str, interval: str
) -> None:
    _, workbook = workbook_and_unpacked
    dax = CalculationCompiler(workbook)._emit(
        parse(f"DATEDIFF('{part}', [Order Date], NOW(), 'monday')"),
        row_context=False,
    )
    assert dax == f"DATEDIFF('Orders'[Order Date], NOW(), {interval})"


def test_hr_calculations_translate_datediff_dependencies_and_total(
    tmp_path: Path,
) -> None:
    unpacked = unpack(HR_WORKBOOK_PATH, tmp_path / "hr-calculations")
    workbook = parse_workbook(unpacked.twb_path)
    compiler = CalculationCompiler(workbook)
    translated = compiler.compile_all()
    by_caption = {
        calc.caption: translated[calc.internal_name] for calc in workbook.calcs
    }

    for caption in ("Age", "Length of Hire", "Age Groups"):
        assert by_caption[caption].status == "supported"
    assert by_caption["Age"].is_calculated_column
    assert by_caption["Length of Hire"].is_calculated_column
    assert "DATEDIFF(" in (by_caption["Age"].dax or "")
    assert "DATEDIFF(" in (by_caption["Length of Hire"].dax or "")
    assert "'HumanResources'[Age]" in (by_caption["Age Groups"].dax or "")

    for caption in ("% Total Hired", "% Total Terminated"):
        translation = by_caption[caption]
        assert translation.classification == "table_calc"
        assert translation.status == "supported"
        assert translation.semantics_approximated
        assert not translation.is_calculated_column
        assert "CALCULATE(" in (translation.dax or "")
        assert "ALLSELECTED()" in (translation.dax or "")

    assert CalculationCompiler(workbook)._emit(
        parse("TODAY()"), row_context=False
    ) == "TODAY()"
    assert CalculationCompiler(workbook)._emit(
        parse("NOW()"), row_context=False
    ) == "NOW()"


def test_unsupported_calculation_dependencies_propagate(
    tmp_path: Path,
) -> None:
    unpacked = unpack(HR_WORKBOOK_PATH, tmp_path / "hr-dependencies")
    workbook = parse_workbook(unpacked.twb_path)
    synthetic_calculations = [
        Calc(
            "SyntheticUnsupported",
            "Synthetic Unsupported",
            "MISSING_FUNCTION([Salary])",
            "",
            "string",
            "dimension",
            "string",
        ),
        Calc(
            "SyntheticDependent",
            "Synthetic Dependent",
            "[SyntheticUnsupported]",
            "",
            "string",
            "dimension",
            "string",
        ),
        Calc(
            "SyntheticTableCalc",
            "Synthetic Table Calc",
            "RANK(SUM([Salary]))",
            "",
            "integer",
            "dimension",
            "integer",
        ),
        Calc(
            "SyntheticTableCalcDependent",
            "Synthetic Table Calc Dependent",
            "[SyntheticTableCalc]",
            "",
            "integer",
            "dimension",
            "integer",
        ),
    ]
    compiler = CalculationCompiler(
        replace(workbook, calcs=workbook.calcs + synthetic_calculations)
    )

    dependent = compiler.compile(synthetic_calculations[1])
    assert dependent.classification == "row"
    assert dependent.status == "unsupported"
    assert dependent.reason == "depends on Synthetic Unsupported"

    table_calculation = compiler.compile(synthetic_calculations[2])
    assert table_calculation.classification == "table_calc"
    assert table_calculation.status == "table_calc"
    table_dependent = compiler.compile(synthetic_calculations[3])
    assert table_dependent.classification == "table_calc"
    assert table_dependent.status == "unsupported"
    assert table_dependent.reason == "depends on Synthetic Table Calc"


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
    assert workbook.start_of_week == "monday"
    assert {
        dashboard.name: (dashboard.width, dashboard.height)
        for dashboard in workbook.dashboards
    } == {
        "Customer Dashboard": (1200, 800),
        "Sales Dashboard": (1200, 800),
    }
    assert [dashboard.name for dashboard in workbook.dashboards] == [
        "Sales Dashboard",
        "Customer Dashboard",
    ]
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
    assert (translations[by_caption["KPI CY Less PY"].internal_name].dax or "").endswith(
        '"⬤", "")'
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


def test_auto_measures_avoid_column_name_collisions_and_dedupe_refs() -> None:
    row_calc = Calc(
        "LengthCalc",
        "Length of Hire",
        "[Salary] + 1",
        "[Salary] + 1",
        "real",
        "measure",
        "quantitative",
    )
    date_ref = "[Employees].[yr:Hiredate:ok]"
    refs = [
        "[Employees].[sum:Salary:qk]",
        date_ref,
        "[Employees].[sum:Salary:ok]",
        "[Employees].[sum:LengthCalc:qk]",
        "[Employees].[sum:LengthCalc:ok]",
    ]
    workbook = _synthetic_measure_workbook(
        ["Salary", "Hiredate"], refs, [row_calc], {"Hiredate": "date"}
    )
    translations = CalculationCompiler(workbook).compile_all()

    auto_measures, measures_map, _ = generate_auto_measures(workbook, translations)

    names = {measure.name for measure in auto_measures}
    assert names == {"SUM Salary", "SUM Length of Hire"}
    assert measures_map[refs[0]] == measures_map[refs[2]] == "SUM Salary"
    assert measures_map[refs[3]] == measures_map[refs[4]] == "SUM Length of Hire"
    assert measures_map[date_ref] == "Hiredate (Year)"
    assert list(measures_map) == refs


@pytest.mark.parametrize(
    ("column_names", "expected_name"),
    [
        (["Value", "SUM Value"], "SUM Value (agg)"),
        (
            ["Value", "SUM Value", "SUM Value (agg)"],
            "SUM Value (agg 2)",
        ),
    ],
)
def test_auto_measure_name_collision_suffixes(
    column_names: list[str], expected_name: str
) -> None:
    raw_ref = "[Employees].[sum:Value:qk]"
    workbook = _synthetic_measure_workbook(column_names, [raw_ref])

    auto_measures, measures_map, _ = generate_auto_measures(workbook, {})

    assert [measure.name for measure in auto_measures] == [expected_name]
    assert measures_map[raw_ref] == expected_name


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
    assert result.column_types["Orders"]["Postal Code"] == "BIG_INT"
    assert result.column_types["Orders"]["Order Date"] == "DATE"
    assert result.column_types["Orders"]["Sales"] == "DOUBLE"
    assert result.column_types["Location"]["Postal Code"] == "BIG_INT"
    assert len(result.conflicts) == 2
    product_conflict = next(
        conflict for conflict in result.conflicts if conflict.table == "Products"
    )
    assert product_conflict.duplicate_keys == 32
    assert product_conflict.conflict_columns == {"Product Name": 32}
    for path in result.csv_paths.values():
        assert path.read_text(encoding="utf-8").splitlines()


def test_tmdl_and_pbir_smoke(workbook_and_unpacked, tmp_path: Path) -> None:
    unpacked, workbook = workbook_and_unpacked
    compiler = CalculationCompiler(workbook)
    translations = compiler.compile_all()
    overrides_dir = ROOT / "migrations" / "sales-customer-dashboards" / "overrides"
    measure_overrides = _load_overrides(overrides_dir)
    model_overrides = load_model_overrides(overrides_dir)
    auto_measures, _, date_columns = generate_auto_measures(
        workbook, translations, model_overrides, measure_overrides
    )
    data_dir = tmp_path / "data"
    extraction = extract_tables(unpacked, workbook, data_dir)
    model_fields = _model_field_types(
        workbook,
        translations,
        auto_measures,
        date_columns,
        measure_overrides,
        model_overrides,
        extraction.column_types,
    )
    assert model_fields["Orders.Order Date (Month)"] == "int64"
    assert "Orders.CY Sales" in model_fields
    assert model_fields["Select Year.Select Year"] == "int64"
    model_dir = generate_tmdl(
        "Sales & Customer Dashboards",
        workbook,
        translations,
        auto_measures,
        date_columns,
        data_dir,
        tmp_path,
        overrides=measure_overrides,
        column_types=extraction.column_types,
        model_overrides=model_overrides,
    )
    pbip_path, report_dir, visual_inventory = generate_pbir(
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
    assert "\tdataType: int64" in orders
    assert "\tdataType: double" in orders
    assert "\tdataType: dateTime" in orders
    assert "M/d/yyyy" in orders
    assert "column 'Postal Code'\n\t\tdataType: int64" in orders
    assert re.search(
        r"column 'Order Date \(Year\)' = [^\n]+\n"
        r"\t\tdataType: int64\n"
        r"\t\tformatString: 0\n"
        r"\t\tlineageTag: [^\n]+\n"
        r"\t\tsummarizeBy: none",
        orders,
    )
    assert (
        "measure 'MAX Order Date' = MAX('Orders'[Order Date])\n"
        "\t\tformatString: M/d/yyyy" in orders
    )
    assert "measure 'KPI CY Less PY' = IF(" in orders
    assert orders.count("column 'Order Date (Month)'") == 1
    assert "column 'Order Date (Month)' = MONTH('Orders'[Order Date])" in orders
    assert "measure 'KPI Total CY Sales'" in orders
    override_measure = orders.index("measure 'KPI Total CY Sales'")
    override_measure_end = orders.find("\n\tmeasure ", override_measure + 1)
    assert "displayFolder: Overrides" in orders[
        override_measure:override_measure_end
    ]
    kpi_start = orders.index("measure 'KPI CY Less PY'")
    kpi_end = orders.find("\n\tmeasure ", kpi_start + 1)
    assert "formatString:" not in orders[kpi_start:kpi_end]
    for path in (model_dir / "definition").rglob("*.tmdl"):
        for line in path.read_text(encoding="utf-8").splitlines():
            assert "\t" not in line.lstrip("\t"), f"inline tab in {path}: {line}"
            if line.startswith("\tcolumn ") or line.startswith("\tmeasure "):
                assert not line.startswith("\t\t")
    parameter_model = (
        model_dir / "definition" / "tables" / "Select Year.tmdl"
    ).read_text(encoding="utf-8")
    assert "PBI_IsParameterQuery" not in parameter_model
    assert "PBI_ParameterDefaultValue" not in parameter_model
    assert (
        "\t\tsummarizeBy: none\n"
        "\t\tisNameInferred\n"
        "\t\tsourceColumn: [Select Year]"
    ) in parameter_model
    calculated_table = (
        model_dir
        / "definition"
        / "tables"
        / "Customer Orders by Year.tmdl"
    ).read_text(encoding="utf-8")
    assert "partition 'Customer Orders by Year' = calculated" in calculated_table
    assert "\t\tsource =\n\t\t\tGENERATE(" in calculated_table
    assert all(
        not line.startswith(" ") for line in calculated_table.splitlines()
    )
    assert "CROSSJOIN(" in calculated_table
    for column in model_overrides.calculated_tables[0].columns:
        assert (
            f"\t\tisNameInferred\n\t\tsourceColumn: [{column.name}]\n"
            in calculated_table
        )
    assert "\t\tsourceColumn: Order Date\n" in orders
    assert "\t\tsourceColumn: [Order Date]\n" not in orders
    relationships = (
        model_dir / "definition" / "relationships.tmdl"
    ).read_text(encoding="utf-8")
    assert "crossFilteringBehavior: bothDirections" in relationships
    report_markdown = _report_markdown(
        "Sales & Customer Dashboards",
        workbook,
        extraction,
        _translation_records(workbook, translations),
        auto_measures,
        measure_overrides,
        model_overrides,
        visual_inventory,
    )
    assert "## Lead overrides" in report_markdown
    assert "Calculated column **Orders.Order Date (Month)**" in report_markdown
    assert "Calculated table **Customer Orders by Year**" in report_markdown
    assert "bothDirections" in report_markdown
    assert "## Visuals" in report_markdown
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
    assert "publicCustomVisuals" not in report_definition
    powershell = shutil.which("powershell")
    if powershell is None:
        pytest.skip("Windows PowerShell is not available for TOM TMDL validation")
    validation = subprocess.run(
        [
            powershell,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "tableau2pbip" / "validate_tmdl.ps1"),
            "-ModelPath",
            str(model_dir),
        ],
        check=False,
        capture_output=True,
        encoding="utf-8",
        timeout=300,
    )
    assert validation.returncode == 0, validation.stdout + validation.stderr
    assert "TOM validation PASS" in validation.stdout


def test_tmdl_measure_name_guard_and_override_replacement(tmp_path: Path) -> None:
    workbook = _synthetic_measure_workbook(["Salary"], [], [])
    raw_ref = "[Employees].[sum:Salary:qk]"
    auto_measure = AutoMeasure("salary", "SUM('Employees'[Salary])", raw_ref)

    with pytest.raises(ValueError, match="(?i)salary"):
        generate_tmdl(
            "Synthetic",
            workbook,
            {},
            [auto_measure],
            [],
            tmp_path / "data",
            tmp_path / "column-collision",
        )

    with pytest.raises(ValueError, match="duplicate measures") as duplicate_error:
        generate_tmdl(
            "Synthetic",
            workbook,
            {},
            [
                AutoMeasure("Revenue", "SUM('Employees'[Salary])", raw_ref),
                AutoMeasure("revenue", "MAX('Employees'[Salary])", raw_ref),
            ],
            [],
            tmp_path / "data",
            tmp_path / "duplicate-measures",
        )
    assert "Revenue" in str(duplicate_error.value)
    assert "revenue" in str(duplicate_error.value)

    model_dir = generate_tmdl(
        "Synthetic",
        workbook,
        {},
        [AutoMeasure("Revenue", "SUM('Employees'[Salary])", raw_ref)],
        [],
        tmp_path / "data",
        tmp_path / "override-replacement",
        overrides={"revenue": ("MAX('Employees'[Salary])", "")},
    )
    table_text = (
        model_dir / "definition" / "tables" / "Employees.tmdl"
    ).read_text(encoding="utf-8")
    assert table_text.count("measure Revenue =") == 1
    assert "displayFolder: Overrides" in table_text


def test_layout_emits_visuals_and_validates_json_schemas(
    workbook_and_unpacked, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, workbook = workbook_and_unpacked
    builder_calls: list[tuple[str, dict[str, object], float, float]] = []

    def build_spec(
        component: str,
        params: dict[str, object],
        width: float,
        height: float,
    ) -> dict[str, object]:
        builder_calls.append((component, params, width, height))
        return {
            "component": component,
            "params": params,
            "width": width,
            "height": height,
        }

    monkeypatch.setattr(visual_builders, "build_spec", build_spec)
    pbip_path, report_dir, visuals = generate_pbir(
        "Sales & Customer Dashboards",
        workbook.dashboards,
        tmp_path,
        LAYOUT_FIXTURE_PATH,
        LAYOUT_MODEL_FIELDS,
    )
    assert pbip_path.exists()
    assert len(visuals) == 6
    assert builder_calls == [("fixture", {}, 380.0, 274.0)]
    assert next(item for item in visuals if item["id"] == "panel")["position"][
        "z"
    ] == 400
    assert len(visual_folder_name("a" * 60)) <= 50
    assert re.fullmatch(r"[A-Za-z0-9_]+", visual_folder_name("a" * 60))

    pages_dir = report_dir / "definition" / "pages"
    pages_index = json.loads((pages_dir / "pages.json").read_text(encoding="utf-8"))
    assert pages_index["pageOrder"][0] == "ReportSectionSalesDashboard"
    assert pages_index["activePageName"] == "ReportSectionSalesDashboard"
    page = json.loads(
        (
            pages_dir
            / "ReportSectionSalesDashboard"
            / "page.json"
        ).read_text(encoding="utf-8")
    )
    assert page["displayOption"] == "ActualSize"
    assert (
        page["objects"]["background"][0]["properties"]["color"]["solid"]["color"][
            "expr"
        ]["Literal"]["Value"]
        == "'#F5F5F5'"
    )
    assert page["objects"]["outspace"][0]["properties"]["transparency"]["expr"][
        "Literal"
    ]["Value"] == "0D"

    sales_page = pages_dir / "ReportSectionSalesDashboard" / "visuals"
    deneb = json.loads(
        (sales_page / "deneb_sales" / "visual.json").read_text(encoding="utf-8")
    )
    assert deneb["visual"]["visualType"] == (
        "deneb7E15AEF80B9E4D4F8E12924291ECE89A"
    )
    projections = deneb["visual"]["query"]["queryState"]["dataset"]["projections"]
    assert [
        (item["queryRef"], item["nativeQueryRef"], item["displayName"])
        for item in projections
    ] == [
        ("Orders.Order Date (Month)", "Month", "Month"),
        ("Orders.CY Sales", "CY", "CY"),
    ]
    deneb_properties = deneb["visual"]["objects"]["vega"][0]["properties"]
    assert deneb_properties["provider"]["expr"]["Literal"]["Value"] == "'vega'"
    assert deneb_properties["renderMode"]["expr"]["Literal"]["Value"] == "'svg'"
    assert deneb_properties["version"]["expr"]["Literal"]["Value"] == "'6.4.3'"
    assert deneb_properties["selectionMode"]["expr"]["Literal"]["Value"] == "'simple'"
    assert deneb_properties["enableSelection"]["expr"]["Literal"]["Value"] == "true"
    assert deneb_properties["enableTooltips"]["expr"]["Literal"]["Value"] == "true"
    assert deneb_properties["enableHighlight"]["expr"]["Literal"]["Value"] == "false"
    assert deneb_properties["enableContextMenu"]["expr"]["Literal"]["Value"] == "true"
    assert deneb_properties["jsonConfig"]["expr"]["Literal"]["Value"] == "'{}'"
    encoded_spec = deneb_properties["jsonSpec"]["expr"]["Literal"]["Value"]
    decoded_spec = json.loads(encoded_spec[1:-1].replace("''", "'"))
    assert decoded_spec["width"] == 380.0
    assert decoded_spec["height"] == 274.0
    state_management = deneb["visual"]["objects"]["stateManagement"][0][
        "properties"
    ]
    assert state_management["viewportWidth"]["expr"]["Literal"]["Value"] == "380D"
    assert state_management["viewportHeight"]["expr"]["Literal"]["Value"] == "274D"
    assert deneb["visual"]["drillFilterOtherVisuals"] is False
    assert all(
        deneb["visual"]["visualContainerObjects"][name][0]["properties"]["show"][
            "expr"
        ]["Literal"]["Value"]
        == "false"
        for name in ("title", "background", "border", "dropShadow", "visualHeader")
    )
    report_definition = json.loads(
        (report_dir / "definition" / "report.json").read_text(encoding="utf-8")
    )
    assert report_definition["publicCustomVisuals"] == [
        "deneb7E15AEF80B9E4D4F8E12924291ECE89A"
    ]

    slicer = json.loads(
        (sales_page / "year_filter" / "visual.json").read_text(encoding="utf-8")
    )
    assert slicer["visual"]["syncGroup"] == {
        "groupName": "year",
        "fieldChanges": True,
        "filterChanges": True,
    }
    assert "filterConfig" not in slicer
    selection_filter = slicer["visual"]["objects"]["general"][0]["properties"][
        "filter"
    ]["filter"]
    assert "In" in selection_filter["Where"][0]["Condition"]
    assert (
        selection_filter["Where"][0]["Condition"]["In"]["Values"][0][0][
            "Literal"
        ]["Value"]
        == "2023L"
    )
    image = json.loads(
        (sales_page / "nav_customer" / "visual.json").read_text(encoding="utf-8")
    )
    image_link = image["visual"]["visualContainerObjects"]["visualLink"][0][
        "properties"
    ]
    assert image_link["type"]["expr"]["Literal"]["Value"] == "'PageNavigation'"
    assert (
        image_link["navigationSection"]["expr"]["Literal"]["Value"]
        == "'ReportSectionCustomerDashboard'"
    )
    bookmark_link = json.loads(
        (sales_page / "filters_toggle" / "visual.json").read_text(encoding="utf-8")
    )["visual"]["visualContainerObjects"]["visualLink"][0]["properties"]
    assert bookmark_link["bookmark"]["expr"]["Literal"]["Value"] == (
        "'sales_filters_shown'"
    )
    shape = json.loads(
        (sales_page / "panel" / "visual.json").read_text(encoding="utf-8")
    )
    assert (
        shape["visual"]["objects"]["fill"][0]["properties"]["fillColor"]["solid"][
            "color"
        ]["expr"]["Literal"]["Value"]
        == "'#072A35'"
    )
    assert shape["isHidden"] is True
    textbox = json.loads(
        (sales_page / "filters_heading" / "visual.json").read_text(encoding="utf-8")
    )
    assert (
        textbox["visual"]["objects"]["general"][0]["properties"]["paragraphs"][0][
            "textRuns"
        ][0]["value"]
        == "FILTERS"
    )
    bookmarks_dir = report_dir / "definition" / "bookmarks"
    bookmark = json.loads(
        (bookmarks_dir / "sales_filters_shown.bookmark.json").read_text(
            encoding="utf-8"
        )
    )
    assert bookmark["explorationState"]["activeSection"] == (
        "ReportSectionSalesDashboard"
    )
    shown_visuals = bookmark["explorationState"]["sections"][
        "ReportSectionSalesDashboard"
    ]["visualContainers"]
    assert set(shown_visuals) == {
        "deneb_sales",
        "year_filter",
        "nav_customer",
        "filters_toggle",
        "panel",
        "filters_heading",
    }
    assert shown_visuals["panel"] == {"singleVisual": {"visualType": "shape"}}
    assert shown_visuals["deneb_sales"]["singleVisual"]["visualType"] == (
        "deneb7E15AEF80B9E4D4F8E12924291ECE89A"
    )
    assert bookmark["options"] == {
        "applyOnlyToTargetVisuals": True,
        "targetVisualNames": [
            "deneb_sales",
            "year_filter",
            "nav_customer",
            "filters_toggle",
            "panel",
            "filters_heading",
        ],
        "suppressData": True,
        "suppressActiveSection": False,
        "suppressDisplay": False,
    }
    hidden_bookmark = json.loads(
        (bookmarks_dir / "sales_filters_hidden.bookmark.json").read_text(
            encoding="utf-8"
        )
    )
    assert hidden_bookmark["displayName"] == "sales_filters_hidden"
    hidden_visuals = hidden_bookmark["explorationState"]["sections"][
        "ReportSectionSalesDashboard"
    ]["visualContainers"]
    assert hidden_visuals["panel"] == {
        "singleVisual": {
            "visualType": "shape",
            "display": {"mode": "hidden"},
        }
    }
    assert hidden_visuals["year_filter"] == {"singleVisual": {"visualType": "slicer"}}
    assert bookmark["options"]["suppressData"] is True
    resources = [
        package
        for package in report_definition["resourcePackages"]
        if package["type"] == "RegisteredResources"
    ]
    assert resources[0]["items"][0]["type"] == "Image"
    assert (
        report_dir
        / "StaticResources"
        / "RegisteredResources"
        / LAYOUT_FIXTURE_IMAGE.name
    ).is_file()
    assert len(validate_json_documents(tmp_path)) >= 14


@pytest.mark.parametrize(
    ("old_text", "new_text", "message"),
    [
        ("Orders.CY Sales", "Orders.Missing Field", "Unknown model field"),
        (
            "target: sales_filters_shown",
            "target: missing_bookmark",
            "unknown bookmark",
        ),
        (
            "target: Customer Dashboard",
            "target: Missing Dashboard",
            "unknown Tableau dashboard",
        ),
        (
            "    display_name: Filters shown",
            "    display_name: Filters shown\n    targets:\n      - missing_visual",
            "targets unknown visual ids",
        ),
        (
            "    targets:\n      - panel\n      - year_filter\n    hidden:\n      - panel",
            "    targets:\n      - year_filter\n    hidden:\n      - panel",
            "hidden visual ids must be included in targets",
        ),
        ("      - panel", "      - missing_visual", "unknown visual ids"),
        (
            '  page_background: "#F5F5F5"',
            '  page_background: "#F5F5F5"\n  unknown: true',
            "Unknown keys",
        ),
    ],
)
def test_layout_rejects_unknown_targets(
    workbook_and_unpacked,
    tmp_path: Path,
    old_text: str,
    new_text: str,
    message: str,
) -> None:
    _, workbook = workbook_and_unpacked
    layout_text = LAYOUT_FIXTURE_PATH.read_text(encoding="utf-8")
    assert old_text in layout_text
    invalid_layout = tmp_path / "invalid_layout.yml"
    invalid_layout.write_text(layout_text.replace(old_text, new_text, 1), encoding="utf-8")
    (tmp_path / LAYOUT_FIXTURE_IMAGE.name).write_bytes(
        LAYOUT_FIXTURE_IMAGE.read_bytes()
    )
    with pytest.raises(ValueError, match=message):
        generate_pbir(
            "Sales & Customer Dashboards",
            workbook.dashboards,
            tmp_path / "output",
            invalid_layout,
            LAYOUT_MODEL_FIELDS,
        )


def test_convert_layout_default_is_next_to_overrides(tmp_path: Path) -> None:
    migration_dir = tmp_path / "migration"
    overrides_dir = migration_dir / "overrides"
    output_dir = migration_dir / "output"
    overrides_dir.mkdir(parents=True)
    output_dir.mkdir()
    layout_path = migration_dir / "layout.yml"
    layout_path.write_text("pages: []\n", encoding="utf-8")
    assert _resolve_overrides_path(None, output_dir) == overrides_dir
    assert _resolve_layout_path(None, overrides_dir, output_dir) == layout_path
    assert _resolve_layout_path(None, None, output_dir) == layout_path
    explicit = tmp_path / "explicit.yml"
    assert _resolve_layout_path(explicit, overrides_dir, output_dir) == explicit
    assert _resolve_overrides_path(explicit, output_dir) == explicit

    no_overrides_dir = tmp_path / "no-overrides"
    no_overrides_output = no_overrides_dir / "output"
    no_overrides_output.mkdir(parents=True)
    assert _resolve_overrides_path(None, no_overrides_output) is None
    no_overrides_layout = no_overrides_dir / "layout.yml"
    no_overrides_layout.write_text("pages: []\n", encoding="utf-8")
    assert _resolve_layout_path(None, None, no_overrides_output) == no_overrides_layout


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("unknown: true\n", "Unknown keys"),
        (
            "relationships:\n"
            "  - from: Orders.Customer ID\n"
            "    to: Customers.Customer ID\n"
            "    crossFilteringBehavior: []\n",
            "crossFilteringBehavior",
        ),
    ],
)
def test_invalid_model_overrides_raise_clear_errors(
    tmp_path: Path, content: str, message: str
) -> None:
    (tmp_path / "model.yml").write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match=message):
        load_model_overrides(tmp_path)


def test_sales_datasource_tables_and_fact_table_are_stable(
    tmp_path: Path,
) -> None:
    unpacked = unpack(WORKBOOK_PATH, tmp_path / "sales-unpacked")
    workbook = parse_workbook(unpacked.twb_path)
    tables = {table.caption: [column.name for column in table.columns] for table in workbook.tables}

    assert set(tables) == {"Customers", "Location", "Orders", "Products"}
    assert {name: len(columns) for name, columns in tables.items()} == {
        "Customers": 2,
        "Location": 5,
        "Orders": 13,
        "Products": 4,
    }
    assert workbook.fact_table == "Orders"


def test_hr_datasource_columns_types_and_fact_table(
    tmp_path: Path,
) -> None:
    unpacked = unpack(HR_WORKBOOK_PATH, tmp_path / "hr-unpacked")
    workbook = parse_workbook(unpacked.twb_path)

    assert [table.caption for table in workbook.tables] == ["HumanResources"]
    assert workbook.fact_table == "HumanResources"
    table = workbook.tables[0]
    assert {
        column.name: column.datatype for column in table.columns
    } == {
        "Employee_ID": "string",
        "First Name": "string",
        "Last Name": "string",
        "Gender": "string",
        "State": "string",
        "City": "string",
        "Education Level": "string",
        "Birthdate": "date",
        "Hiredate": "date",
        "Termdate": "date",
        "Department": "string",
        "Job Title": "string",
        "Salary": "integer",
        "Performance Rating": "string",
    }


def test_hr_button_parsing_resolves_windows_and_inherits_hidden_state(
    tmp_path: Path,
) -> None:
    unpacked = unpack(HR_WORKBOOK_PATH, tmp_path / "hr-buttons")
    workbook = parse_workbook(unpacked.twb_path)
    zones = {
        zone.id: zone
        for dashboard in workbook.dashboards
        for zone in _all_zones(dashboard.zones)
    }
    buttons = {
        zone_id: zone.button
        for zone_id, zone in zones.items()
        if zone.button is not None
    }

    assert workbook.window_ids == {
        "{D32130D7-33C4-4F9C-88E2-F0FD1B9DCF64}": "HR | Summary",
        "{D681C40F-6D5B-488A-BA76-7F8043BBBF0F}": "HR | Details",
    }
    assert buttons["136"].kind == "goto"
    assert buttons["136"].target_window_id in workbook.window_ids
    assert (
        workbook.window_ids[buttons["136"].target_window_id] == "HR | Details"
    )
    assert buttons["141"].kind == "toggle"
    assert buttons["141"].toggle_zone_ids == ["137"]
    assert buttons["141"].images == [
        "Image/info-shown.png",
        "Image/info-hidden.png",
    ]
    assert buttons["141"].active_state == 1
    assert buttons["127"].kind == "toggle"
    assert buttons["127"].toggle_zone_ids == ["122"]
    assert buttons["127"].images == [
        "Image/filter-active.png",
        "Image/filter-inactive.png",
    ]
    export_buttons = [
        button for button in buttons.values() if button.kind == "export"
    ]
    assert {button.export_type for button in export_buttons} == {"pdf", "image"}
    assert zones["137"].hidden_by_user
    assert zones["138"].hidden_by_user


def test_hr_conversion_smoke_emits_human_resources_model(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "hr-migration" / "output"
    result = convert_workbook(HR_WORKBOOK_PATH, output_dir)
    assert Path(str(result["pbip_path"])).is_file()
    model_files = list(output_dir.rglob("*.tmdl"))
    assert model_files
    model = "\n".join(path.read_text(encoding="utf-8") for path in model_files)
    assert "table HumanResources" in model or "table 'HumanResources'" in model
    for measure in ("% Total Hired", "% Total Terminated"):
        assert re.search(rf"measure '{re.escape(measure)}'\s*=", model)
    assert model.count("ALLSELECTED()") >= 2
    column_names = {
        (quoted or bare).replace("''", "'").casefold()
        for quoted, bare in re.findall(
            r"^\tcolumn (?:'((?:[^']|'')+)'|([^\s=]+))",
            model,
            re.MULTILINE,
        )
    }
    measure_names = {
        (quoted or bare).replace("''", "'").casefold()
        for quoted, bare in re.findall(
            r"^\tmeasure (?:'((?:[^']|'')+)'|([^\s=]+))\s*=",
            model,
            re.MULTILINE,
        )
    }
    assert not (column_names & measure_names)
    assert {
        "sum length of hire",
        "sum age",
        "sum salary",
    } <= measure_names


def test_inspect_cli_prints_one_inventory() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "tableau2pbip",
            "inspect",
            str(HR_WORKBOOK_PATH),
        ],
        check=True,
        capture_output=True,
        encoding="utf-8",
        cwd=ROOT,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    inventory = json.loads(completed.stdout)
    assert inventory["fact_table"] == "HumanResources"
    assert completed.stdout.count('"fact_table"') == 1


def test_slicer_selection_merges_existing_general_properties() -> None:
    general_properties = {"altText": {"expr": {"Literal": {"Value": "'Year'"}}}}
    visual_objects: dict[str, object] = {
        "general": [{"properties": general_properties}]
    }
    selection_filter = {"Version": 2, "From": [], "Where": []}

    _merge_slicer_selection(visual_objects, selection_filter)

    assert visual_objects["general"] == [
        {
            "properties": {
                "altText": {"expr": {"Literal": {"Value": "'Year'"}}},
                "filter": {"filter": selection_filter},
            }
        }
    ]


def test_sales_slicer_defaults_use_selection_state() -> None:
    with tempfile.TemporaryDirectory(prefix="pbi-") as temporary_directory:
        output_dir = Path(temporary_directory) / "output"
        result = convert_workbook(
            WORKBOOK_PATH,
            output_dir,
            overrides_dir=ROOT
            / "migrations"
            / "sales-customer-dashboards"
            / "overrides",
            layout_path=ROOT
            / "migrations"
            / "sales-customer-dashboards"
            / "layout.yml",
        )
        report_dir = Path(str(result["report_dir"]))
        for page, visual_id in (
            ("ReportSectionSalesDashboard", "s_fp_year"),
            ("ReportSectionCustomerDashboard", "c_fp_year"),
        ):
            visual_path = (
                report_dir
                / "definition"
                / "pages"
                / page
                / "visuals"
                / visual_id
                / "visual.json"
            )
            visual_document = json.loads(visual_path.read_text(encoding="utf-8"))
            assert "filterConfig" not in visual_document
            selection_filter = visual_document["visual"]["objects"]["general"][0][
                "properties"
            ]["filter"]["filter"]
            assert selection_filter["Version"] == 2
            assert selection_filter["Where"][0]["Condition"]["In"]["Values"] == [
                [{"Literal": {"Value": "2023L"}}]
            ]
        validated = validate_json_documents(report_dir / "definition")
        assert len(validated) >= 5


def test_all_native_visual_types_emit_schema_valid_projections(
    tmp_path: Path,
) -> None:
    visual_roles = {
        "clusteredBarChart": {
            "Category": [{"column": "Orders.Order Date (Month)"}],
            "Y": [{"measure": "Orders.CY Sales"}],
            "Series": [{"column": "Orders.Order Date (Month)"}],
        },
        "clusteredColumnChart": {
            "Category": [{"column": "Orders.Order Date (Month)"}],
            "Y": [{"measure": "Orders.CY Sales"}],
            "Series": [{"column": "Orders.Order Date (Month)"}],
        },
        "lineChart": {
            "Category": [{"column": "Orders.Order Date (Month)"}],
            "Y": [{"measure": "Orders.CY Sales"}],
            "Series": [{"column": "Orders.Order Date (Month)"}],
        },
        "tableEx": {"Values": [{"column": "Orders.Order Date (Month)"}]},
        "pivotTable": {
            "Rows": [{"column": "Orders.Order Date (Month)"}],
            "Columns": [{"column": "Orders.Order Date (Month)"}],
            "Values": [{"measure": "Orders.CY Sales"}],
        },
        "scatterChart": {
            "Category": [{"column": "Orders.Order Date (Month)"}],
            "X": [{"measure": "Orders.CY Sales"}],
            "Y": [{"measure": "Orders.CY Sales"}],
        },
        "card": {"Values": [{"measure": "Orders.CY Sales"}]},
        "pieChart": {
            "Category": [{"column": "Orders.Order Date (Month)"}],
            "Y": [{"measure": "Orders.CY Sales"}],
        },
        "donutChart": {
            "Category": [{"column": "Orders.Order Date (Month)"}],
            "Y": [{"measure": "Orders.CY Sales"}],
        },
    }
    visuals = [
        {
            "id": f"native_{visual_type}",
            "type": "native",
            "visual_type": visual_type,
            "roles": roles,
            "title": f"{visual_type} title",
            "x": 0,
            "y": 0,
            "w": 300,
            "h": 200,
        }
        for visual_type, roles in visual_roles.items()
    ]
    layout_path = tmp_path / "native-layout.yml"
    layout_path.write_text(
        yaml.safe_dump(
            {
                "pages": [
                    {"tableau_dashboard": "Native fixture", "visuals": visuals}
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    dashboard = Dashboard("Native fixture", 800, 600, [])
    output_dir = tmp_path / "native-output"
    _, report_dir, visual_inventory = generate_pbir(
        "Native fixture",
        [dashboard],
        output_dir,
        layout_path,
        LAYOUT_MODEL_FIELDS,
    )
    assert len(visual_inventory) == len(visual_roles)
    assert len(validate_json_documents(output_dir)) >= len(visual_roles) + 3

    visuals_dir = (
        report_dir
        / "definition"
        / "pages"
        / "ReportSectionNativeFixture"
        / "visuals"
    )
    for visual_type, roles in visual_roles.items():
        document = json.loads(
            (
                visuals_dir
                / f"native_{visual_type}"
                / "visual.json"
            ).read_text(encoding="utf-8")
        )
        visual = document["visual"]
        assert visual["visualType"] == visual_type
        assert set(visual["query"]["queryState"]) == set(roles)
        for role, field_specs in roles.items():
            projections = visual["query"]["queryState"][role]["projections"]
            assert len(projections) == len(field_specs)
            for projection, field_spec in zip(projections, field_specs, strict=True):
                field_ref = next(iter(field_spec.values()))
                assert projection["queryRef"] == field_ref
                assert projection["nativeQueryRef"] == field_ref
                assert projection["displayName"] == field_ref.rsplit(".", 1)[-1]
                assert "field" in projection
        assert (
            visual["visualContainerObjects"]["title"][0]["properties"]["text"][
                "expr"
            ]["Literal"]["Value"]
            == f"'{visual_type} title'"
        )


def test_native_visual_rejects_unknown_model_fields(tmp_path: Path) -> None:
    layout_path = tmp_path / "unknown-native-layout.yml"
    layout_path.write_text(
        yaml.safe_dump(
            {
                "pages": [
                    {
                        "tableau_dashboard": "Native fixture",
                        "visuals": [
                            {
                                "id": "unknown",
                                "type": "native",
                                "visual_type": "clusteredBarChart",
                                "roles": {
                                    "Category": [
                                        {"column": "Orders.Does Not Exist"}
                                    ],
                                    "Y": [{"measure": "Orders.CY Sales"}],
                                },
                                "x": 0,
                                "y": 0,
                                "w": 300,
                                "h": 200,
                            }
                        ],
                    }
                ]
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Unknown model field"):
        load_layout(
            layout_path,
            [Dashboard("Native fixture", 800, 600, [])],
            LAYOUT_MODEL_FIELDS,
        )


@pytest.mark.parametrize(
    ("workbook_path", "expect_hr_substitution"),
    [
        (WORKBOOK_PATH, False),
        (HR_WORKBOOK_PATH, True),
    ],
)
def test_scaffold_emits_loadable_layouts_images_and_placeholders(
    tmp_path: Path,
    workbook_path: Path,
    expect_hr_substitution: bool,
) -> None:
    output_dir = tmp_path / workbook_path.stem.replace(" ", "-")
    result = scaffold_workbook(workbook_path, output_dir)
    assert Path(str(result["layout"])).is_file()
    assert int(result["copied_images"]) > 0
    assert len(list((output_dir / "images").rglob("*.*"))) > 0
    assert result["pages"] > 0

    layout = yaml.safe_load(
        (output_dir / "layout.yml").read_text(encoding="utf-8")
    )
    unpacked = unpack(workbook_path, tmp_path / f"{output_dir.name}-verify")
    workbook = parse_workbook(unpacked.twb_path)
    assert len(layout["pages"]) == len(workbook.dashboards)
    translations = CalculationCompiler(workbook).compile_all()
    measure_overrides = _load_overrides(output_dir / "overrides")
    model_overrides = load_model_overrides(output_dir / "overrides")
    auto_measures, _, date_columns = generate_auto_measures(
        workbook, translations, model_overrides, measure_overrides
    )
    model_fields = _model_field_types(
        workbook,
        translations,
        auto_measures,
        date_columns,
        measure_overrides,
        model_overrides,
        {},
    )
    load_layout(output_dir / "layout.yml", workbook.dashboards, model_fields)

    report = (output_dir / "SCAFFOLD_REPORT.md").read_text(encoding="utf-8")
    if expect_hr_substitution:
        assert "Unmapped worksheet Map States" not in report
        assert "map → bar (map visuals need Power BI sign-in)" in report
        assert "HR \\| Summary" in report

    original_layout = (output_dir / "layout.yml").read_bytes()
    with pytest.raises(FileExistsError, match="Refusing to overwrite"):
        scaffold_workbook(workbook_path, output_dir)
    assert (output_dir / "layout.yml").read_bytes() == original_layout


def test_hr_scaffold_maps_worksheets_and_emits_toggle_bookmarks(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "hr-scaffold"
    scaffold_workbook(HR_WORKBOOK_PATH, output_dir)
    layout = yaml.safe_load(
        (output_dir / "layout.yml").read_text(encoding="utf-8")
    )
    unpacked = unpack(HR_WORKBOOK_PATH, tmp_path / "hr-scaffold-verify")
    workbook = parse_workbook(unpacked.twb_path)
    pages = {page["tableau_dashboard"]: page for page in layout["pages"]}
    summary = pages["HR | Summary"]
    details = pages["HR | Details"]
    visuals_by_title = {
        visual["title"]: visual
        for page in layout["pages"]
        for visual in page["visuals"]
        if visual.get("type") == "native"
    }
    expected_types = {
        "BAN Active": "card",
        "Departments": "clusteredBarChart",
        "Gender": "pieChart",
        "Education vs Performance": "pivotTable",
        "Age vs Salary": "scatterChart",
        "Map States": "clusteredBarChart",
        "Gender vs Education Level": "clusteredBarChart",
    }
    for worksheet, expected_type in expected_types.items():
        assert visuals_by_title[worksheet]["visual_type"] == expected_type

    pivot_roles = visuals_by_title["Education vs Performance"]["roles"]
    assert {"Rows", "Columns", "Values"} <= set(pivot_roles)
    scatter_roles = visuals_by_title["Age vs Salary"]["roles"]
    assert {"Category", "X", "Y"} <= set(scatter_roles)
    series_visual = visuals_by_title["Gender vs Education Level"]
    assert "Series" in series_visual["roles"]
    rank_field = "Calculation_3363625995844042762"
    assert rank_field not in str(visuals_by_title["Departments"]["roles"])

    report = (output_dir / "SCAFFOLD_REPORT.md").read_text(encoding="utf-8")
    dropped_and_substituted = report.split(
        "## Dropped fields / substitutions", 1
    )[1].split("## Calculation translation status", 1)[0]
    assert rank_field in dropped_and_substituted
    assert "Map States: map → bar (map visuals need Power BI sign-in)" in report
    assert "HR \\| Summary" in report

    zone_by_id = {
        zone.id: zone
        for dashboard in workbook.dashboards
        for zone in _all_zones(dashboard.zones)
    }
    summary_visuals = summary["visuals"]
    all_visuals = [
        visual for page in layout["pages"] for visual in page["visuals"]
    ]

    def visuals_for_zone(zone_ids: set[str]) -> list[dict[str, object]]:
        return [
            visual
            for visual in summary_visuals
            if any(
                re.search(rf"_{re.escape(zone_id)}(?:_|$)", visual["id"])
                for zone_id in zone_ids
            )
        ]

    empty_zone_ids = {
        zone.id
        for dashboard in workbook.dashboards
        for zone in _all_zones(dashboard.zones)
        if zone.type_v2.casefold() == "empty" and not _zone_background(zone)
    }
    assert empty_zone_ids
    assert all(
        not any(
            re.search(rf"_{re.escape(zone_id)}(?:_|$)", visual["id"])
            for visual in all_visuals
        )
        for zone_id in empty_zone_ids
    )
    colored_empty = next(
        visual
        for visual in all_visuals
        if re.search(r"_223(?:_|$)", visual["id"])
    )
    assert colored_empty["type"] == "shape"
    assert colored_empty["fill"] == "#03c4a1"

    goto_visual = next(
        visual for visual in visuals_for_zone({"136"}) if visual["type"] == "image"
    )
    assert goto_visual["action"] == {
        "type": "page",
        "target": "HR | Details",
    }
    for zone in zone_by_id.values():
        if zone.button is None or zone.button.kind != "export":
            continue
        export_visual = next(
            visual
            for page in layout["pages"]
            for visual in page["visuals"]
            if re.search(
                rf"_{re.escape(zone.id)}(?:_|$)", visual["id"]
            )
        )
        assert export_visual["type"] == "image"
        assert "action" not in export_visual
    assert "Power BI: File > Export" in report

    info_shown = next(
        visual
        for visual in summary_visuals
        if visual.get("file") == "Image/info-shown.png"
    )
    info_hidden = next(
        visual
        for visual in summary_visuals
        if visual.get("file") == "Image/info-hidden.png"
    )
    assert info_shown["hidden"] is True
    assert info_hidden["hidden"] is False
    assert info_shown["action"] == {"type": "bookmark", "target": "141_hidden"}
    assert info_hidden["action"] == {"type": "bookmark", "target": "141_shown"}
    bookmarks = {bookmark["name"]: bookmark for bookmark in layout["bookmarks"]}
    shown_bookmark = bookmarks["141_shown"]
    hidden_bookmark = bookmarks["141_hidden"]
    assert shown_bookmark["page"] == "HR | Summary"
    assert {info_shown["id"], info_hidden["id"]} <= set(
        shown_bookmark["targets"]
    )
    assert info_hidden["id"] in shown_bookmark["hidden"]
    assert info_shown["id"] in hidden_bookmark["hidden"]
    target_zone_ids = {zone.id for zone in _all_zones([zone_by_id["137"]])}
    expected_container_visuals = {
        visual["id"] for visual in visuals_for_zone(target_zone_ids)
    }
    assert expected_container_visuals <= set(shown_bookmark["targets"])
    assert expected_container_visuals <= set(hidden_bookmark["targets"])
    assert expected_container_visuals <= set(hidden_bookmark["hidden"])

    filter_active = next(
        visual
        for visual in summary_visuals
        if visual.get("file") == "Image/filter-active.png"
    )
    filter_inactive = next(
        visual
        for visual in summary_visuals
        if visual.get("file") == "Image/filter-inactive.png"
    )
    assert filter_active["hidden"] is True
    assert filter_inactive["hidden"] is False
    filter_zone_ids = {zone.id for zone in _all_zones([zone_by_id["122"]])}
    hidden_filter_visuals = visuals_for_zone(filter_zone_ids)
    assert hidden_filter_visuals
    assert all(visual["hidden"] for visual in hidden_filter_visuals)

    details_visuals = details["visuals"]
    assert any(visual["type"] == "native" for visual in details_visuals)
    details_info = next(
        visual
        for visual in details_visuals
        if visual.get("file") == "Image/info-shown.png"
    )
    assert details_info["action"] == {
        "type": "bookmark",
        "target": "HR_Details_141_hidden",
    }
    assert bookmarks["HR_Details_141_hidden"]["page"] == "HR | Details"
    assert len(bookmarks) == len(layout["bookmarks"])


def test_scaffold_report_escapes_pipe_characters() -> None:
    report = _scaffold_report_markdown(
        [
            {
                "dashboard": "HR | Summary",
                "zone": "17",
                "source": "Age | Salary",
                "visual_type": "native:scatterChart",
            }
        ],
        [],
        [],
        ["Age | Salary: Rank"],
        ["Map States: map → bar"],
    )
    assert "| HR \\| Summary | `17` | Age \\| Salary |" in report
    assert "Age | Salary: Rank" in report
    assert "Map States: map → bar" in report


def test_shape_outline_is_hidden_without_selector(
    workbook_and_unpacked, tmp_path: Path
) -> None:
    _, workbook = workbook_and_unpacked
    layout_path = tmp_path / "shape-layout.yml"
    layout_path.write_text(
        "pages:\n"
        "  - tableau_dashboard: Sales Dashboard\n"
        "    visuals:\n"
        "      - id: panel\n"
        "        type: shape\n"
        "        fill: '#FFFFFF'\n"
        "        x: 0\n"
        "        y: 0\n"
        "        w: 200\n"
        "        h: 100\n",
        encoding="utf-8",
    )
    _, report_dir, _ = generate_pbir(
        "Sales & Customer Dashboards",
        workbook.dashboards,
        tmp_path / "shape-output",
        layout_path,
        {},
    )
    shape_path = (
        report_dir
        / "definition"
        / "pages"
        / "ReportSectionSalesDashboard"
        / "visuals"
        / "panel"
        / "visual.json"
    )
    shape = json.loads(shape_path.read_text(encoding="utf-8"))["visual"]
    assert shape["objects"]["outline"] == [
        {"properties": {"show": {"expr": {"Literal": {"Value": "false"}}}}}
    ]


def test_trends_top_rule_is_conditional() -> None:
    default_spec = step_trends(600, 350)
    configured_spec = step_trends(
        600,
        350,
        geometry={"top_rule": [4, 561, 0.5]},
    )

    def has_top_rule(spec: dict[str, object]) -> bool:
        return any(
            mark.get("type") == "rule"
            and mark.get("encode", {})
            .get("update", {})
            .get("x", {})
            .get("value")
            == 4
            and mark["encode"]["update"]["y"]["value"] == 0.5
            and mark["encode"]["update"]["x2"]["value"] == 561
            and mark["encode"]["update"]["y2"]["value"] == 0.5
            and mark["encode"]["update"]["strokeWidth"]["value"] == 1
            for mark in spec["marks"]
        )

    assert not has_top_rule(default_spec)
    assert has_top_rule(configured_spec)
