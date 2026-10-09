"""Step 2 of the migration: turn the workbook inventory into a Power BI project (PBIP).

Reads  part1-tableau-to-powerbi/inventory.json (from extract_twbx.py)
Writes part1-tableau-to-powerbi/Superstore.pbip
       part1-tableau-to-powerbi/Superstore.SemanticModel/   (TMDL tables, measures, relationships)
       part1-tableau-to-powerbi/Superstore.Report/          (PBIR pages + visuals)
       part1-tableau-to-powerbi/dax_translations.md         (every Tableau calc next to its DAX)
       part1-tableau-to-powerbi/sheet_mapping.md            (every Tableau sheet -> Power BI visual)

Open the .pbip in Power BI Desktop (Windows) with the "Power BI Project (.pbip)" preview
feature enabled; the CSV paths come from the DataFolder parameter in expressions.tmdl.
"""
import hashlib
import json
import os
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
P1 = os.path.join(ROOT, "part1-tableau-to-powerbi")
MODEL = os.path.join(P1, "Superstore.SemanticModel")
REPORT = os.path.join(P1, "Superstore.Report")


def tag(name):
    """Stable lineage tags so re-running the generator produces no spurious diffs."""
    return str(uuid.UUID(hashlib.md5(name.encode()).hexdigest()))


def vid(name):
    return hashlib.sha1(name.encode()).hexdigest()[:20]


# --------------------------------------------------------------------------- model
# Physical columns (name, DAX type, source CSV column, M type).
TABLES = {
    "Orders": {
        "csv": "orders.csv",
        "columns": [
            ("Row ID", "int64", "Int64.Type"), ("Order ID", "string", "type text"),
            ("Order Date", "dateTime", "type date"), ("Ship Date", "dateTime", "type date"),
            ("Ship Mode", "string", "type text"), ("Customer ID", "string", "type text"),
            ("Segment", "string", "type text"), ("Postal Code", "int64", "Int64.Type"),
            ("Product ID", "string", "type text"), ("Sales", "double", "type number"),
            ("Quantity", "int64", "Int64.Type"), ("Discount", "double", "type number"),
            ("Profit", "double", "type number"),
        ],
        "calculated_columns": [
            # Tableau 'Order Date (Year)' = YEAR([Order Date]) and the WEEK() shelf on Weekly Trends.
            ("Order Year", "int64", "YEAR(Orders[Order Date])", "Tableau: YEAR([Order Date]) ('Order Date (Year)')"),
            ("Order Week", "dateTime", "Orders[Order Date] - WEEKDAY(Orders[Order Date], 1) + 1",
             "Tableau: WEEK([Order Date]) on the Weekly Trends columns shelf (weeks start Sunday)"),
        ],
    },
    "Customers": {"csv": "customers.csv", "columns": [("Customer ID", "string", "type text"), ("Customer Name", "string", "type text")], "calculated_columns": []},
    "Products": {"csv": "products.csv", "columns": [("Product ID", "string", "type text"), ("Category", "string", "type text"), ("Sub-Category", "string", "type text"), ("Product Name", "string", "type text")], "calculated_columns": []},
    "Location": {"csv": "location.csv", "columns": [("Postal Code", "int64", "Int64.Type"), ("City", "string", "type text"), ("State", "string", "type text"), ("Region", "string", "type text"), ("Country/Region", "string", "type text")], "calculated_columns": []},
}

# Tableau has no equivalent of a many-to-many bridge for Products (32 duplicated IDs), so the
# Products relationship is many-to-many; the others are classic 1:* lookups.
RELATIONSHIPS = [
    ("Orders", "Customer ID", "Customers", "Customer ID", "oneToMany"),
    ("Orders", "Postal Code", "Location", "Postal Code", "manyToMany"),
    ("Orders", "Product ID", "Products", "Product ID", "manyToMany"),
]

