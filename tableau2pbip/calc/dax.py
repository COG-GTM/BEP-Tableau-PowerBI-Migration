from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable

from tableau2pbip.calc.ast import (
    Binary,
    Call,
    Case,
    Conditional,
    Expr,
    Field,
    Literal,
    Lod,
    ParameterRef,
    Unary,
)
from tableau2pbip.calc.parser import ParseError, parse
from tableau2pbip.ir import Calc, FieldRef, Workbook
from tableau2pbip.overrides import ModelOverrides
from tableau2pbip.parse import decode_field_ref


_AGGREGATES = {"SUM", "AVG", "MIN", "MAX", "COUNT", "COUNTD", "ATTR"}
_TABLE_CALCS = {
    "INDEX",
    "LOOKUP",
    "TOTAL",
    "FIRST",
    "LAST",
    "SIZE",
}
_DATE_PARTS = {
    "YEAR": "YEAR",
    "MONTH": "MONTH",
    "DAY": "DAY",
    "QUARTER": "QUARTER",
}
_FIELD_PATTERN = re.compile(r"\[[^\]]+\]\.\[[^\]]+\]")
_BRACKET_PATTERN = re.compile(r"\[([^\]]+)\]")


class DaxUnsupportedError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CalcTranslation:
    classification: str
    status: str
    dax: str | None
    is_calculated_column: bool
    reason: str = ""
    semantics_approximated: bool = False


@dataclass(frozen=True, slots=True)
class AutoMeasure:
    name: str
    dax: str
    tableau_ref: str
    display_folder: str = "Auto measures"


def _function_names(expression: Expr) -> Iterable[str]:
    if isinstance(expression, Call):
        yield expression.name.upper()
        for argument in expression.arguments:
            yield from _function_names(argument)
    elif isinstance(expression, Unary):
        yield from _function_names(expression.operand)
    elif isinstance(expression, Binary):
        yield from _function_names(expression.left)
        yield from _function_names(expression.right)
    elif isinstance(expression, Conditional):
        for condition, result in expression.branches:
            yield from _function_names(condition)
            yield from _function_names(result)
        if expression.otherwise is not None:
            yield from _function_names(expression.otherwise)
    elif isinstance(expression, Case):
        yield from _function_names(expression.value)
        for value, result in expression.branches:
            yield from _function_names(value)
            yield from _function_names(result)
        if expression.otherwise is not None:
            yield from _function_names(expression.otherwise)
    elif isinstance(expression, Lod):
        yield from _function_names(expression.expression)


def classify_expression(expression: Expr) -> str:
    functions = {name.upper() for name in _function_names(expression)}
    if any(
        name.startswith("WINDOW_")
        or name.startswith("RUNNING_")
        or name.startswith("RANK")
        or name in _TABLE_CALCS
        for name in functions
    ):
        return "table_calc"
    if any(isinstance(node, Lod) for node in _walk_expr(expression)):
        return "lod"
    if functions.intersection(_AGGREGATES):
        return "aggregate"
    return "row"


def _walk_expr(expression: Expr) -> Iterable[Expr]:
    yield expression
    if isinstance(expression, Call):
        for argument in expression.arguments:
            yield from _walk_expr(argument)
    elif isinstance(expression, Unary):
        yield from _walk_expr(expression.operand)
    elif isinstance(expression, Binary):
        yield from _walk_expr(expression.left)
        yield from _walk_expr(expression.right)
    elif isinstance(expression, Conditional):
        for condition, result in expression.branches:
            yield from _walk_expr(condition)
            yield from _walk_expr(result)
        if expression.otherwise is not None:
            yield from _walk_expr(expression.otherwise)
    elif isinstance(expression, Case):
        yield from _walk_expr(expression.value)
        for value, result in expression.branches:
            yield from _walk_expr(value)
            yield from _walk_expr(result)
        if expression.otherwise is not None:
            yield from _walk_expr(expression.otherwise)
    elif isinstance(expression, Lod):
        yield from _walk_expr(expression.expression)


def _quote(value: str) -> str:
    return value.replace("'", "''")


