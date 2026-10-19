#!/usr/bin/env python3
"""Build the deterministic GDIT Tableau workbook and packaged budget extract."""

from __future__ import annotations

import hashlib
import tempfile
import zipfile
from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

import pandas as pd
from tableauhyperapi import (
    Connection,
    CreateMode,
    HyperProcess,
    Inserter,
    SqlType,
    TableDefinition,
    TableName,
    Telemetry,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
TABLEAU_DIR = Path(__file__).resolve().parent
BUDGET_XLSX = REPO_ROOT / "gdit-workforce-demo/data/finance/fy_headcount_budget.xlsx"
WORKBOOK_NAME = "GDIT Workforce & Pipeline"
WORKBOOK_FILE = TABLEAU_DIR / f"{WORKBOOK_NAME}.twb"
PACKAGE_FILE = TABLEAU_DIR / f"{WORKBOOK_NAME}.twbx"
HYPER_MEMBER = "Data/TableauTemp/GDIT-Budget.hyper"
VERSION = "18.1"
SOURCE_BUILD = "2024.1.2 (20241.24.0425.1340)"
POOLER_HOST = "aws-0-us-east-1.pooler.supabase.com"
PARAMETER_SOURCE = "Parameters"

WORKFORCE_ID = "federated.gdit_workforce_live"
PIPELINE_ID = "federated.gdit_pipeline_live"
BUDGET_ID = "federated.gdit_budget_extract"
WORKFORCE_CONNECTION = "postgres.workforce"
PIPELINE_CONNECTION = "postgres.pipeline"
BUDGET_CONNECTION = "hyper.budget"

DIVISIONS = ("Defense", "Intelligence", "Civilian", "Health")

TABLE_COLUMNS: dict[str, list[tuple[str, str]]] = {
    "workers": [
        ("worker_id", "string"), ("first_name", "string"), ("last_name", "string"),
        ("gender", "string"), ("birthdate", "date"), ("education_level", "string"),
        ("hire_date", "date"), ("term_date", "date"), ("term_type", "string"),
        ("division", "string"), ("business_unit", "string"), ("cost_center", "string"),
        ("location_state", "string"), ("location_city", "string"), ("remote_flag", "boolean"),
        ("job_family", "string"), ("job_title", "string"), ("job_level", "integer"),
        ("manager_id", "string"), ("clearance_level", "string"), ("base_salary", "real"),
        ("performance_rating", "integer"), ("last_updated", "datetime"),
    ],
    "worker_events": [
        ("event_id", "string"), ("worker_id", "string"), ("event_date", "date"),
        ("event_type", "string"), ("from_value", "string"), ("to_value", "string"),
    ],
    "training_completions": [
        ("completion_id", "string"), ("worker_id", "string"), ("course_code", "string"),
        ("assigned_date", "date"), ("due_date", "date"), ("completed_date", "date"),
        ("status", "string"), ("score", "integer"),
    ],
    "courses": [
        ("course_code", "string"), ("course_name", "string"), ("category", "string"),
        ("required", "boolean"), ("recurrence_months", "integer"),
    ],
    "v_entitlement_expanded": [("user_email", "string"), ("division", "string")],
    "opportunities": [
        ("opp_id", "string"), ("account_name", "string"), ("division", "string"),
        ("business_unit", "string"), ("stage", "string"), ("amount", "real"),
        ("probability", "integer"), ("created_date", "date"), ("close_date", "date"),
        ("contract_vehicle", "string"), ("required_clearance", "string"),
    ],
    "staffing_requests": [
        ("req_id", "string"), ("opp_id", "string"), ("division", "string"),
        ("job_family", "string"), ("clearance_required", "string"), ("headcount", "integer"),
        ("opened_date", "date"), ("needed_by", "date"), ("status", "string"),
        ("filled_date", "date"), ("filled_worker_id", "string"),
    ],
}

FIELD_ROLES = {
    "date": ("dimension", "ordinal"),
    "datetime": ("dimension", "ordinal"),
    "string": ("dimension", "nominal"),
    "boolean": ("dimension", "nominal"),
    "integer": ("measure", "quantitative"),
    "real": ("measure", "quantitative"),
}

WORKFORCE_CALCS = [
    ("user_email (v_entitlement_expanded)", "string", "dimension", "nominal", "[user_email]"),
    ("Entitlement OK", "boolean", "dimension", "nominal", "[user_email (v_entitlement_expanded)] = [View As]"),
    ("Is Active", "boolean", "dimension", "nominal", "ISNULL([term_date])"),
    ("Months Ago Term", "integer", "measure", "quantitative", "DATEDIFF('month', [term_date], DATETRUNC('month', TODAY()))"),
    ("Latest Window", "boolean", "dimension", "nominal", "[Months Ago Term] >= 1 AND [Months Ago Term] <= [Window Months]"),
    ("Prior Window", "boolean", "dimension", "nominal", "[Months Ago Term] > [Window Months] AND [Months Ago Term] <= 2*[Window Months]"),
    ("Voluntary Exit ID", "string", "dimension", "nominal", "IF [term_type]='Voluntary' THEN [worker_id] END"),
    ("Vol Exits Latest", "integer", "measure", "quantitative", "COUNTD(IF [Latest Window] THEN [Voluntary Exit ID] END)"),
    ("Vol Exits Prior", "integer", "measure", "quantitative", "COUNTD(IF [Prior Window] THEN [Voluntary Exit ID] END)"),
    ("Attrition Ratio", "real", "measure", "quantitative", "[Vol Exits Latest] / [Vol Exits Prior]"),
    ("Headcount", "integer", "measure", "quantitative", "COUNTD(IF [Is Active] THEN [worker_id] END)"),
    ("Headcount at As Of", "integer", "measure", "quantitative", "COUNTD(IF [hire_date] <= [As Of Quarter End] AND (ISNULL([term_date]) OR [term_date] > [As Of Quarter End]) THEN [worker_id] END)"),
    ("Tenure at Exit (yrs)", "real", "measure", "quantitative", "{FIXED [worker_id]: MIN(DATEDIFF('day', [hire_date], [term_date]))} / 365.25"),
    ("Division Avg Salary", "real", "measure", "quantitative", "{FIXED [division]: AVG([base_salary])}"),
    ("Salary vs Division Avg", "real", "measure", "quantitative", "AVG([base_salary]) / AVG([Division Avg Salary]) - 1"),
    ("Title Exits (INCLUDE)", "integer", "measure", "quantitative", "{INCLUDE [job_title]: [Vol Exits Latest]}"),
    ("Division Headcount", "integer", "measure", "quantitative", "{FIXED [division]: COUNTD(IF [Is Active] THEN [worker_id] END)}"),
    ("Vol Exits Monthly", "integer", "measure", "quantitative", "COUNTD([Voluntary Exit ID])"),
    ("Monthly Vol Exits YoY %", "real", "measure", "quantitative", "(SUM([Vol Exits Monthly]) - LOOKUP(SUM([Vol Exits Monthly]), -12)) / ABS(LOOKUP(SUM([Vol Exits Monthly]), -12))"),
    ("Trailing 3M Vol Exits", "integer", "measure", "quantitative", "WINDOW_SUM(COUNTD([Voluntary Exit ID]), -2, 0)"),
    ("Running Vol Exits YTD", "integer", "measure", "quantitative", "RUNNING_SUM(COUNTD([Voluntary Exit ID]))"),
    ("Title Rank", "integer", "measure", "quantitative", "RANK(COUNTD(IF [Latest Window] THEN [Voluntary Exit ID] END))"),
    ("Overdue Rate", "real", "measure", "quantitative", "SUM(IF [status] = 'Overdue' THEN 1 ELSE 0 END) / SUM(IF [status] IN ('Completed', 'Overdue') THEN 1 ELSE 0 END)"),
    ("Division Overdue Rate", "real", "measure", "quantitative", "{FIXED [division], [category]: SUM(IF [status]='Overdue' THEN 1 ELSE 0 END) / SUM(IF [status] IN ('Completed','Overdue') THEN 1 ELSE 0 END)}"),
    ("Fiscal Year", "string", "dimension", "nominal", '"FY" + RIGHT(STR(YEAR([As Of Quarter End])),2)'),
    ("Fiscal Quarter", "string", "dimension", "nominal", '"Q" + STR(DATEPART(\'quarter\',[As Of Quarter End]))'),
    ("Budget Variance %", "real", "measure", "quantitative", "[Headcount at As Of] / SUM([FY Budget (extract)].[headcount_budget]) - 1"),
]

PIPELINE_CALCS = [
    ("user_email (v_entitlement_expanded)", "string", "dimension", "nominal", "[user_email]"),
    ("Entitlement OK", "boolean", "dimension", "nominal", "[user_email (v_entitlement_expanded)] = [View As]"),
    ("Past Due Open HC", "integer", "measure", "quantitative", "IF [status]='Open' AND [needed_by] < TODAY() THEN [headcount] ELSE 0 END"),
    ("Opp Amount", "real", "measure", "quantitative", "{FIXED [opp_id]: MIN([amount])}"),
    ("Opp Requested HC", "integer", "measure", "quantitative", "{FIXED [opp_id]: SUM([headcount])}"),
    ("Opp Past Due HC", "integer", "measure", "quantitative", "{FIXED [opp_id]: SUM([Past Due Open HC])}"),
    ("Revenue at Risk", "real", "measure", "quantitative", "SUM({FIXED [opp_id]: MIN([amount]) * SUM([Past Due Open HC]) / SUM([headcount])})"),
]

WORKSHEETS = {
    "Attrition Watch": [
        ("KPI Headcount", "workforce", "KPI", ["division"], ["Headcount"]),
        ("KPI Vol Exits Latest", "workforce", "KPI", ["division"], ["Vol Exits Latest"]),
        ("KPI Vol Exits Prior", "workforce", "KPI", ["division"], ["Vol Exits Prior"]),
        ("KPI Attrition Ratio", "workforce", "KPI", ["division"], ["Attrition Ratio"]),
        ("Monthly Exits Trend", "workforce", "DualAxis", ["term_date"], ["Vol Exits Monthly", "Trailing 3M Vol Exits"]),
        ("Exits by Division", "workforce", "Bar", ["division"], ["Vol Exits Latest"]),
        ("Top Titles", "workforce", "Bar", ["job_title"], ["Vol Exits Latest", "Title Rank"]),
        ("Clearance x Family Heatmap", "workforce", "Heatmap", ["clearance_level", "job_family"], ["Vol Exits Latest"]),
        ("Exits by State", "workforce", "Map", ["location_state"], ["Vol Exits Latest"]),
        ("Running YTD Exits", "workforce", "Line", ["term_date"], ["Running Vol Exits YTD"]),
    ],
    "Staffing Risk": [
        ("Revenue at Risk by Account", "pipeline", "DualAxis", ["account_name"], ["Revenue at Risk", "Past Due Open HC"]),
        ("Past Due HC by Family x Clearance", "pipeline", "Heatmap", ["job_family", "clearance_required"], ["Past Due Open HC"]),
        ("Open Requests Detail", "pipeline", "Text", ["account_name", "opp_id", "job_family"], ["Past Due Open HC"]),
    ],
    "Training Compliance": [
        ("Overdue Rate by BU", "workforce", "Bar", ["business_unit"], ["Overdue Rate", "Division Overdue Rate"]),
        ("Overdue by Course Category", "workforce", "Bar", ["category"], ["Overdue Rate"]),
    ],
    "Headcount vs Budget": [
        ("Headcount vs Budget", "workforce", "Budget", ["division"], ["Headcount at As Of", "Budget Variance %"]),
    ],
}


def xml_tag(tag: str, attributes: dict[str, object] | None = None, parent=None):
    if parent is None:
        raise ValueError("parent is required")
    return ET.SubElement(parent, tag, {key: str(value) for key, value in (attributes or {}).items()})


def type_for_datatype(datatype: str) -> tuple[str, str]:
    return FIELD_ROLES[datatype]


def field_column(parent, name: str, datatype: str, role: str | None = None, field_type: str | None = None):
    default_role, default_type = type_for_datatype(datatype)
    attributes = {
        "name": f"[{name}]",
        "datatype": datatype,
        "role": role or default_role,
        "type": field_type or default_type,
    }
    return xml_tag("column", attributes, parent)


def calc_column(parent, name: str, datatype: str, role: str, field_type: str, formula: str, description: str | None = None):
    column = field_column(parent, name, datatype, role, field_type)
    calculation = xml_tag("calculation", {"class": "tableau", "formula": formula}, column)
    if description:
        calculation.set("comment", description)
        xml_tag("description", parent=column).text = description
    if name in {"Monthly Vol Exits YoY %", "Trailing 3M Vol Exits", "Running Vol Exits YTD", "Title Rank"}:
        table_calc_attrs = {"ordering-type": "Rows"}
        if name == "Running Vol Exits YTD":
            table_calc_attrs["restart-at"] = "Year"
        xml_tag("table-calc", table_calc_attrs, calculation)
    return column


def object_id(name: str) -> str:
    digest = hashlib.md5(name.encode("utf-8"), usedforsecurity=False).hexdigest().upper()
    return f"{name.split('.')[-1]}_{digest}"


def relation_node(parent, connection_name: str, table_name: str, columns: list[tuple[str, str]]):
    table = xml_tag(
        "relation",
        {
            "connection": connection_name,
            "name": table_name.split(".")[-1],
            "table": f"[{table_name.replace('.', '].[')}]" if "." in table_name else f"[Extract].[{table_name}]",
            "type": "table",
        },
        parent,
    )
    column_list = xml_tag("columns", parent=table)
    for index, (name, datatype) in enumerate(columns):
        xml_tag("column", {"datatype": datatype, "name": name, "ordinal": index}, column_list)
    return table


def build_logical_connection(parent, connection_name: str, objects: list[tuple[str, str, list[tuple[str, str]]]], relationships: list[tuple[str, str, str, str, bool, bool]]):
    graph = xml_tag("_.fcp.ObjectModelEncapsulateLegacy.true...object-graph", parent=parent)
    objects_node = xml_tag("objects", parent=graph)
    for label, table_name, columns in objects:
        obj = xml_tag("object", {"caption": label, "id": object_id(table_name)}, objects_node)
        props = xml_tag("properties", {"context": ""}, obj)
        relation_node(props, connection_name, table_name, columns)
    relationships_node = xml_tag("relationships", parent=graph)
    for first, second, left_field, right_field, first_unique, second_unique in relationships:
        relationship = xml_tag("relationship", parent=relationships_node)
        expression = xml_tag("expression", {"op": "="}, relationship)
        xml_tag("expression", {"op": f"[{left_field}]"}, expression)
        xml_tag("expression", {"op": f"[{right_field}]"}, expression)
        first_point = xml_tag("first-end-point", {"object-id": object_id(first)}, relationship)
        second_point = xml_tag("second-end-point", {"object-id": object_id(second)}, relationship)
        if first_unique:
            first_point.set("unique-key", "true")
        if second_unique:
            second_point.set("unique-key", "true")


def add_postgres_source(parent, caption: str, source_id: str, connection_name: str, objects, relationships):
    datasource = xml_tag(
        "datasource",
        {"caption": caption, "inline": "true", "name": source_id, "version": VERSION},
        parent,
    )
    connection = xml_tag("connection", {"class": "federated"}, datasource)
    named = xml_tag("named-connections", parent=connection)
    named_connection = xml_tag(
        "named-connection",
        {"caption": caption, "name": connection_name},
        named,
    )
    xml_tag(
        "connection",
        {
            "class": "postgres",
            "server": POOLER_HOST,
            "port": "5432",
            "dbname": "postgres",
            "username": "tableau_reader",
            "sslmode": "require",
        },
        named_connection,
    )
    build_logical_connection(connection, connection_name, objects, relationships)
    return datasource


def add_calcs(datasource, calculations, comment_view_as=False):
    for name, datatype, role, field_type, formula in calculations:
        description = "replace with USERNAME() when published" if comment_view_as and name == "Entitlement OK" else None
        calc_column(datasource, name, datatype, role, field_type, formula, description)


def add_parameters(parent, emails: list[str], as_of_date: str):
    datasource = xml_tag(
        "datasource",
        {"hasconnection": "false", "inline": "true", "name": PARAMETER_SOURCE, "version": VERSION},
        parent,
    )
    xml_tag("aliases", {"enabled": "yes"}, datasource)
    definitions = [
        ("View As", "string", "nominal", "list", '"exec@gdit-demo.example"', emails),
        ("Window Months", "integer", "quantitative", "range", "3", (1, 12, 1)),
        ("Top N Titles", "integer", "quantitative", "range", "10", (5, 25, 1)),
    ]
    for name, datatype, field_type, domain, value, domain_values in definitions:
        column = xml_tag(
            "column",
            {
                "caption": name,
                "datatype": datatype,
                "name": f"[{name}]",
                "param-domain-type": domain,
                "role": "measure",
                "type": field_type,
                "value": value,
            },
            datasource,
        )
        xml_tag("calculation", {"class": "tableau", "formula": value}, column)
        if domain == "list":
            member_list = xml_tag("members", parent=column)
            for member in domain_values:
                member_value = f'"{member}"'
                xml_tag("member", {"value": member_value}, member_list)
        else:
            minimum, maximum, granularity = domain_values
            xml_tag(
                "range",
                {"granularity": granularity, "max": maximum, "min": minimum},
                column,
            )
    column = xml_tag(
        "column",
        {
            "caption": "As Of Quarter End",
            "datatype": "date",
            "name": "[As Of Quarter End]",
            "param-domain-type": "any",
            "role": "measure",
            "type": "ordinal",
            "value": as_of_date,
        },
        datasource,
    )
    xml_tag(
        "calculation",
        {"class": "tableau", "formula": f"#{as_of_date}#"},
        column,
    )
    return datasource


def add_entitlement_filter(datasource):
    filter_node = xml_tag("filter", {"class": "categorical", "column": "[Entitlement OK]"}, datasource)
    xml_tag(
        "groupfilter",
        {"function": "member", "level": "[Entitlement OK]", "member": "true"},
        filter_node,
    )


def build_datasources(root, today: pd.Timestamp, emails: list[str]):
    sources = xml_tag("datasources", parent=root)
    workers = TABLE_COLUMNS["workers"]
    worker_events = TABLE_COLUMNS["worker_events"]
    completions = TABLE_COLUMNS["training_completions"]
    courses = TABLE_COLUMNS["courses"]
    entitlements = TABLE_COLUMNS["v_entitlement_expanded"]
    workforce = add_postgres_source(
        sources,
        "Workforce (live)",
        WORKFORCE_ID,
        WORKFORCE_CONNECTION,
        [
            ("workers", "workday.workers", workers),
            ("worker_events", "workday.worker_events", worker_events),
            ("training_completions", "oracle_lms.training_completions", completions),
            ("courses", "oracle_lms.courses", courses),
            ("v_entitlement_expanded", "security.v_entitlement_expanded", entitlements),
        ],
        [
            ("workday.workers", "workday.worker_events", "worker_id", "worker_id (worker_events)", True, False),
            ("workday.workers", "oracle_lms.training_completions", "worker_id", "worker_id (training_completions)", True, False),
            ("oracle_lms.training_completions", "oracle_lms.courses", "course_code", "course_code (courses)", False, True),
            ("workday.workers", "security.v_entitlement_expanded", "division", "division (v_entitlement_expanded)", False, False),
        ],
    )
    for table, columns in (("workers", workers), ("worker_events", worker_events), ("training_completions", completions), ("courses", courses), ("v_entitlement_expanded", entitlements)):
        seen = set()
        for name, datatype in columns:
            field_name = name
            if name == "worker_id" and table == "worker_events":
                field_name = "worker_id (worker_events)"
            elif name == "worker_id" and table == "training_completions":
                field_name = "worker_id (training_completions)"
            elif name == "course_code" and table == "courses":
                field_name = "course_code (courses)"
            elif name == "division" and table == "v_entitlement_expanded":
                field_name = "division (v_entitlement_expanded)"
            elif name == "user_email":
                field_name = "user_email"
            if field_name not in seen:
                field_column(workforce, field_name, datatype)
                seen.add(field_name)
    add_calcs(workforce, WORKFORCE_CALCS, comment_view_as=True)
    add_entitlement_filter(workforce)
    top_titles = xml_tag("group", {"name": "[Top N Titles]", "ui-builtin": "set"}, workforce)
    xml_tag(
        "groupfilter",
        {
            "function": "top",
            "level": "[job_title]",
            "measure": "[Vol Exits Latest]",
            "count": "[Top N Titles]",
            "direction": "top",
        },
        top_titles,
    )
    state_column = workforce.find("./column[@name='[location_state]']")
    if state_column is not None:
        state_column.set("semantic-role", "[State].[Name]")

    opps = TABLE_COLUMNS["opportunities"]
    requests = TABLE_COLUMNS["staffing_requests"]
    pipeline = add_postgres_source(
        sources,
        "Pipeline (live)",
        PIPELINE_ID,
        PIPELINE_CONNECTION,
        [
            ("opportunities", "salesforce.opportunities", opps),
            ("staffing_requests", "salesforce.staffing_requests", requests),
            ("v_entitlement_expanded", "security.v_entitlement_expanded", entitlements),
        ],
        [
            ("salesforce.opportunities", "salesforce.staffing_requests", "opp_id", "opp_id (staffing_requests)", True, False),
            ("salesforce.opportunities", "security.v_entitlement_expanded", "division", "division (v_entitlement_expanded)", False, False),
        ],
    )
    for table, columns in (("opportunities", opps), ("staffing_requests", requests), ("v_entitlement_expanded", entitlements)):
        seen = set()
        for name, datatype in columns:
            field_name = f"{name} ({table})" if name in {"opp_id", "division"} and table != "opportunities" else name
            if name == "division" and table == "v_entitlement_expanded":
                field_name = "division (v_entitlement_expanded)"
            if name == "opp_id" and table == "staffing_requests":
                field_name = "opp_id (staffing_requests)"
            if field_name not in seen:
                field_column(pipeline, field_name, datatype)
                seen.add(field_name)
    add_calcs(pipeline, PIPELINE_CALCS)
    add_entitlement_filter(pipeline)
    selected_accounts = xml_tag("group", {"name": "[Selected Accounts]", "ui-builtin": "set"}, pipeline)
    xml_tag("groupfilter", {"function": "union", "level": "[account_name]"}, selected_accounts)

    budget_columns = [
        ("division", "string"), ("business_unit", "string"), ("fiscal_year", "string"),
        ("fiscal_quarter", "string"), ("headcount_budget", "integer"), ("labor_budget_usd", "integer"),
    ]
    budget = xml_tag(
        "datasource",
        {"caption": "FY Budget (extract)", "inline": "true", "name": BUDGET_ID, "version": VERSION},
        sources,
    )
    connection = xml_tag("connection", {"class": "federated"}, budget)
    named = xml_tag("named-connections", parent=connection)
    named_connection = xml_tag("named-connection", {"caption": "FY Budget", "name": BUDGET_CONNECTION}, named)
    xml_tag("connection", {"class": "hyper", "dbname": HYPER_MEMBER}, named_connection)
    budget_objects = [("FY Headcount Budget", "Extract.FY Headcount Budget", budget_columns)]
    build_logical_connection(connection, BUDGET_CONNECTION, budget_objects, [])
    for name, datatype in budget_columns:
        field_column(budget, name, datatype)

    params = add_parameters(sources, emails, today.strftime("%Y-%m-%d"))
    return {WORKFORCE_ID: workforce, PIPELINE_ID: pipeline, BUDGET_ID: budget, PARAMETER_SOURCE: params}


TABLE_CALCS = {"Monthly Vol Exits YoY %", "Trailing 3M Vol Exits", "Running Vol Exits YTD", "Title Rank"}


def instance_parts(field: str):
    if field == "term_date":
        return "ordinal", "Month", "mth", "ok"
    if field in {
        "Revenue at Risk", "Headcount at As Of", "Headcount", "Vol Exits Latest",
        "Vol Exits Prior", "Attrition Ratio", "Past Due Open HC", "Overdue Rate",
        "Division Overdue Rate", "Budget Variance %", "Vol Exits Monthly",
        "Trailing 3M Vol Exits", "Running Vol Exits YTD", "Title Rank",
        "headcount_budget", "labor_budget_usd",
    }:
        return "quantitative", "User", "usr", "qk"
    return "nominal", "None", "none", "nk"


def column_instance(parent, field: str):
    field_type, derivation, short_name, suffix = instance_parts(field)
    instance_name = f"[{short_name}:{field}:{suffix}]"
    instance = xml_tag(
        "column-instance",
        {
            "column": f"[{field}]",
            "derivation": derivation,
            "name": instance_name,
            "pivot": "key",
            "type": field_type,
        },
        parent,
    )
    if field in TABLE_CALCS:
        attrs = {"ordering-type": "Rows"}
        if field == "Running Vol Exits YTD":
            attrs["restart-at"] = "Year"
        xml_tag("table-calc", attrs, instance)
    return instance_name


def make_worksheet(parent, name: str, kind: str, chart: str, dimensions: list[str], measures: list[str], source_fields):
    worksheet = xml_tag("worksheet", {"name": name}, parent)
    table = xml_tag("table", parent=worksheet)
    view = xml_tag("view", parent=table)
    source_id = PIPELINE_ID if kind == "pipeline" else WORKFORCE_ID
    caption = "Pipeline (live)" if kind == "pipeline" else "Workforce (live)"
    data_sources = xml_tag("datasources", parent=view)
    xml_tag("datasource", {"caption": caption, "name": source_id}, data_sources)
    if chart == "Budget":
        xml_tag("datasource", {"caption": "FY Budget (extract)", "name": BUDGET_ID}, data_sources)

    all_fields = list(dict.fromkeys(dimensions + measures))
    if chart == "Budget":
        all_fields.extend(["Fiscal Year", "Fiscal Quarter"])
    source_ids = [source_id, BUDGET_ID] if chart == "Budget" else [source_id]
    instance_names = {}
    for dep_id in source_ids:
        dependencies = xml_tag("datasource-dependencies", {"datasource": dep_id}, view)
        dep_fields = all_fields if dep_id == source_id else ["division", "fiscal_year", "fiscal_quarter", "headcount_budget"]
        if dep_id == BUDGET_ID:
            dep_fields += ["labor_budget_usd"]
        for field in dict.fromkeys(dep_fields):
            field_xml = source_fields[dep_id].find(f"./column[@name='[{field}]']")
            if field_xml is None:
                raise ValueError(f"Missing {field!r} in datasource {dep_id}")
            dependencies.append(deepcopy(field_xml))
            instance_names[(dep_id, field)] = column_instance(dependencies, field)
        if dep_id == BUDGET_ID:
            for field in ("division", "fiscal_year", "fiscal_quarter"):
                xml_tag(
                    "link",
                    {
                        "source": f"[{WORKFORCE_ID}].[{ {'fiscal_year': 'Fiscal Year', 'fiscal_quarter': 'Fiscal Quarter'}.get(field, field) }]",
                        "target": f"[{BUDGET_ID}].[{field}]",
                    },
                    dependencies,
                )

    if name == "Monthly Exits Trend":
        xml_tag("filter", {"class": "relative-date", "column": "[term_date]", "periods": "36", "range": "last"}, view)
    if name == "Top Titles":
        xml_tag(
            "filter",
            {
                "class": "quantitative",
                "column": "[Title Rank]",
                "expression": "[Title Rank] <= [Top N Titles]",
            },
            view,
        )
    if name == "Overdue Rate by BU":
        filter_node = xml_tag("filter", {"class": "categorical", "column": "[category]"}, view)
        group = xml_tag("groupfilter", {"function": "union"}, filter_node)
        xml_tag("groupfilter", {"function": "member", "level": "[category]", "member": '"Security"'}, group)
    if name == "Open Requests Detail":
        xml_tag("filter", {"class": "set", "column": "[Selected Accounts]"}, view)

    cols = xml_tag("cols", parent=view)
    rows = xml_tag("rows", parent=view)
    if dimensions:
        cols.text = " ".join(f"[{source_id}].{instance_names[(source_id, field)]}" for field in dimensions)
    if measures:
        rows.text = " ".join(f"[{source_id}].{instance_names[(source_id, field)]}" for field in measures)

    pane_group = xml_tag("panes", parent=view)
    dual = chart == "DualAxis"
    pane_measures = measures if dual else measures[:1]
    for index, measure in enumerate(pane_measures):
        pane = xml_tag("pane", {"selection-relaxation-option": "selection-relaxation-allow"}, pane_group)
        xml_tag("view", parent=pane)
        if chart == "Heatmap":
            mark_name = "Square"
        elif chart == "Map":
            mark_name = "Map"
        elif chart == "Line" or (dual and index == 1 and name != "Revenue at Risk by Account"):
            mark_name = "Line"
        elif dual and index == 1:
            mark_name = "Circle"
        elif chart == "Text":
            mark_name = "Text"
        else:
            mark_name = "Bar"
        xml_tag("mark", {"class": mark_name}, pane)
        encodings = xml_tag("encodings", parent=pane)
        color_field = "Budget Variance %" if chart == "Budget" else dimensions[0] if dimensions else ""
        if color_field:
            color_id = source_id if color_field in instance_names and (source_id, color_field) in instance_names else source_id
            color_instance = instance_names.get((color_id, color_field), f"[usr:{color_field}:qk]" if color_field == "Budget Variance %" else f"[none:{color_field}:nk]")
            xml_tag("color", {"column": f"[{color_id}].{color_instance}"}, encodings)
        xml_tag("text", {"column": f"[{source_id}].{instance_names[(source_id, measure)]}"}, encodings)
        xml_tag("axis", {"name": measure, "synchronized": "false" if dual else "true"}, pane)
    if chart == "Budget":
        xml_tag("reference-line", {"field": "[FY Budget (extract)].[headcount_budget]"}, view)
    if name == "Overdue Rate by BU":
        xml_tag("reference-line", {"field": "[Division Overdue Rate]"}, view)
    return worksheet


def add_actions(parent):
    actions = xml_tag("actions", parent=parent)
    action = xml_tag("action", {"caption": "Filter by Division", "name": "[Action_Division_Filter]"}, actions)
    xml_tag("activation", {"auto-clear": "true", "type": "on-select"}, action)
    xml_tag("source", {"dashboard": "Attrition Watch", "type": "sheet", "worksheet": "Exits by Division"}, action)
    command = xml_tag("command", {"command": "tsc:tsl-filter"}, action)
    xml_tag("param", {"name": "special-fields", "value": "all"}, command)
    xml_tag("param", {"name": "target", "value": "Attrition Watch"}, command)
    action = xml_tag("action", {"caption": "Highlight Job Family", "name": "[Action_Job_Family_Highlight]"}, actions)
    xml_tag("activation", {"auto-clear": "true", "type": "on-select"}, action)
    xml_tag("source", {"dashboard": "Attrition Watch", "type": "sheet", "worksheet": "Clearance x Family Heatmap"}, action)
    command = xml_tag("command", {"command": "tsc:brush"}, action)
    xml_tag("param", {"name": "special-fields", "value": "all"}, command)
    xml_tag("param", {"name": "target", "value": "Attrition Watch"}, command)
    action = xml_tag("action", {"caption": "Select Accounts", "name": "[Action_Selected_Accounts]"}, actions)
    xml_tag("activation", {"auto-clear": "true", "type": "on-select"}, action)
    xml_tag("source", {"dashboard": "Staffing Risk", "type": "sheet", "worksheet": "Revenue at Risk by Account"}, action)
    command = xml_tag("command", {"command": "tsc:tsl-set"}, action)
    xml_tag("param", {"name": "set", "value": "[Selected Accounts]"}, command)
    xml_tag("param", {"name": "target", "value": "Staffing Risk"}, command)


def add_dashboard(parent, name: str, worksheets: list[str], controls: list[str] = ()):
    dashboard = xml_tag("dashboard", {"name": name}, parent)
    xml_tag("style", parent=dashboard)
    xml_tag(
        "size",
        {
            "maxheight": "900",
            "maxwidth": "1600",
            "minheight": "900",
            "minwidth": "1600",
            "preset-index": "1",
            "sizing-mode": "fixed",
        },
        dashboard,
    )
    zones = xml_tag("zones", parent=dashboard)
    root_zone = xml_tag("zone", {"h": "100000", "id": "1", "type-v2": "layout-basic", "w": "100000", "x": "0", "y": "0"}, zones)
    if name == "Attrition Watch":
        kpis = worksheets[:4]
        rest = worksheets[4:]
        positions = [(index * 18000, 0, 18000, 14000) for index in range(4)]
        positions.extend([(0, 14000, 65000, 36000), (65000, 14000, 35000, 36000)])
        positions.extend([(0, 50000, 33000, 50000), (33000, 50000, 34000, 50000), (67000, 50000, 33000, 50000)])
        worksheet_positions = list(zip(kpis + rest, positions))
        control_positions = [(72000 + i * 9300, 0, 9300, 14000) for i in range(len(controls))]
    elif name == "Staffing Risk":
        worksheet_positions = list(zip(worksheets, [(0, 0, 65000, 75000), (65000, 0, 35000, 75000), (0, 75000, 100000, 25000)]))
        control_positions = [(85000, 0, 15000, 10000) for _ in controls]
    elif name == "Training Compliance":
        worksheet_positions = list(zip(worksheets, [(0, 0, 50000, 100000), (50000, 0, 50000, 100000)]))
        control_positions = []
    else:
        worksheet_positions = list(zip(worksheets, [(0, 0, 100000, 100000)]))
        control_positions = [(82000, 0, 18000, 10000) for _ in controls]
    for index, (sheet, (x, y, width, height)) in enumerate(worksheet_positions):
        xml_tag(
            "zone",
            {
                "h": str(height),
                "id": str(index + 2),
                "name": sheet,
                "type-v2": "worksheet",
                "w": str(width),
                "x": str(x),
                "y": str(y),
            },
            root_zone,
        )
    for index, (control, (x, y, width, height)) in enumerate(zip(controls, control_positions), start=len(worksheet_positions) + 2):
        xml_tag(
            "zone",
            {
                "h": str(height),
                "id": str(index),
                "name": f"[{control}]",
                "type-v2": "parameter-control",
                "w": str(width),
                "x": str(x),
                "y": str(y),
            },
            root_zone,
        )
    data_sources = xml_tag("datasources", parent=dashboard)
    for source_id, caption in ((WORKFORCE_ID, "Workforce (live)"), (PIPELINE_ID, "Pipeline (live)"), (BUDGET_ID, "FY Budget (extract)")):
        xml_tag("datasource", {"caption": caption, "name": source_id}, data_sources)
    return dashboard


def write_hyper(destination: Path):
    frame = pd.read_excel(BUDGET_XLSX)
    table_definition = TableDefinition(
        table_name=TableName("Extract", "FY Headcount Budget"),
        columns=[
            TableDefinition.Column("division", SqlType.text()),
            TableDefinition.Column("business_unit", SqlType.text()),
            TableDefinition.Column("fiscal_year", SqlType.text()),
            TableDefinition.Column("fiscal_quarter", SqlType.text()),
            TableDefinition.Column("headcount_budget", SqlType.int()),
            TableDefinition.Column("labor_budget_usd", SqlType.big_int()),
        ],
    )
    rows = [
        (
            str(row.division),
            str(row.business_unit),
            str(row.fiscal_year),
            str(row.fiscal_quarter),
            int(row.headcount_budget),
            int(row.labor_budget_usd),
        )
        for row in frame.itertuples(index=False)
    ]
    with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        with Connection(
            endpoint=hyper.endpoint,
            database=str(destination),
            create_mode=CreateMode.CREATE_AND_REPLACE,
        ) as connection:
            connection.catalog.create_schema("Extract")
            connection.catalog.create_table(table_definition)
            with Inserter(connection, table_definition) as inserter:
                inserter.add_rows(rows)
                inserter.execute()
        with Connection(endpoint=hyper.endpoint, database=str(destination)) as connection:
            actual = connection.execute_list_query(
                'SELECT COUNT(*), SUM("headcount_budget"), SUM("labor_budget_usd") '
                'FROM "Extract"."FY Headcount Budget"'
            )[0]
        expected = (
            len(frame),
            int(frame["headcount_budget"].sum()),
            int(frame["labor_budget_usd"].sum()),
        )
        observed = tuple(int(value) for value in actual)
        if observed != expected:
            raise ValueError(f"Budget Hyper mismatch: expected {expected}, got {observed}")
    return expected


def build_twb(today: pd.Timestamp, emails: list[str]) -> bytes:
    template_path = REPO_ROOT / "projects/hr-dashboard-project/HR Dashboard.twbx"
    with zipfile.ZipFile(template_path) as package:
        template_name = next(name for name in package.namelist() if name.endswith(".twb"))
        template = ET.fromstring(package.read(template_name))
    root = ET.Element(
        "workbook",
        {
            "original-version": VERSION,
            "source-build": SOURCE_BUILD,
            "source-platform": "win",
            "version": VERSION,
        },
    )
    for tag in ("document-format-change-manifest", "preferences", "style"):
        element = template.find(tag)
        if element is not None:
            root.append(deepcopy(element))
    xml_tag(
        "repository-location",
        {"id": "GDITWorkforcePipeline", "path": "/workbooks", "revision": ""},
        root,
    )
    all_sources = build_datasources(root, today, emails)
    add_actions(root)
    worksheets_element = xml_tag("worksheets", parent=root)
    all_worksheets = []
    for dashboard_name, specs in WORKSHEETS.items():
        for sheet_name, kind, chart, dimensions, measures in specs:
            make_worksheet(worksheets_element, sheet_name, kind, chart, dimensions, measures, all_sources)
            all_worksheets.append(sheet_name)
    dashboards = xml_tag("dashboards", parent=root)
    add_dashboard(
        dashboards,
        "Attrition Watch",
        [spec[0] for spec in WORKSHEETS["Attrition Watch"] if spec[0] != "Running YTD Exits"],
        ["View As", "Window Months", "Top N Titles"],
    )
    add_dashboard(
        dashboards,
        "Staffing Risk",
        [spec[0] for spec in WORKSHEETS["Staffing Risk"]],
        ["View As"],
    )
    add_dashboard(dashboards, "Training Compliance", [spec[0] for spec in WORKSHEETS["Training Compliance"]])
    add_dashboard(
        dashboards,
        "Headcount vs Budget",
        [spec[0] for spec in WORKSHEETS["Headcount vs Budget"]],
        ["As Of Quarter End"],
    )
    windows = xml_tag("windows", parent=root)
    for sheet_name in all_worksheets:
        xml_tag("window", {"class": "worksheet", "name": sheet_name}, windows)
    for dashboard_name in WORKSHEETS:
        xml_tag("window", {"class": "dashboard", "name": dashboard_name}, windows)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def main():
    workforce_path = REPO_ROOT / "gdit-workforce-demo/data/out/workday.workers.csv"
    workers = pd.read_csv(workforce_path, parse_dates=["last_updated"])
    today = workers["last_updated"].max().normalize()
    quarter_start_month = ((today.month - 1) // 3) * 3 + 1
    current_quarter_start = pd.Timestamp(today.year, quarter_start_month, 1)
    as_of = current_quarter_start - pd.Timedelta(days=1)
    entitlements = pd.read_csv(REPO_ROOT / "gdit-workforce-demo/data/out/security.entitlements.csv")
    emails = sorted(entitlements["user_email"].drop_duplicates().tolist())
    if len(emails) != 4:
        raise ValueError(f"Expected 4 entitlement emails, found {len(emails)}")
    emails = ["exec@gdit-demo.example"] + [email for email in emails if email != "exec@gdit-demo.example"]
    TABLEAU_DIR.mkdir(parents=True, exist_ok=True)
    workbook_bytes = build_twb(as_of, emails)
    with tempfile.TemporaryDirectory(prefix="gdit-tableau-") as temp_dir:
        hyper_path = Path(temp_dir) / "GDIT-Budget.hyper"
        budget_totals = write_hyper(hyper_path)
        WORKBOOK_FILE.write_bytes(workbook_bytes)
        entries = [
            (f"{WORKBOOK_NAME}.twb", workbook_bytes),
            (HYPER_MEMBER, hyper_path.read_bytes()),
        ]
        with zipfile.ZipFile(PACKAGE_FILE, "w") as archive:
            for name, payload in entries:
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                archive.writestr(info, payload, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        with zipfile.ZipFile(PACKAGE_FILE) as archive:
            infos = archive.infolist()
            expected_names = [f"{WORKBOOK_NAME}.twb", HYPER_MEMBER]
            if archive.namelist() != expected_names:
                raise ValueError(f"Unexpected TWBX entry order: {archive.namelist()}")
            if any(info.date_time != (1980, 1, 1, 0, 0, 0) for info in infos):
                raise ValueError("TWBX entry timestamps are not normalized")
    print(f"Workbook: {WORKBOOK_FILE}")
    print(f"Package: {PACKAGE_FILE}")
    print(f"Default As Of Quarter End: {as_of.date().isoformat()}")
    print(f"Included budget extract: {HYPER_MEMBER}")
    print(f"Budget extract validation: rows={budget_totals[0]}, headcount_sum={budget_totals[1]}, labor_budget_sum={budget_totals[2]}")


if __name__ == "__main__":
    main()