# Every Tableau calculated field / parameter and its DAX translation.
# (tableau_name, dax_name, dax_expression, format, translation_note)
Y = "VAR y = [Selected Year] RETURN "
MEASURES = [
    # -- parameter -------------------------------------------------------------------
    ("Current Year", "Selected Year", "SELECTEDVALUE('Select Year'[Year], 2023)", "0",
     "Tableau parameter [Select Year] (default 2023) becomes a disconnected 'Select Year' table driven by a slicer; SELECTEDVALUE reads the choice."),
    ("Previous Year", "Previous Year", "[Selected Year] - 1", "0", "Same arithmetic as Tableau."),
    # -- current year / previous year row filters ----------------------------------
    ("CY Sales", "CY Sales", Y + "CALCULATE(SUM(Orders[Sales]), Orders[Order Year] = y)", '"$"#,##0',
     "Tableau IF YEAR([Order Date]) = [Select Year] THEN [Sales] END (row-level IF, then SUM) becomes CALCULATE with a year filter."),
    ("PY Sales", "PY Sales", Y + "CALCULATE(SUM(Orders[Sales]), Orders[Order Year] = y - 1)", '"$"#,##0', "Same, with year - 1."),
    ("CY Profit", "CY Profit", Y + "CALCULATE(SUM(Orders[Profit]), Orders[Order Year] = y)", '"$"#,##0', "Row-level IF -> CALCULATE."),
    ("PY Profit", "PY Profit", Y + "CALCULATE(SUM(Orders[Profit]), Orders[Order Year] = y - 1)", '"$"#,##0', "Row-level IF -> CALCULATE."),
    ("CY Quantity", "CY Quantity", Y + "CALCULATE(SUM(Orders[Quantity]), Orders[Order Year] = y)", "#,##0", "Row-level IF -> CALCULATE."),
    ("PY Quantity", "PY Quantity", Y + "CALCULATE(SUM(Orders[Quantity]), Orders[Order Year] = y - 1)", "#,##0", "Row-level IF -> CALCULATE."),
    ("CY Orders", "CY Orders", Y + "CALCULATE(DISTINCTCOUNT(Orders[Order ID]), Orders[Order Year] = y)", "#,##0",
     "Tableau keeps the Order ID string and the sheet applies COUNTD; in DAX the DISTINCTCOUNT lives in the measure."),
    ("PY Orders", "PY Orders", Y + "CALCULATE(DISTINCTCOUNT(Orders[Order ID]), Orders[Order Year] = y - 1)", "#,##0", "COUNTD -> DISTINCTCOUNT."),
    ("CY Customers", "CY Customers", Y + "CALCULATE(DISTINCTCOUNT(Orders[Customer ID]), Orders[Order Year] = y)", "#,##0", "COUNTD -> DISTINCTCOUNT."),
    ("PY Customers", "PY Customers", Y + "CALCULATE(DISTINCTCOUNT(Orders[Customer ID]), Orders[Order Year] = y - 1)", "#,##0", "COUNTD -> DISTINCTCOUNT."),
    # -- ratios -----------------------------------------------------------------------
    ("% Diff Sales", "% Diff Sales", "DIVIDE([CY Sales] - [PY Sales], [PY Sales])", "0.0%", "Division -> DIVIDE (safe on zero)."),
    ("% Diff Profit", "% Diff Profit", "DIVIDE([CY Profit] - [PY Profit], [CY Profit])", "0.0%",
     "Kept faithful to the source: the Tableau formula divides by CY Profit, not PY Profit. Flagged for the dashboard owner."),
    ("% Diff Quantity", "% Diff Quantity", "DIVIDE([CY Quantity] - [PY Quantity], [PY Quantity])", "0.0%", "Division -> DIVIDE."),
    ("% Diff Orders", "% Diff Orders", "DIVIDE([CY Orders] - [PY Orders], [PY Orders])", "0.0%", "Division -> DIVIDE."),
    ("% Diff Customers", "% Diff Customers", "DIVIDE([CY Customers] - [PY Customers], [PY Customers])", "0.0%", "Division -> DIVIDE."),
    ("CY Sales per Customer", "CY Sales per Customer", "DIVIDE([CY Sales], [CY Customers])", '"$"#,##0', "Division -> DIVIDE."),
    ("PY Sales per Customer", "PY Sales per Customer", "DIVIDE([PY Sales], [PY Customers])", '"$"#,##0', "Division -> DIVIDE."),
    ("% Diff Sales per Customers", "% Diff Sales per Customer", "DIVIDE([CY Sales per Customer] - [PY Sales per Customer], [PY Sales per Customer])", "0.0%", "Division -> DIVIDE."),
    # -- table calculations (WINDOW_*) --------------------------------------------------
    ("KPI CY Less PY", "KPI CY Less PY", 'IF([CY Sales] < [PY Sales], "⬤", "")', None, "Plain IF; used as a marker column in the Sub-Category comparison."),
    ("KPI Sales Avg", "KPI Sales Avg",
     'IF([CY Sales] > AVERAGEX(ALLSELECTED(Products[Sub-Category]), [CY Sales]), "Above", "Below")', None,
     "WINDOW_AVG over the Sub-Category partition becomes AVERAGEX over ALLSELECTED(Sub-Category)."),
    ("KPI Profit Avg", "KPI Profit Avg",
     'IF([CY Profit] > AVERAGEX(ALLSELECTED(Products[Sub-Category]), [CY Profit]), "Above", "Below")', None,
     "WINDOW_AVG -> AVERAGEX(ALLSELECTED(...))."),
    ("Min/Max Sales", "Min/Max Sales", None, '"$"#,##0', "WINDOW_MAX / WINDOW_MIN over the weekly partition become MAXX / MINX over ALLSELECTED(Order Week); returns BLANK() for in-between weeks exactly like the Tableau END-without-ELSE."),
    ("Min/Max Profit", "Min/Max Profit", None, '"$"#,##0', "Same pattern as Min/Max Sales."),
    ("Min/Max Quantity", "Min/Max Quantity", None, "#,##0", "Same pattern as Min/Max Sales."),
    ("Min/Max Orders", "Min/Max Orders", None, "#,##0", "Same pattern as Min/Max Sales."),
    ("Min/Max Customers", "Min/Max Customers", None, "#,##0", "Same pattern as Min/Max Sales."),
    ("Min/Max Sales Per Customers", "Min/Max Sales per Customer", None, '"$"#,##0', "Same pattern as Min/Max Sales."),
    # -- level of detail ----------------------------------------------------------------
    ("{SUM([CY Sales])}", "CY Sales (Total)", "CALCULATE([CY Sales], REMOVEFILTERS(Orders), REMOVEFILTERS(Products), REMOVEFILTERS(Customers), REMOVEFILTERS(Location))", '"$"#,##0',
     "Table-scoped LOD {SUM(...)} ignores every dimension on the sheet -> CALCULATE with REMOVEFILTERS on the dimension tables."),
    ("Nr of Orders per Customers", "Customers with N Orders",
     "VAR n = SELECTEDVALUE('Orders per Customer'[Orders]) RETURN COUNTROWS(FILTER(VALUES(Orders[Customer ID]), [CY Orders] = n))", "#,##0",
     "{FIXED [CY Customers]: COUNTD([CY Orders])} is used as a histogram axis. DAX cannot put a parameter-dependent LOD in a column, so the bins become a disconnected 'Orders per Customer' table and this measure counts the customers that fall in each bin."),
    ("INDEX()", "Customer Rank", "RANKX(ALLSELECTED(Customers[Customer Name]), [CY Sales], , DESC, DENSE)", "0",
     "INDEX() over customers sorted by sales -> RANKX."),
    ("Order Date (Year)", "(calculated column Orders[Order Year])", None, None, "Row-level YEAR() becomes a calculated column, not a measure."),
    ("Select Year (parameter)", "(table 'Select Year', slicer)", None, None, "List parameter with values 2020-2023 -> single-select slicer on a disconnected table."),
]


