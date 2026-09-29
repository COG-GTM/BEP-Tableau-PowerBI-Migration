"""Tableau KPI card: title, headline total, ▲/▼ % vs PY, CY/PY monthly lines with highest/lowest month dots."""
from . import common, fonts

GEOMETRY = {"title": (15.5, 31), "value": (12, 69), "delta": (12, 95), "x0": 34.5, "x1": 345, "y_top": 128,
            "y_zero": 237, "axis_y": 256, "line_w": 3.0, "dot": 20}


def kpi_card(width: float, height: float, title: str, value_format: str, *, month: str = "Month", cy: str = "CY",
             py: str = "PY", total: str = "Total", diff: str = "Diff", text_color: str = common.TEXT_DEFAULT,
             measure_label: str = "", geometry: dict | None = None) -> dict:
    """value_format is a d3 format applied to the headline total; '$~s'-style K formatting uses 'k$' shorthand."""
    g = {**GEOMETRY, **(geometry or {})}
    tot, dif = common.first(total, "0"), common.first(diff, "0")
    value_sig = _format_value(tot, value_format)
    delta_sig = f"({dif}>=0?'▲ '+format({dif},'.1%'):'▼ '+format({dif},'.1%'))"
    d_weight, d_px = fonts.resolve("Tableau Semibold", 12)
    delta_w = fonts.width_expr("delta_text", d_weight, d_px)
    space_w = fonts.text_width(" ", d_weight, d_px)
    label = measure_label or title.replace("Total ", "")
    tooltip = (f"{{'Month': datum.monthName, '{label} CY': {_format_value(f'datum[{cy!r}]', value_format, True)}, "
               f"'{label} PY': {_format_value(f'datum[{py!r}]', value_format, True)}}}")
    return common.spec(width, height, background="#ffffff", data=[
        {"name": "pts", "source": "dataset", "transform": [
            {"type": "filter", "expr": f"isValid(datum[{cy!r}])"},
            {"type": "joinaggregate", "fields": [cy, cy], "ops": ["max", "min"], "as": ["mx", "mn"]},
            {"type": "formula", "as": "monthName",
             "expr": f"timeFormat(datetime(2000, datum[{month!r}]-1, 1), '%B')"}]}],
        signals=[{"name": "delta_text", "update": delta_sig}, {"name": "delta_w", "update": delta_w}],
        scales=[
            {"name": "x", "type": "linear", "domain": [1, 12], "range": [g["x0"], g["x1"]], "zero": False},
            {"name": "y", "type": "linear", "range": [g["y_zero"], g["y_top"]], "zero": True, "nice": False,
             "domain": {"fields": [{"data": "dataset", "field": cy}, {"data": "dataset", "field": py}]}}],
        marks=[
            common.text(g["title"][0], g["title"][1], value=title, font="Tableau Book", pt=14, color=text_color),
            common.text(g["value"][0], g["value"][1], signal=value_sig, font="Tableau Bold", pt=22, color=text_color),
            common.text(g["delta"][0], g["delta"][1], signal="delta_text", font="Tableau Semibold", pt=12,
                        color=text_color),
            common.text({"signal": f"{g['delta'][0]}+delta_w+{space_w}"}, g["delta"][1], value="vs. PY",
                        font="Tableau Book", pt=12, color=common.GRAY_TEXT),
            _line(month, py, common.PY_GRAY, g["line_w"]),
            _line(month, cy, common.DARK, g["line_w"]),
            {"type": "symbol", "from": {"data": "pts"}, "encode": {"update": {
                "x": {"scale": "x", "field": month}, "y": {"scale": "y", "field": cy}, "shape": {"value": "circle"},
                "size": {"value": g["dot"] ** 2}, "fill": {"signal": f"datum[{cy!r}]==datum.mx?'{common.BLUE}':'{common.ORANGE}'"},
                "opacity": {"signal": f"datum[{cy!r}]==datum.mx||datum[{cy!r}]==datum.mn?{common.MARK_OPACITY}:0"},
                "tooltip": {"signal": tooltip}}}},
            {"type": "symbol", "from": {"data": "pts"}, "encode": {"update": {
                "x": {"scale": "x", "field": month}, "y": {"scale": "y", "field": cy}, "shape": {"value": "circle"},
                "size": {"value": 144}, "fill": {"value": "transparent"}, "tooltip": {"signal": tooltip}}}},
            common.text({"scale": "x", "value": 1}, g["axis_y"], value="Jan", color=common.AXIS_TEXT, align="center"),
            common.text({"scale": "x", "value": 12}, g["axis_y"], value="Dec", color=common.AXIS_TEXT, align="center"),
        ])


def _line(month: str, field: str, color: str, width: float) -> dict:
    return {"type": "line", "from": {"data": "dataset"}, "encode": {"update": {
        "x": {"scale": "x", "field": month}, "y": {"scale": "y", "field": field}, "stroke": {"value": color},
        "strokeWidth": {"value": width}, "defined": {"signal": f"isValid(datum[{field!r}])"}}}}


def _format_value(expr: str, fmt: str, guard: bool = False) -> str:
    """'k$' → Tableau n"$"#,##0,K ; otherwise a d3 format string."""
    body = (f"({expr}<0?'-':'')+'$'+format(abs({expr})/1000,',.0f')+'K'" if fmt == "k$"
            else f"({expr}<0?'-':'')+'$'+format(abs({expr}),',.0f')" if fmt == "$" else f"format({expr},{fmt!r})")
    return f"(isValid({expr})?{body}:'')" if guard else body
