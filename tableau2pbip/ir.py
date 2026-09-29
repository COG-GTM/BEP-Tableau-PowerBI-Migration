from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class TableColumn:
    name: str
    datatype: str


@dataclass(frozen=True, slots=True)
class Table:
    caption: str
    hyper_table: str
    columns: list[TableColumn]


@dataclass(frozen=True, slots=True)
class Relationship:
    from_table: str
    from_col: str
    to_table: str
    to_col: str


@dataclass(frozen=True, slots=True)
class Calc:
    internal_name: str
    caption: str
    formula_raw: str
    formula_resolved: str
    datatype: str
    role: str
    type: str
    format: str = ""


@dataclass(frozen=True, slots=True)
class Parameter:
    internal_name: str
    caption: str
    datatype: str
    members: list[str]
    default: str
    format: str


@dataclass(frozen=True, slots=True)
class FieldRef:
    datasource: str
    derivation: str
    field_internal: str
    field_caption: str
    type_suffix: str
    raw: str = ""


@dataclass(frozen=True, slots=True)
class Encoding:
    kind: str
    field_ref: str


@dataclass(frozen=True, slots=True)
class Pane:
    mark_class: str
    encodings: list[Encoding]


@dataclass(frozen=True, slots=True)
class WorksheetFilter:
    filter_class: str
    column: str
    raw_xml: str


@dataclass(frozen=True, slots=True)
class Style:
    element: str
    attr: str
    value: str
    field: str


@dataclass(frozen=True, slots=True)
class Worksheet:
    name: str
    rows: str
    cols: str
    panes: list[Pane]
    filters: list[WorksheetFilter]
    styles: list[Style]


@dataclass(frozen=True, slots=True)
class TextRun:
    fontname: str
    fontsize: str
    fontcolor: str
    bold: bool
    text: str


@dataclass(frozen=True, slots=True)
class Zone:
    id: str
    type_v2: str
    name: str
    param: str
    friendly_name: str
    x: float
    y: float
    w: float
    h: float
    raw_x: int
    raw_y: int
    raw_w: int
    raw_h: int
    style: dict[str, str] = field(default_factory=dict)
    is_fixed: bool = False
    text_runs: list[TextRun] = field(default_factory=list)
    children: list[Zone] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Dashboard:
    name: str
    width: int
    height: int
    zones: list[Zone]


@dataclass(frozen=True, slots=True)
class Action:
    name: str
    source_dashboard: str
    source_worksheet: str
    command: str
    target: str


@dataclass(frozen=True, slots=True)
class Workbook:
    name: str
    tables: list[Table]
    relationships: list[Relationship]
    calcs: list[Calc]
    parameters: list[Parameter]
    worksheets: list[Worksheet]
    dashboards: list[Dashboard]
    actions: list[Action]
    start_of_week: str = "sunday"