def minmax(measure, partition="Orders[Order Week]"):
    return (f"VAR cur = [{measure}] VAR mx = MAXX(ALLSELECTED({partition}), [{measure}]) "
            f"VAR mn = MINX(ALLSELECTED({partition}), [{measure}]) RETURN IF(cur = mx || cur = mn, cur)")


MINMAX_SOURCE = {
    "Min/Max Sales": "CY Sales", "Min/Max Profit": "CY Profit", "Min/Max Quantity": "CY Quantity",
    "Min/Max Orders": "CY Orders", "Min/Max Customers": "CY Customers",
    "Min/Max Sales per Customer": "CY Sales per Customer",
}


def measure_rows():
    rows = []
    for t_name, d_name, expr, fmt, note in MEASURES:
        if expr is None and d_name in MINMAX_SOURCE:
            expr = minmax(MINMAX_SOURCE[d_name])
        rows.append((t_name, d_name, expr, fmt, note))
    return rows


def tmdl_measure(name, expr, fmt, note):
    q = f"'{name}'" if any(c in name for c in " %/()-") else name
    out = [f"\t/// {note}", f"\tmeasure {q} = {expr}"]
    if fmt:
        out.append(f"\t\tformatString: {fmt}")
    out.append(f"\t\tlineageTag: {tag('measure:' + name)}")
    out.append("")
    return "\n".join(out)


