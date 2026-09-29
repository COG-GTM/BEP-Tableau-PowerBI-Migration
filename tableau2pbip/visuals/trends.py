"""Stacked step-line trend panes (one per measure) coloured above/below the pane average, with average reference lines."""
from . import common, fonts

AXIS_PAD = 0.055  # Tableau automatic axis padding as a fraction of the data span


def _axis_signals(name: str, field: str, i: int) -> list[dict]:
    lo, hi = f"{name}_lo", f"{name}_hi"
    return [
        {"name": lo, "update": f"min(0, extent(pluck(data('pts'), {field!r}))[0])"},
        {"name": hi, "update": f"max(0, extent(pluck(data('pts'), {field!r}))[1])"},
        {"name": f"{name}_dom", "update": f"[{lo}<0?{lo}-({hi}-{lo})*{AXIS_PAD}:0, {hi}>0?{hi}+({hi}-{lo})*{AXIS_PAD}:0]"},
        {"name": f"{name}_avg", "update": f"length(data('stats'))?data('stats')[0].avg_{i}:0"},
    ]


def step_trends(width: float, height: float, *, x: str = "Week", measures: list[dict] | None = None,
                geometry: dict | None = None) -> dict:
    """measures: [{field, label, format}] top to bottom; format '$k' renders Tableau "$#,##0,K" ticks."""
    ms = measures or [{"field": "Sales", "label": "Sales"}, {"field": "Profit", "label": "Profit"}]
    g = {"x0": 70, "x1": 561, "panes": [[0, 146.5], [146.5, 294]], "x_axis_y": 313, "ytick_x": 62.5,
         "title_x": 19.5, "line_w": 2.5, "grid": "#cbcbcb", "tick_count": [4, 3], "x_ticks": 10,
         **(geometry or {})}
    signals: list[dict] = [
        {"name": "xext", "update": f"extent(pluck(data('pts'), {x!r}))"},
        {"name": "xdom", "update": "[xext[0]-(xext[1]-xext[0])*0.057, xext[1]+(xext[1]-xext[0])*0.057]"},
    ]
    scales: list[dict] = [{"name": "x", "type": "linear", "zero": False, "nice": False,
                           "domain": {"signal": "xdom"}, "range": [g["x0"], g["x1"]]}]
    marks: list[dict] = [
        _rule(g["x0"], g["panes"][0][0], g["x0"], g["panes"][-1][1], g["grid"]),
        _rule(g["x1"], g["panes"][0][0], g["x1"], g["panes"][-1][1], g["grid"]),
    ]
    top_rule = g.get("top_rule")
    if top_rule is not None:
        if (
            not isinstance(top_rule, (list, tuple))
            or len(top_rule) != 3
            or any(not isinstance(value, (int, float)) for value in top_rule)
        ):
            raise ValueError("geometry.top_rule must contain [x0, x1, y]")
        x0, x1, y = top_rule
        marks.append(_rule(x0, y, x1, y, g["grid"]))
    data: list[dict] = [{"name": "pts", "source": "dataset", "transform": [
        {"type": "filter", "expr": f"isValid(datum[{x!r}])"},
        {"type": "collect", "sort": {"field": x}}]},
        {"name": "stats", "source": "pts", "transform": [{"type": "aggregate", "ops": ["mean"] * len(ms),
                                                           "fields": [m["field"] for m in ms],
                                                           "as": [f"avg_{i}" for i in range(len(ms))]}]}]
    wt, px = fonts.resolve(None, None)
    cap = fonts.cap_height(px)
    for i, m in enumerate(ms):
        f, sid = m["field"], f"m{i}"
        top, bottom = g["panes"][i]
        fmt = m.get("format", "$k")
        signals += _axis_signals(sid, f, i)
        scales.append({"name": sid, "type": "linear", "zero": False, "nice": False,
                       "domain": {"signal": f"{sid}_dom"}, "range": [bottom, top]})
        color = f"(datum[{f!r}]>={sid}_avg?'{common.BLUE}':'{common.ORANGE}')"
        next_color = f"(datum.next_{i}>={sid}_avg?'{common.BLUE}':'{common.ORANGE}')"
        data.append({"name": f"seg{i}", "source": "pts", "transform": [
            {"type": "window", "ops": ["lead", "lead"], "fields": [f, x], "as": [f"next_{i}", "next_x"]},
            {"type": "formula", "as": "c0", "expr": color},
            {"type": "formula", "as": "c1", "expr": f"isValid(datum.next_{i})?{next_color}:datum.c0"}]})
        n = g["tick_count"][i]
        signals += [
            {"name": f"{sid}_raw", "update": f"max(1e-9, ({sid}_hi-{sid}_lo)/{n})"},
            {"name": f"{sid}_mag", "update": f"pow(10, floor(log({sid}_raw)/LN10))"},
            {"name": f"{sid}_step", "update": f"{sid}_mag*({sid}_raw/{sid}_mag<=1?1:{sid}_raw/{sid}_mag<=2?2:"
                                              f"{sid}_raw/{sid}_mag<=2.5?2.5:{sid}_raw/{sid}_mag<=5?5:10)"},
            {"name": f"{sid}_tol", "update": f"({sid}_dom[1]-{sid}_dom[0])*0.03"},
        ]
        data.append({"name": f"ticks{i}", "values": [], "transform": [
            {"type": "sequence", "start": {"signal": f"ceil(({sid}_dom[0]-{sid}_tol)/{sid}_step)"},
             "stop": {"signal": f"floor(({sid}_dom[1]+{sid}_tol)/{sid}_step)+1"}},
            {"type": "formula", "as": "v", "expr": f"datum.data*{sid}_step"}]})
        tip = (f"{{'Week of Order Date': 'Week '+datum[{x!r}], {m.get('label', f)!r}: {_fmt(f'datum[{f!r}]', fmt, True)}}}")
        marks += [
            _rule(g["x0"], bottom, g["x1"], bottom, g["grid"]),
            {"type": "rule", "encode": {"update": {
                "x": {"value": g["x0"]}, "x2": {"value": g["x1"]}, "y": {"scale": sid, "signal": f"{sid}_avg"},
                "stroke": {"value": "#959595"}, "strokeWidth": {"value": 2}, "strokeDash": {"value": [7, 4]}}}},
            common.text(g["x0"] + 1, {"scale": sid, "signal": f"{sid}_avg", "offset": -4},
                        signal=f"'Avg. '+{_fmt(f'{sid}_avg', fmt)}", color="#333333"),
            {"type": "rect", "from": {"data": f"seg{i}"}, "encode": {"update": {
                "x": {"scale": "x", "field": x}, "x2": {"scale": "x", "signal": f"isValid(datum.next_x)?datum.next_x:datum[{x!r}]"},
                "yc": {"scale": sid, "field": f}, "height": {"value": g["line_w"]}, "fill": {"field": "c0"}}}},
            {"type": "rect", "from": {"data": f"seg{i}"}, "encode": {"update": {
                "xc": {"scale": "x", "signal": "datum.next_x"}, "width": {"value": g["line_w"]},
                "y": {"scale": sid, "signal": f"max(datum[{f!r}], datum.next_{i})", "offset": -g["line_w"] / 2},
                "y2": {"scale": sid, "signal": f"min(datum[{f!r}], datum.next_{i})", "offset": g["line_w"] / 2},
                "fill": {"signal": f"{{gradient: 'linear', x1: 0, y1: 0, x2: 0, y2: 1, stops: ["
                                   f"{{offset: 0, color: datum[{f!r}]>=datum.next_{i}?datum.c0:datum.c1}}, "
                                   f"{{offset: 1, color: datum[{f!r}]>=datum.next_{i}?datum.c1:datum.c0}}]}}"},
                "opacity": {"signal": "isValid(datum.next_x)?1:0"}}}},
            {"type": "symbol", "from": {"data": "pts"}, "encode": {"update": {
                "x": {"scale": "x", "field": x}, "y": {"scale": sid, "field": f}, "size": {"value": 100},
                "fill": {"value": "transparent"}, "tooltip": {"signal": tip}}}},
            common.text(g["ytick_x"], {"signal": f"clamp(scale('{sid}', datum.v)+{cap / 2}, {top + cap + 2}, {bottom - 2})"},
                        signal=_fmt("datum.v", fmt), color=common.AXIS_TEXT, align="right", from_data=f"ticks{i}"),
            common.text(g["title_x"], (top + bottom) / 2, value=m.get("label", f), color="#333333", align="center",
                        baseline="middle", extra={"angle": {"value": -90}}),
        ]
    data.append({"name": "xticks", "values": [], "transform": [
        {"type": "sequence", "start": 0, "stop": {"signal": f"ceil(xdom[1]/{g['x_ticks']})"}},
        {"type": "formula", "as": "v", "expr": f"datum.data*{g['x_ticks']}"},
        {"type": "filter", "expr": "datum.v>=xdom[0]&&datum.v<=xdom[1]"}]})
    marks.append(common.text({"scale": "x", "field": "v"}, g["x_axis_y"], signal="''+datum.v", color=common.AXIS_TEXT,
                             align="center", from_data="xticks"))
    return common.spec(width, height, marks, data=data, signals=signals, scales=scales)


def _rule(x1: float, y1: float, x2: float, y2: float, color: str) -> dict:
    return {"type": "rule", "encode": {"update": {"x": {"value": x1}, "y": {"value": y1}, "x2": {"value": x2},
                                                  "y2": {"value": y2}, "stroke": {"value": color}, "strokeWidth": {"value": 1}}}}


def _fmt(expr: str, fmt: str, full: bool = False) -> str:
    if fmt == "$k" and not full:
        return f"(({expr})<0?'-':'')+'$'+format(abs({expr})/1000,',.0f')+'K'"
    if fmt in ("$k", "$"):
        return f"(({expr})<0?'-':'')+'$'+format(abs({expr}),',.0f')"
    return f"format({expr},{fmt!r})"
