from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from tableau2pbip import visuals as visual_builders
from tableau2pbip.calc.ast import Binary, Call, Field, Literal
from tableau2pbip.calc.dax import CalculationCompiler, generate_auto_measures
from tableau2pbip.calc.parser import parse
from tableau2pbip.extract import extract_tables
from tableau2pbip.ir import FieldRef
from tableau2pbip.layout import visual_folder_name
from tableau2pbip.migrate import (
    _load_overrides,
    _model_field_types,
    _report_markdown,
    _resolve_layout_path,
    _resolve_overrides_path,
    _translation_records,
)
from tableau2pbip.overrides import load_model_overrides
from tableau2pbip.parse import decode_field_ref, parse_workbook
from tableau2pbip.pbir import generate_pbir
from tableau2pbip.schema_validation import validate_json_documents
from tableau2pbip.tmdl import generate_tmdl
from tableau2pbip.unpack import unpack


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_PATH = (
    ROOT
    / "projects"
    / "sales-dashboard-project"
    / "Sales & Customer Dashboards.twbx"
)
LAYOUT_FIXTURE_PATH = ROOT / "validation" / "tableau2pbip_layout_fixture.yml"
LAYOUT_FIXTURE_IMAGE = ROOT / "validation" / "tableau2pbip_fixture.svg"
LAYOUT_MODEL_FIELDS = {
    "Orders.Order Date (Month)": "int64",
    "Orders.CY Sales": "double",
    "Select Year.Select Year": "int64",
}


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
    auto_measures, _, date_columns = generate_auto_measures(workbook, translations)
    data_dir = tmp_path / "data"
    extraction = extract_tables(unpacked, workbook, data_dir)
    overrides_dir = ROOT / "migrations" / "sales-customer-dashboards" / "overrides"
    measure_overrides = _load_overrides(overrides_dir)
    model_overrides = load_model_overrides(overrides_dir)
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
    assert "In" in slicer["filterConfig"]["filters"][0]["filter"]["Where"][0][
        "Condition"
    ]
    assert (
        slicer["filterConfig"]["filters"][0]["filter"]["Where"][0]["Condition"][
            "In"
        ]["Values"][0][0]["Literal"]["Value"]
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