def tmdl_column(name, dtype, note=None, expr=None, summarize="none", is_key=False, source_col=None):
    q = f"'{name}'" if any(c in name for c in " %/()-") else name
    out = []
    if note:
        out.append(f"\t/// {note}")
    out.append(f"\tcolumn {q}" + (f" = {expr}" if expr else ""))
    out.append(f"\t\tdataType: {dtype}")
    if is_key:
        out.append("\t\tisKey")
    if dtype == "dateTime":
        out.append("\t\tformatString: yyyy-mm-dd")
    out.append(f"\t\tsummarizeBy: {summarize}")
    if not expr:
        out.append(f"\t\tsourceColumn: {source_col or name}")
    out.append(f"\t\tlineageTag: {tag('column:' + name)}")
    out.append("")
    return "\n".join(out)


def m_partition(table, csv, columns):
    types = ", ".join(f'{{"{c}", {mt}}}' for c, _, mt in columns)
    return (
        f"\tpartition {table} = m\n\t\tmode: import\n\t\tsource =\n"
        f"\t\t\t\tlet\n"
        f'\t\t\t\t    Source = Csv.Document(File.Contents(DataFolder & "{csv}"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),\n'
        f"\t\t\t\t    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),\n"
        f"\t\t\t\t    Typed = Table.TransformColumnTypes(Headers, {{{types}}})\n"
        f"\t\t\t\tin\n\t\t\t\t    Typed\n\n"
    )


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)