def _dax_column(table: str, column: str) -> str:
    return f"'{_quote(table)}'[{column}]"


def _is_number(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


class CalculationCompiler:
    def __init__(self, workbook: Workbook) -> None:
        self.workbook = workbook
        self.calcs_by_internal = {calc.internal_name: calc for calc in workbook.calcs}
        self.calcs_by_caption = {calc.caption: calc for calc in workbook.calcs}
        self.parameters_by_internal = {
            parameter.internal_name: parameter for parameter in workbook.parameters
        }
        self.parameters_by_caption = {
            parameter.caption: parameter for parameter in workbook.parameters
        }
        self.column_owner: dict[str, tuple[str, str]] = {}
        self.caption_to_column: dict[str, tuple[str, str]] = {}
        self._compiled: dict[str, CalcTranslation] = {}
        for table in workbook.tables:
            for column in table.columns:
                key = column.name.casefold()
                value = (table.caption, column.name)
                if key not in self.column_owner or table.caption.casefold() == workbook.fact_table.casefold():
                    self.column_owner[key] = value
                self.caption_to_column.setdefault(column.name, value)
        for calc in workbook.calcs:
            self.caption_to_column.setdefault(
                calc.caption, (workbook.fact_table, calc.caption)
            )

    def compile(self, calc: Calc) -> CalcTranslation:
        return self._compile(calc, frozenset())

    def _compile(
        self, calc: Calc, visiting: frozenset[str]
    ) -> CalcTranslation:
        cached = self._compiled.get(calc.internal_name)
        if cached is not None:
            return cached
        if calc.internal_name in visiting:
            return CalcTranslation(
                "unsupported",
                "unsupported",
                None,
                False,
                f"Recursive calculation reference {calc.caption}",
            )
        try:
            expression = parse(calc.formula_raw)
        except (ParseError, ValueError) as error:
            return CalcTranslation("unsupported", "unsupported", None, False, str(error))
        classification = self._effective_classification(
            expression, frozenset({calc.internal_name})
        )
        next_visiting = visiting | {calc.internal_name}
        for node in _walk_expr(expression):
            if not isinstance(node, Field):
                continue
            dependency = self._resolve_calc(node.name)
            if dependency is None:
                continue
            dependency_translation = self._compile(dependency, next_visiting)
            if dependency_translation.status != "supported":
                result = CalcTranslation(
                    classification,
                    "unsupported",
                    None,
                    False,
                    f"depends on {dependency.caption}",
                )
                self._compiled[calc.internal_name] = result
                return result
        if classification == "table_calc":
            functions = {name.upper() for name in _function_names(expression)}
            table_functions = {
                name
                for name in functions
                if name in _TABLE_CALCS
                or name.startswith(("WINDOW_", "RUNNING_", "RANK"))
            }
            if table_functions == {"TOTAL"}:
                try:
                    dax = self._emit(expression, row_context=False)
                except (DaxUnsupportedError, IndexError) as error:
                    result = CalcTranslation(
                        "table_calc", "unsupported", None, False, str(error)
                    )
                else:
                    result = CalcTranslation(
                        "table_calc",
                        "supported",
                        dax,
                        False,
                        semantics_approximated=True,
                    )
                self._compiled[calc.internal_name] = result
                return result
            result = CalcTranslation("table_calc", "table_calc", None, False)
            self._compiled[calc.internal_name] = result
            return result
        if classification == "lod":
            lod = next(
                (node for node in _walk_expr(expression) if isinstance(node, Lod)),
                None,
            )
            if lod is not None and lod.kind == "fixed":
                if calc.role.casefold() == "dimension" or not self._is_fixed_aggregated(calc):
                    result = CalcTranslation("lod", "needs_override", None, False)
                    self._compiled[calc.internal_name] = result
                    return result
        try:
            dax = self._emit(expression, row_context=False)
        except (DaxUnsupportedError, IndexError) as error:
            result = CalcTranslation(
                classification, "unsupported", None, False, str(error)
            )
            self._compiled[calc.internal_name] = result
            return result
        if classification == "lod":
            result = CalcTranslation(
                "lod", "supported", dax, False, semantics_approximated=True
            )
            self._compiled[calc.internal_name] = result
            return result
        has_parameter = self._uses_parameter(
            expression, frozenset({calc.internal_name})
        )
        calculated_column = classification == "row" and not has_parameter
        result = CalcTranslation(
            classification,
            "supported",
            dax,
            calculated_column,
        )
        self._compiled[calc.internal_name] = result
        return result

    def compile_all(self) -> dict[str, CalcTranslation]:
        return {calc.internal_name: self.compile(calc) for calc in self.workbook.calcs}

    def emit_aggregation(self, reference: FieldRef, raw_ref: str) -> AutoMeasure | None:
        derivation = reference.derivation.casefold()
        if derivation == "attr" or derivation == "usr":
            return None
        date_part = self._date_part(reference)
        if date_part is not None:
            field = self._resolve_column(reference.field_internal)
            if field is None:
                return None
            table, column = field
            function, suffix = date_part
            name = f"{column} ({suffix})"
            expression = f"{function}({_dax_column(table, column)})"
            if function == "WEEKNUM":
                expression = (
                    f"WEEKNUM({_dax_column(table, column)}, "
                    f"{self._weeknum_return_type()})"
                )
            return AutoMeasure(name, expression, raw_ref, "Tableau date parts")

        aggregation = {
            "sum": "SUM",
            "avg": "AVG",
            "min": "MIN",
            "max": "MAX",
            "cnt": "COUNT",
            "ctd": "COUNTD",
            "count": "COUNT",
            "countd": "COUNTD",
            "mn": "MIN",
        }.get(derivation)
        if aggregation is None:
            return None
        caption = reference.field_caption
        name = {
            "SUM": caption,
            "COUNTD": f"CNTD {caption}",
            "AVG": f"AVG {caption}",
            "MIN": f"MIN {caption}",
            "MAX": f"MAX {caption}",
            "COUNT": f"COUNT {caption}",
        }[aggregation]
        calc = self._resolve_calc(reference.field_internal)
        if calc is not None:
            calc_expression = self._parse_calc(calc)
            if aggregation in {"COUNTD", "COUNT"} and self._contains_parameter(calc_expression):
                row_expression = self._emit(calc_expression, row_context=True)
                dax = (
                    f"COUNTROWS(FILTER(DISTINCT(SELECTCOLUMNS('{_quote(self.workbook.fact_table)}', "
                    f"\"__v\", {row_expression})), NOT ISBLANK([__v])))"
                )
            elif self._contains_parameter(calc_expression):
                dax = self._iterator(aggregation, self._emit(calc_expression, row_context=True))
            elif aggregation == "COUNTD":
                dax = f"DISTINCTCOUNT({_dax_column(self.workbook.fact_table, calc.caption)})"
            else:
                dax = self._aggregate_expression(
                    aggregation, _dax_column(self.workbook.fact_table, calc.caption)
                )
        else:
            column = self._resolve_column(reference.field_internal)
            if column is None:
                return None
            table, column_name = column
            field_expression = _dax_column(table, column_name)
            dax = self._aggregate_expression(aggregation, field_expression)
        return AutoMeasure(name, dax, raw_ref)

    def _aggregate_expression(self, aggregation: str, expression: str) -> str:
        if aggregation == "SUM":
            return f"SUM({expression})"
        if aggregation == "AVG":
            return f"AVERAGE({expression})"
        if aggregation == "MIN":
            return f"MIN({expression})"
        if aggregation == "MAX":
            return f"MAX({expression})"
        if aggregation == "COUNT":
            return f"COUNT({expression})"
        if aggregation == "COUNTD":
            return f"DISTINCTCOUNT({expression})"
        raise DaxUnsupportedError(f"Unsupported aggregation {aggregation}")

    def _iterator(self, aggregation: str, expression: str) -> str:
        iterator = {
            "SUM": "SUMX",
            "AVG": "AVERAGEX",
            "MIN": "MINX",
            "MAX": "MAXX",
            "COUNT": "COUNTX",
        }.get(aggregation)
        if iterator is None:
            if aggregation == "COUNTD":
                return (
                    f"COUNTROWS(FILTER(DISTINCT(SELECTCOLUMNS('{_quote(self.workbook.fact_table)}', "
                    f"\"__v\", {expression})), NOT ISBLANK([__v])))"
                )
            raise DaxUnsupportedError(f"Unsupported iterator aggregation {aggregation}")
        return f"{iterator}('{_quote(self.workbook.fact_table)}', {expression})"

    def _date_part(self, reference: FieldRef) -> tuple[str, str] | None:
        value = reference.derivation.casefold()
        normalized = value[1:] if value.startswith("t") else value
        parts = {
            "mn": ("MONTH", "Month"),
            "wk": ("WEEKNUM", "Week"),
            "yr": ("YEAR", "Year"),
            "qr": ("QUARTER", "Quarter"),
            "dy": ("DAY", "Day"),
        }
        field = self._resolve_column(reference.field_internal)
        if normalized in parts and field is not None:
            column_type = next(
                (
                    item.datatype.casefold()
                    for table in self.workbook.tables
                    if table.caption == field[0]
                    for item in table.columns
                    if item.name == field[1]
                ),
                "",
            )
            if "date" in column_type:
                return parts[normalized]
        return None

    def _weeknum_return_type(self) -> int:
        return 2 if self.workbook.start_of_week.casefold() == "monday" else 1

    def _resolve_calc(self, name: str) -> Calc | None:
        internal = name.strip("[]")
        if internal in self.calcs_by_internal:
            return self.calcs_by_internal[internal]
        return self.calcs_by_caption.get(internal)

    def _resolve_column(self, name: str) -> tuple[str, str] | None:
        key = name.strip("[]").casefold()
        if key in self.column_owner:
            return self.column_owner[key]
        if key in self.calcs_by_internal:
            return (self.workbook.fact_table, self.calcs_by_internal[key].caption)
        calc = self.calcs_by_caption.get(name)
        return (self.workbook.fact_table, calc.caption) if calc is not None else None

    def _effective_classification(
        self, expression: Expr, visiting: frozenset[str] = frozenset()
    ) -> str:
        local = classify_expression(expression)
        if local in {"table_calc", "lod", "aggregate"}:
            return local
        for node in _walk_expr(expression):
            if not isinstance(node, Field):
                continue
            calc = self._resolve_calc(node.name)
            if calc is None or calc.internal_name in visiting:
                continue
            try:
                nested = parse(calc.formula_raw)
            except (ParseError, ValueError):
                continue
            nested_class = self._effective_classification(
                nested, visiting | {calc.internal_name}
            )
            if nested_class in {"table_calc", "lod", "aggregate"}:
                return nested_class
        return "row"

    def _uses_parameter(
        self, expression: Expr, visiting: frozenset[str] = frozenset()
    ) -> bool:
        if any(isinstance(node, ParameterRef) for node in _walk_expr(expression)):
            return True
        for node in _walk_expr(expression):
            if not isinstance(node, Field):
                continue
            calc = self._resolve_calc(node.name)
            if calc is None or calc.internal_name in visiting:
                continue
            try:
                nested = parse(calc.formula_raw)
            except (ParseError, ValueError):
                continue
            if self._uses_parameter(nested, visiting | {calc.internal_name}):
                return True
        return False

    def _parse_calc(self, calc: Calc) -> Expr:
        return parse(calc.formula_raw)

    def _contains_parameter(self, expression: Expr) -> bool:
        return self._uses_parameter(expression)

    def _is_fixed_aggregated(self, calc: Calc) -> bool:
        for worksheet in self.workbook.worksheets:
            raw_values = [worksheet.rows, worksheet.cols]
            raw_values.extend(
                encoding.field_ref
                for pane in worksheet.panes
                for encoding in pane.encodings
            )
            for raw in raw_values:
                for reference in _FIELD_PATTERN.findall(raw):
                    decoded = decode_field_ref(reference)
                    if decoded.field_internal in {
                        calc.internal_name,
                        calc.caption,
                    } and decoded.derivation.casefold() in {
                        "sum",
                        "avg",
                        "min",
                        "max",
                        "cnt",
                        "ctd",
                    }:
                        return True
        return False

    def _emit(
        self,
        expression: Expr,
        row_context: bool,
        resolving: frozenset[str] = frozenset(),
    ) -> str:
        if isinstance(expression, Literal):
            if expression.kind == "string":
                return f'"{expression.value.replace(chr(34), chr(34) * 2)}"'
            if expression.kind == "date":
                return self._date_literal(expression.value)
            if expression.kind == "bool":
                return "TRUE()" if expression.value == "true" else "FALSE()"
            if expression.kind == "blank":
                return "BLANK()"
            return expression.value
        if isinstance(expression, ParameterRef):
            parameter = self.parameters_by_caption.get(expression.name)
            if parameter is None:
                parameter = self.parameters_by_internal.get(expression.name)
            if parameter is None:
                raise DaxUnsupportedError(f"Unknown parameter {expression.name!r}")
            default = parameter.default
            if parameter.datatype.casefold() in {"string", "text"}:
                default = f'"{default}"'
            return (
                f"SELECTEDVALUE('{_quote(parameter.caption)}'"
                f"[{parameter.caption}], {default})"
            )
        if isinstance(expression, Field):
            if "." in expression.name and expression.name.casefold().startswith("parameters."):
                name = expression.name.split(".", 1)[1]
                return self._emit(ParameterRef(name), row_context, resolving)
            calc = self._resolve_calc(expression.name)
            if calc is not None:
                if calc.caption in resolving:
                    raise DaxUnsupportedError(f"Recursive calculation reference {calc.caption}")
                calc_expr = self._parse_calc(calc)
                calc_class = self._effective_classification(
                    calc_expr, frozenset({calc.internal_name})
                )
                calc_translation = self._compiled.get(calc.internal_name)
                if calc_class == "aggregate" or (
                    calc_class == "table_calc"
                    and calc_translation is not None
                    and calc_translation.status == "supported"
                    and not calc_translation.is_calculated_column
                ):
                    return f"[{calc.caption}]"
                if self._contains_parameter(calc_expr):
                    return self._emit(
                        calc_expr,
                        row_context,
                        resolving | {calc.caption},
                    )
                return _dax_column(self.workbook.fact_table, calc.caption)
            column = self._resolve_column(expression.name)
            if column is None:
                raise DaxUnsupportedError(f"Unknown field {expression.name!r}")
            table, name = column
            reference = _dax_column(table, name)
            if row_context and table != self.workbook.fact_table:
                return f"RELATED({reference})"
            return reference
        if isinstance(expression, Unary):
            operand = self._emit(expression.operand, row_context, resolving)
            if expression.operator.upper() == "NOT":
                return f"NOT({operand})"
            return f"({expression.operator}{operand})"
        if isinstance(expression, Binary):
            left = self._emit(expression.left, row_context, resolving)
            right = self._emit(expression.right, row_context, resolving)
            operator = {
                "AND": "&&",
                "OR": "||",
                "<>": "<>",
                "!=": "<>",
                "^": "^",
            }.get(expression.operator.upper(), expression.operator)
            if operator == "/":
                return f"DIVIDE({left}, {right})"
            return f"({left} {operator} {right})"
        if isinstance(expression, Conditional):
            result = (
                self._emit(expression.otherwise, row_context, resolving)
                if expression.otherwise is not None
                else "BLANK()"
            )
            for condition, value in reversed(expression.branches):
                result = (
                    f"IF({self._emit(condition, row_context, resolving)}, "
                    f"{self._emit(value, row_context, resolving)}, {result})"
                )
            if expression.otherwise is None and len(expression.branches) == 1:
                condition, value = expression.branches[0]
                result = (
                    f"IF({self._emit(condition, row_context, resolving)}, "
                    f"{self._emit(value, row_context, resolving)})"
                )
            return result
        if isinstance(expression, Case):
            arguments = [self._emit(expression.value, row_context, resolving)]
            for value, result in expression.branches:
                arguments.extend(
                    (
                        self._emit(value, row_context, resolving),
                        self._emit(result, row_context, resolving),
                    )
                )
            if expression.otherwise is not None:
                arguments.append(self._emit(expression.otherwise, row_context, resolving))
            return f"SWITCH({', '.join(arguments)})"
        if isinstance(expression, Lod):
            body = self._emit(expression.expression, row_context, resolving)
            if expression.kind == "table":
                return f"CALCULATE({body}, REMOVEFILTERS())"
            dimensions = [
                self._emit(Field(dimension), row_context=True, resolving=resolving)
                for dimension in expression.dimensions
            ]
            values = [f"VALUES({dimension})" for dimension in dimensions]
            iterator_table = values[0] if len(values) == 1 else f"CROSSJOIN({', '.join(values)})"
            return f"SUMX({iterator_table}, CALCULATE({body}))"
        if isinstance(expression, Call):
            name = expression.name.upper()
            if name in {"TODAY", "NOW"}:
                if expression.arguments:
                    raise DaxUnsupportedError(f"{name} expects no arguments")
                return f"{name}()"
            if name == "DATEDIFF":
                return self._datediff(expression.arguments, row_context, resolving)
            if name == "TOTAL":
                if len(expression.arguments) != 1:
                    raise DaxUnsupportedError("TOTAL expects one argument")
                value = self._emit(
                    expression.arguments[0], row_context, resolving
                )
                return f"CALCULATE({value}, ALLSELECTED())"
            if name in _AGGREGATES:
                if len(expression.arguments) != 1:
                    raise DaxUnsupportedError(f"{name} expects one argument")
                argument = expression.arguments[0]
                argument_field: Field | None = argument if isinstance(argument, Field) else None
                referenced_calc = self._resolve_calc(argument_field.name) if argument_field is not None else None
                if referenced_calc is not None:
                    calc_expr = self._parse_calc(referenced_calc)
                    if self._contains_parameter(calc_expr):
                        row = self._emit(calc_expr, row_context=True, resolving=resolving)
                        return self._iterator(name, row)
                    if name == "COUNTD":
                        return (
                            "DISTINCTCOUNT("
                            f"{_dax_column(self.workbook.fact_table, referenced_calc.caption)})"
                        )
                if name == "ATTR":
                    return f"SELECTEDVALUE({self._emit(argument, row_context, resolving)})"
                emitted = self._emit(argument, row_context, resolving)
                if isinstance(argument, Field):
                    return self._aggregate_expression(name, emitted)
                return self._iterator(name, emitted)
            if name == "IIF":
                if len(expression.arguments) != 3:
                    raise DaxUnsupportedError("IIF expects three arguments")
                condition, yes, no = expression.arguments
                return (
                    f"IF({self._emit(condition, row_context, resolving)}, "
                    f"{self._emit(yes, row_context, resolving)}, "
                    f"{self._emit(no, row_context, resolving)})"
                )
            if name in _DATE_PARTS:
                return f"{_DATE_PARTS[name]}({self._emit(expression.arguments[0], row_context, resolving)})"
            if name == "DATEPART":
                return self._datepart(expression.arguments, row_context, resolving)
            if name == "ZN":
                value = self._emit(expression.arguments[0], row_context, resolving)
                return f"COALESCE({value}, 0)"
            if name == "ISNULL":
                return f"ISBLANK({self._emit(expression.arguments[0], row_context, resolving)})"
            if name == "IFNULL":
                return (
                    f"COALESCE({self._emit(expression.arguments[0], row_context, resolving)}, "
                    f"{self._emit(expression.arguments[1], row_context, resolving)})"
                )
            if name in {"LEFT", "RIGHT", "MID", "UPPER", "LOWER", "LEN", "TRIM", "ROUND", "ABS"}:
                dax_name = {"LEN": "LEN", "ROUND": "ROUND", "ABS": "ABS"}.get(name, name)
                args = ", ".join(
                    self._emit(argument, row_context, resolving)
                    for argument in expression.arguments
                )
                return f"{dax_name}({args})"
            if name == "CONTAINS":
                args = ", ".join(
                    self._emit(argument, row_context, resolving)
                    for argument in expression.arguments
                )
                return f"CONTAINSSTRING({args})"
            if name == "INT":
                return f"TRUNC({self._emit(expression.arguments[0], row_context, resolving)})"
            if name == "FLOAT":
                return f"VALUE({self._emit(expression.arguments[0], row_context, resolving)})"
            if name == "STR":
                return f"FORMAT({self._emit(expression.arguments[0], row_context, resolving)}, \"General Number\")"
            raise DaxUnsupportedError(f"Unsupported function {expression.name}")
        raise DaxUnsupportedError(f"Unsupported expression node {type(expression).__name__}")

    def _datepart(
        self,
        arguments: list[Expr],
        row_context: bool,
        resolving: frozenset[str],
    ) -> str:
        if len(arguments) != 2 or not isinstance(arguments[0], Literal):
            raise DaxUnsupportedError("DATEPART expects a date part string and date expression")
        part = arguments[0].value.casefold()
        function = {
            "year": "YEAR",
            "month": "MONTH",
            "week": "WEEKNUM",
            "day": "DAY",
            "quarter": "QUARTER",
        }.get(part)
        if function is None:
            raise DaxUnsupportedError(f"Unsupported DATEPART value {part!r}")
        value = self._emit(arguments[1], row_context, resolving)
        if function == "WEEKNUM":
            return f"WEEKNUM({value}, {self._weeknum_return_type()})"
        return f"{function}({value})"

    def _datediff(
        self,
        arguments: list[Expr],
        row_context: bool,
        resolving: frozenset[str],
    ) -> str:
        if (
            len(arguments) not in {3, 4}
            or not isinstance(arguments[0], Literal)
            or arguments[0].kind != "string"
        ):
            raise DaxUnsupportedError(
                "DATEDIFF expects a date part string, start date, and end date"
            )
        part = arguments[0].value.casefold()
        interval = {
            "year": "YEAR",
            "quarter": "QUARTER",
            "month": "MONTH",
            "week": "WEEK",
            "day": "DAY",
            "hour": "HOUR",
            "minute": "MINUTE",
            "second": "SECOND",
        }.get(part)
        if interval is None:
            raise DaxUnsupportedError(f"Unsupported DATEDIFF value {part!r}")
        start = self._emit(arguments[1], row_context, resolving)
        end = self._emit(arguments[2], row_context, resolving)
        return f"DATEDIFF({start}, {end}, {interval})"

    def _date_literal(self, value: str) -> str:
        normalized = value.strip()
        for pattern in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
            try:
                parsed = (
                    date.fromisoformat(normalized)
                    if pattern == "%Y-%m-%d"
                    else datetime.strptime(normalized, pattern).date()
                )
                return f"DATE({parsed.year}, {parsed.month}, {parsed.day})"
            except ValueError:
                continue
        raise DaxUnsupportedError(f"Unsupported date literal {value!r}")


def generate_calculations(workbook: Workbook) -> dict[str, CalcTranslation]:
    compiler = CalculationCompiler(workbook)
    return compiler.compile_all()


def generate_auto_measures(
    workbook: Workbook,
    calculations: dict[str, CalcTranslation] | None = None,
    model_overrides: ModelOverrides | None = None,
    measure_override_names: Iterable[str] = (),
) -> tuple[list[AutoMeasure], dict[str, str], list[AutoMeasure]]:
    compiler = CalculationCompiler(workbook)
    caption_map: dict[str, str] = {}
    for calc in workbook.calcs:
        caption_map[calc.internal_name] = calc.caption
    calcs_by_internal = {calc.internal_name: calc for calc in workbook.calcs}
    for table in workbook.tables:
        for column in table.columns:
            caption_map[column.name] = column.name
    measures_map: dict[str, str] = {}
    date_columns: dict[str, AutoMeasure] = {}
    calc_caption_set = {
        calc.caption.casefold()
        for calc in workbook.calcs
        if calculations is not None
        and calculations.get(calc.internal_name) is not None
        and calculations[calc.internal_name].classification == "aggregate"
    }
    parameter_internal_names = {
        parameter.internal_name for parameter in workbook.parameters
    }
    calc_measure_names = {
        calc.caption.casefold()
        for calc in workbook.calcs
        if (
            calc.internal_name not in parameter_internal_names
            and calculations is not None
            and calculations.get(calc.internal_name) is not None
            and calculations[calc.internal_name].status == "supported"
            and calculations[calc.internal_name].dax is not None
            and calculations[calc.internal_name].classification
            in {"aggregate", "lod", "table_calc"}
        )
    }
    raw_refs: list[str] = []
    for worksheet in workbook.worksheets:
        raw_refs.extend(_FIELD_PATTERN.findall(worksheet.rows))
        raw_refs.extend(_FIELD_PATTERN.findall(worksheet.cols))
        raw_refs.extend(
            encoding.field_ref
            for pane in worksheet.panes
            for encoding in pane.encodings
        )
    seen_refs: set[str] = set()
    auto_candidates: list[tuple[str, FieldRef, AutoMeasure]] = []
    for raw_ref in raw_refs:
        if raw_ref in seen_refs:
            continue
        seen_refs.add(raw_ref)
        reference = decode_field_ref(raw_ref, caption_map)
        calc = calcs_by_internal.get(reference.field_internal)
        translation = (
            calculations.get(reference.field_internal)
            if calculations is not None
            else None
        )
        if (
            calc is not None
            and translation is not None
            and translation.classification == "lod"
            and translation.status == "supported"
            and translation.dax is not None
        ):
            measures_map[raw_ref] = calc.caption
            continue
        measure = compiler.emit_aggregation(reference, raw_ref)
        if measure is None:
            continue
        if measure.display_folder == "Tableau date parts":
            date_columns[measure.name] = measure
            measures_map[raw_ref] = measure.name
            continue
        measures_map[raw_ref] = ""
        auto_candidates.append((raw_ref, reference, measure))

    column_names = {
        column.name.casefold()
        for table in workbook.tables
        for column in table.columns
    }
    column_names.update(
        parameter.caption.casefold() for parameter in workbook.parameters
    )
    if calculations is not None:
        column_names.update(
            calc.caption.casefold()
            for calc in workbook.calcs
            if calc.internal_name not in parameter_internal_names
            and (translation := calculations.get(calc.internal_name)) is not None
            and translation.status == "supported"
            and translation.is_calculated_column
            and translation.dax is not None
        )
    column_names.update(column.name.casefold() for column in date_columns.values())
    if model_overrides is not None:
        column_names.update(
            column.name.casefold()
            for column in model_overrides.calculated_columns
        )
        column_names.update(
            column.name.casefold()
            for table in model_overrides.calculated_tables
            for column in table.columns
        )

    reserved_names = column_names | calc_measure_names
    reserved_names.update(name.casefold() for name in measure_override_names)
    auto_measures: dict[str, AutoMeasure] = {}
    base_to_final: dict[str, str] = {}
    for raw_ref, reference, measure in auto_candidates:
        base_key = measure.name.casefold()
        if base_key in base_to_final:
            measures_map[raw_ref] = base_to_final[base_key]
            continue

        candidate_name = measure.name
        if base_key in calc_caption_set:
            candidate_name = f"{candidate_name} (agg)"
        if candidate_name.casefold() in reserved_names:
            candidate_name = (
                f"SUM {reference.field_caption}"
                if reference.derivation.casefold() == "sum"
                else candidate_name
            )
            if candidate_name.casefold() in reserved_names:
                base_name = candidate_name
                suffix_index = 1
                while True:
                    suffix = (
                        " (agg)"
                        if suffix_index == 1
                        else f" (agg {suffix_index})"
                    )
                    candidate_name = f"{base_name}{suffix}"
                    if candidate_name.casefold() not in reserved_names:
                        break
                    suffix_index += 1
        named_measure = AutoMeasure(
            candidate_name,
            measure.dax,
            measure.tableau_ref,
            measure.display_folder,
        )
        reserved_names.add(candidate_name.casefold())
        auto_measures[candidate_name.casefold()] = named_measure
        base_to_final[base_key] = candidate_name
        measures_map[raw_ref] = candidate_name

    return list(auto_measures.values()), measures_map, list(date_columns.values())