def build_model(inv):
    write(os.path.join(MODEL, "definition.pbism"), json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.2", "settings": {"qnaEnabled": True}}, indent=2))
    write(os.path.join(MODEL, ".platform"), json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "SemanticModel", "displayName": "Superstore"},
        "config": {"version": "2.0", "logicalId": tag("model")}}, indent=2))
    write(os.path.join(MODEL, "definition", "database.tmdl"), "database\n\tcompatibilityLevel: 1601\n")
    write(os.path.join(MODEL, "definition", "expressions.tmdl"),
          '/// Folder that holds the CSVs exported from the Tableau extract (superstore-demo/data).\n'
          'expression DataFolder = "C:\\superstore-demo\\data\\" meta [IsParameterQuery = true, Type = "Text", IsParameterQueryRequired = true]\n'
          f"\tlineageTag: {tag('expr:DataFolder')}\n\n\tannotation PBI_ResultType = Text\n")

    table_names = list(TABLES) + ["Select Year", "Orders per Customer", "Measures"]
    model = ["model Model", "\tculture: en-US", "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
             "\tsourceQueryCulture: en-US", "\tdataAccessOptions", "\t\tlegacyRedirects", "\t\treturnErrorValuesAsNull", "",
             "annotation PBI_QueryOrder = " + json.dumps(table_names), "", "annotation __PBI_TimeIntelligenceEnabled = 0", ""]
    for t in table_names:
        model.append(f"ref table {'\'' + t + '\'' if ' ' in t else t}")
    model.append("")
    write(os.path.join(MODEL, "definition", "model.tmdl"), "\n".join(model))

    rels = []
    for ft, fc, tt, tc, card in RELATIONSHIPS:
        rels.append(f"relationship {tag('rel:' + ft + fc + tt)}\n\tfromColumn: {ft}.'{fc}'\n\ttoColumn: {tt}.'{tc}'"
                    + ("\n\tfromCardinality: many\n\ttoCardinality: many" if card == "manyToMany" else "") + "\n")
    write(os.path.join(MODEL, "definition", "relationships.tmdl"), "\n".join(rels))

    for t, spec in TABLES.items():
        body = [f"/// Source: Tableau data source 'Sales DataSource', table {spec['csv']} ({inv['tables'][spec['csv'][:-4]]['rows']:,} rows in the extract).",
                f"table {t}", f"\tlineageTag: {tag('table:' + t)}", ""]
        for name, dtype, _ in spec["columns"]:
            body.append(tmdl_column(name, dtype, summarize="sum" if dtype in ("double",) else "none"))
        for name, dtype, expr, note in spec["calculated_columns"]:
            body.append(tmdl_column(name, dtype, note=note, expr=expr))
        body.append(m_partition(t, spec["csv"], spec["columns"]))
        write(os.path.join(MODEL, "definition", "tables", f"{t}.tmdl"), "\n".join(body))

    # Disconnected parameter table (Tableau parameter 'Select Year').
    years = [int(v) for v in inv["parameters"][0]["allowed_values"]]
    write(os.path.join(MODEL, "definition", "tables", "Select Year.tmdl"),
          "/// Tableau parameter 'Select Year' (list 2020-2023, default 2023). Disconnected table; a single-select slicer drives [Selected Year].\n"
          f"table 'Select Year'\n\tlineageTag: {tag('table:Select Year')}\n\n"
          + tmdl_column("Year", "int64", is_key=True, source_col="[Year]") +
          f"\tpartition 'Select Year' = calculated\n\t\tmode: import\n\t\tsource = DATATABLE(\"Year\", INTEGER, {{{', '.join('{' + str(y) + '}' for y in years)}}})\n")

    write(os.path.join(MODEL, "definition", "tables", "Orders per Customer.tmdl"),
          "/// Histogram bins for the Customer Distribution chart, replacing the Tableau LOD {FIXED [CY Customers]: COUNTD([CY Orders])}.\n"
          f"table 'Orders per Customer'\n\tlineageTag: {tag('table:Orders per Customer')}\n\n"
          + tmdl_column("Orders", "int64", is_key=True, source_col="[Value]") +
          "\tpartition 'Orders per Customer' = calculated\n\t\tmode: import\n\t\tsource = GENERATESERIES(1, 20, 1)\n")

    body = ["/// Every Tableau calculated field, translated to DAX. See dax_translations.md for the side-by-side.",
            "table Measures", f"\tlineageTag: {tag('table:Measures')}", ""]
    for _, d_name, expr, fmt, note in measure_rows():
        if expr:
            body.append(tmdl_measure(d_name, expr, fmt, note))
    body.append(tmdl_column("Value", "int64").replace("sourceColumn: Value", "isHidden\n\t\tsourceColumn: [Value]"))
    body.append("\tpartition Measures = calculated\n\t\tmode: import\n\t\tsource = {BLANK()}\n")
    write(os.path.join(MODEL, "definition", "tables", "Measures.tmdl"), "\n".join(body))


# --------------------------------------------------------------------------- report
def field(entity, prop, measure=False):
    kind = "Measure" if measure else "Column"
    return {"field": {kind: {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
            "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop}


def literal(v):
    return {"expr": {"Literal": {"Value": v}}}


def visual(name, vtype, pos, roles, title=None, extra_objects=None, sort=None):
    query = {"queryState": {role: {"projections": projs} for role, projs in roles.items()}}
    if sort:
        query["sortDefinition"] = {"sort": [{"field": sort[0]["field"], "direction": sort[1]}], "isDefaultSort": True}
    v = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.9.0/schema.json",
        "name": vid(name),
        "position": {"x": pos[0], "y": pos[1], "z": pos[4], "width": pos[2], "height": pos[3], "tabOrder": pos[4]},
        "visual": {"visualType": vtype, "query": query, "objects": extra_objects or {}, "drillFilterOtherVisuals": True,
                   "visualContainerObjects": {"title": [{"properties": {"show": literal("true" if title else "false"),
                                                                             **({"text": literal(f"'{title}'")} if title else {})}}]}},
    }
    return v


def page(name, display, visuals, order):
    pdir = os.path.join(REPORT, "definition", "pages", name)
    write(os.path.join(pdir, "page.json"), json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
        "name": name, "displayName": display, "displayOption": "FitToPage", "height": 800, "width": 1200,
        "objects": {"background": [{"properties": {"color": {"solid": {"color": literal("'#F6F7F9'")}}, "transparency": literal("0D")}}]}}, indent=2))
    for v in visuals:
        write(os.path.join(pdir, "visuals", v["name"], "visual.json"), json.dumps(v, indent=2))
    order.append(name)


def card(name, measure, pos, title):
    return visual(name, "cardVisual", pos, {"Data": [field("Measures", measure, True)]}, title)


def slicer(pos):
    return visual("Select Year", "slicer", pos, {"Values": [{**field("Select Year", "Year"), "active": True}]}, "Select Year",
                  {"data": [{"properties": {"mode": literal("'Dropdown'")}}],
                   "selection": [{"properties": {"singleSelect": literal("true"), "strictSingleSelect": literal("true")}}]})


SHEET_MAP = []  # (dashboard, tableau sheet, tableau mark, power bi visual, fields)


def build_report():
    write(os.path.join(REPORT, "definition.pbir"), json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0", "datasetReference": {"byPath": {"path": "../Superstore.SemanticModel"}}}, indent=2))
    write(os.path.join(REPORT, ".platform"), json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
        "metadata": {"type": "Report", "displayName": "Superstore"},
        "config": {"version": "2.0", "logicalId": tag("report")}}, indent=2))
    write(os.path.join(REPORT, "definition", "version.json"), json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json", "version": "2.0.0"}, indent=2))
    write(os.path.join(REPORT, "definition", "report.json"), json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/2.0.0/schema.json",
        "themeCollection": {"baseTheme": {"name": "CY24SU10", "reportVersionAtImport": {"visual": "1.8.97", "report": "2.0.97", "page": "1.3.97"}, "type": "SharedResources"}},
        "resourcePackages": [{"name": "SharedResources", "type": "SharedResources", "items": [{"name": "CY24SU10", "path": "BaseThemes/CY24SU10.json", "type": "BaseTheme"}]}],
        "settings": {"useStylableVisualContainerHeader": True, "defaultFilterActionIsDataFilter": True, "useEnhancedTooltips": True}}, indent=2))

    order = []
    # ---- Sales Dashboard -----------------------------------------------------------
    S = "Sales Dashboard"
    vis = [slicer((920, 20, 260, 60, 1000))]
    SHEET_MAP.append((S, "Select Year (parameter)", "parameter control", "slicer (single select)", "Select Year[Year]"))
    for i, (sheet, m) in enumerate([("KPI Sales", "CY Sales"), ("KPI Profit", "CY Profit"), ("KPI Quantity", "CY Quantity")]):
        vis.append(card(sheet, m, (20 + i * 300, 100, 280, 110, 2000 + i), f"{m}"))
        pct = {"CY Sales": "% Diff Sales", "CY Profit": "% Diff Profit", "CY Quantity": "% Diff Quantity"}[m]
        vis.append(card(sheet + " pct", pct, (20 + i * 300, 215, 280, 50, 2100 + i), f"{pct} vs PY"))
        SHEET_MAP.append((S, sheet, "Text / sparkline", "2 cards", f"[{m}], [{pct}]"))
    vis.append(visual("Weekly Trends", "lineChart", (20, 290, 880, 240, 3000),
                      {"Category": [{**field("Orders", "Order Week"), "active": True}],
                       "Y": [field("Measures", "CY Sales", True), field("Measures", "CY Profit", True)]},
                      "Weekly Trends — Sales & Profit (selected year)"))
    SHEET_MAP.append((S, "Weekly Trends", "Line (WEEK(Order Date) x SUM(CY Sales), SUM(CY Profit))", "lineChart", "Orders[Order Week] x [CY Sales], [CY Profit]"))
    vis.append(visual("Subcategory Comparison", "clusteredBarChart", (20, 545, 880, 240, 4000),
                      {"Category": [{**field("Products", "Sub-Category"), "active": True}],
                       "Y": [field("Measures", "CY Sales", True), field("Measures", "PY Sales", True)]},
                      "Sales by Sub-Category — selected year vs previous year",
                      sort=(field("Measures", "CY Sales", True), "Descending")))
    SHEET_MAP.append((S, "Subcategory Comparison", "Bar (Sub-Category x CY Sales, PY Sales, CY Profit; KPI CY Less PY marker)", "clusteredBarChart + table", "Products[Sub-Category] x [CY Sales], [PY Sales]"))
    vis.append(visual("Subcategory KPI", "tableEx", (920, 100, 260, 685, 5000),
                      {"Values": [field("Products", "Sub-Category"), field("Measures", "CY Profit", True),
                                  field("Measures", "KPI Sales Avg", True), field("Measures", "KPI CY Less PY", True)]},
                      "Sub-Category KPI flags"))
    SHEET_MAP.append((S, "Legend KPI / Legend Subcategory", "legend sheets", "tableEx (flags) — legends are native in Power BI", "[KPI Sales Avg], [KPI CY Less PY]"))
    page("sales", S, vis, order)

    # ---- Customer Dashboard --------------------------------------------------------
    C = "Customer Dashboard"
    vis = [slicer((920, 20, 260, 60, 1000))]
    for i, (sheet, m, pct) in enumerate([("KPI Customers", "CY Customers", "% Diff Customers"), ("KPI Orders", "CY Orders", "% Diff Orders"),
                                         ("KPI Sales Per Customers", "CY Sales per Customer", "% Diff Sales per Customer")]):
        vis.append(card(sheet, m, (20 + i * 300, 100, 280, 110, 2000 + i), m))
        vis.append(card(sheet + " pct", pct, (20 + i * 300, 215, 280, 50, 2100 + i), f"{pct} vs PY"))
        SHEET_MAP.append((C, sheet, "Text / sparkline", "2 cards", f"[{m}], [{pct}]"))
    vis.append(visual("Customer Distribution", "clusteredColumnChart", (20, 290, 580, 240, 3000),
                      {"Category": [{**field("Orders per Customer", "Orders"), "active": True}],
                       "Y": [field("Measures", "Customers with N Orders", True)]},
                      "Customer Distribution — customers by number of orders"))
    SHEET_MAP.append((C, "Customer Distribution", "Bar (LOD orders-per-customer x COUNTD(CY Customers))", "clusteredColumnChart", "'Orders per Customer'[Orders] x [Customers with N Orders]"))
    vis.append(visual("Top Customers", "tableEx", (20, 545, 1160, 240, 4000),
                      {"Values": [field("Measures", "Customer Rank", True), field("Customers", "Customer Name"),
                                  field("Measures", "CY Sales", True), field("Measures", "CY Profit", True), field("Measures", "CY Orders", True)]},
                      "Top Customers (selected year)", sort=(field("Measures", "CY Sales", True), "Descending")))
    SHEET_MAP.append((C, "Top Customers", "Text table (INDEX() rank x Customer Name, MAX(Order Date), measures)", "tableEx sorted by CY Sales", "[Customer Rank], Customers[Customer Name], [CY Sales], [CY Profit], [CY Orders]"))
    page("customers", C, vis, order)

    write(os.path.join(REPORT, "definition", "pages", "pages.json"), json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
        "pageOrder": order, "activePageName": order[0]}, indent=2))

    for sheet in ["Test KPI", "Test KPI2", "Test Max Min"]:
        SHEET_MAP.append(("(not on a dashboard)", sheet, "scratch sheet", "not migrated — not referenced by any dashboard", ""))


def build_docs(inv):
    L = ["# Tableau calculated fields → DAX", "",
         "Generated by `scripts/build_pbip.py`. Measures live in `Superstore.SemanticModel/definition/tables/Measures.tmdl`.", "",
         "| Tableau field | Tableau formula | DAX name | DAX | Note |", "|---|---|---|---|---|"]
    formulas = {c["name"]: c["formula"] for c in inv["calculated_fields"]}
    formulas["Select Year (parameter)"] = "parameter, list 2020-2023, default 2023"
    for t_name, d_name, expr, fmt, note in measure_rows():
        f = formulas.get(t_name, "").replace("\r\n", " ").replace("\n", " ").replace("|", "\\|")
        e = (expr or "").replace("|", "\\|")
        L.append(f"| {t_name} | `{f}` | {d_name} | `{e}` | {note} |")
    L += ["", "## Translation rules used", "",
          "| Tableau pattern | DAX pattern |", "|---|---|",
          "| Parameter | Disconnected table + slicer, read with `SELECTEDVALUE()` |",
          "| `IF <row condition> THEN [Measure] END` then `SUM()` | `CALCULATE(SUM(...), <condition>)` |",
          "| `COUNTD()` | `DISTINCTCOUNT()` |",
          "| `A / B` | `DIVIDE(A, B)` |",
          "| `WINDOW_AVG / WINDOW_MAX / WINDOW_MIN` (table calc) | `AVERAGEX / MAXX / MINX` over `ALLSELECTED(<partition column>)` |",
          "| `{ SUM(...) }` (table-scoped LOD) | `CALCULATE(..., REMOVEFILTERS(...))` |",
          "| `{ FIXED dim : agg }` used as a dimension | Disconnected bin table + counting measure |",
          "| `INDEX()` | `RANKX(ALLSELECTED(...), ...)` |",
          "| `YEAR([date])`, `WEEK([date])` on a shelf | Calculated columns `Order Year`, `Order Week` |", ""]
    write(os.path.join(P1, "dax_translations.md"), "\n".join(L))

    L = ["# Tableau sheets → Power BI visuals", "",
         "| Dashboard | Tableau worksheet | Tableau mark / shelves | Power BI visual | Fields |", "|---|---|---|---|---|"]
    for row in SHEET_MAP:
        L.append("| " + " | ".join(row) + " |")
    write(os.path.join(P1, "sheet_mapping.md"), "\n".join(L) + "\n")


def main():
    inv = json.load(open(os.path.join(P1, "inventory.json"), encoding="utf-8"))
    for d in (MODEL, REPORT):
        if os.path.isdir(d):
            import shutil
            shutil.rmtree(d)
    write(os.path.join(P1, "Superstore.pbip"), json.dumps({
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0", "artifacts": [{"report": {"path": "Superstore.Report"}}], "settings": {"enableAutoRecovery": True}}, indent=2))
    build_model(inv)
    build_report()
    build_docs(inv)
    n_vis = sum(len(files) for _, _, files in os.walk(os.path.join(REPORT, "definition", "pages")) if files) - 3
    print(f"wrote {MODEL} ({len([m for m in measure_rows() if m[2]])} measures), {REPORT} ({n_vis} visuals, 2 pages)")


if __name__ == "__main__":
    main()
