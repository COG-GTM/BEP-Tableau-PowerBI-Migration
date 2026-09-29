"""Bar-chart components: Tableau-style comparison bars (CY vs PY + signed measure) and a coloured distribution."""
from . import common, fonts

SELECTED_OFF = "datum.__selected__=='off'"


def _axis_range(x0: float, x1: float, pad: float) -> dict:
    """Tableau automatic axis: data extremes sit `pad` px inside the pane, a zero anchor sits on the pane edge."""
    return {"signal": f"[{x0}+(dmin<0?{pad}:0), {x1}-(dmax>0?{pad}:0)]"}


def bar_compare(width: float, height: float, *, category: str = "Category", cy: str = "CY", py: str = "PY",
                signed: str = "Signed", flag: str = "Flag", geometry: dict | None = None,
                formats: dict | None = None) -> dict:
    """Rows sorted by CY desc: label, flag dot, thin CY bar over wide PY bar, then a signed bar (blue ≥0 / orange <0)."""
    g = {"label_x": 10, "flag_x": 95, "sales": [112, 337], "signed": [337, 562], "pad": 11, "rows": [0, 320.9],
         "py_h": 15, "cy_h": 6, "signed_h": 15, "flag_d": 9.5, "label_font": "Tableau Medium", "label_pt": 10,
         "label_color": "#000000", **(geometry or {})}
    f = {"cy": "$", "py": "$", "signed": "$", **(formats or {})}
    weight, px = fonts.resolve(g["label_font"], g["label_pt"])
    cap = fonts.cap_height(px)
    dim = {"opacity": {"signal": f"{SELECTED_OFF}?0.25:1"}}
    tip = (f"{{'Sub-Category': datum[{category!r}], 'CY Sales': {_fmt(f'datum[{cy!r}]', f['cy'])}, "
           f"'PY Sales': {_fmt(f'datum[{py!r}]', f['py'])}, 'CY Profit': {_fmt(f'datum[{signed!r}]', f['signed'])}}}")
    band = {"scale": "row", "field": category, "band": 0.5}

    def bar(field, scale, h, color, x2=0):
        return {"type": "rect", "from": {"data": "rows"}, "encode": {"update": {
            "x": {"scale": scale, "value": x2}, "x2": {"scale": scale, "field": field},
            "yc": band, "height": {"value": h}, "fill": color, "tooltip": {"signal": tip}, **dim}}}

    return common.spec(width, height, data=[
        {"name": "rows", "source": "dataset", "transform": [
            {"type": "collect", "sort": {"field": cy, "order": "descending"}}]},
        {"name": "sext", "source": "dataset", "transform": [
            {"type": "fold", "fields": [cy, py], "as": ["k", "v"]},
            {"type": "aggregate", "fields": ["v", "v"], "ops": ["min", "max"], "as": ["mn", "mx"]}]},
        {"name": "pext", "source": "dataset", "transform": [
            {"type": "aggregate", "fields": [signed, signed], "ops": ["min", "max"], "as": ["mn", "mx"]}]}],
        signals=[
            {"name": "smin", "update": "min(0, length(data('sext'))?data('sext')[0].mn:0)"},
            {"name": "smax", "update": "max(0, length(data('sext'))?data('sext')[0].mx:0)"},
            {"name": "pmin", "update": "min(0, length(data('pext'))?data('pext')[0].mn:0)"},
            {"name": "pmax", "update": "max(0, length(data('pext'))?data('pext')[0].mx:0)"}],
        scales=[
            {"name": "row", "type": "band", "domain": {"data": "rows", "field": category, "sort": False},
             "range": g["rows"], "padding": 0},
            {"name": "sx", "type": "linear", "zero": False, "nice": False, "domain": {"signal": "[smin, smax]"},
             "range": {"signal": f"[{g['sales'][0]}+(smin<0?{g['pad']}:0), {g['sales'][1]}-(smax>0?{g['pad']}:0)]"}},
            {"name": "px", "type": "linear", "zero": False, "nice": False, "domain": {"signal": "[pmin, pmax]"},
             "range": {"signal": f"[{g['signed'][0]}+(pmin<0?{g['pad']}:0), {g['signed'][1]}-(pmax>0?{g['pad']}:0)]"}}],
        marks=[
            {"type": "text", "from": {"data": "rows"}, "encode": {"update": {
                "x": {"value": g["label_x"]}, "y": {"scale": "row", "field": category, "band": 0.5, "offset": cap / 2},
                "text": {"field": category}, "font": {"value": fonts.FAMILY}, "fontSize": {"value": round(px, 3)},
                "fontWeight": {"value": weight}, "fill": {"value": g["label_color"]}, "baseline": {"value": "alphabetic"},
                "tooltip": {"signal": tip}, **dim}}},
            {"type": "symbol", "from": {"data": "rows"}, "encode": {"update": {
                "x": {"value": g["flag_x"]}, "y": band, "shape": {"value": "circle"},
                "size": {"value": g["flag_d"] ** 2}, "fill": {"value": common.ORANGE},
                "opacity": {"signal": f"datum[{flag!r}]=='⬤'?({SELECTED_OFF}?0.25:1):0"}}}},
            bar(py, "sx", g["py_h"], {"value": common.PY_GRAY}),
            bar(cy, "sx", g["cy_h"], {"value": common.DARK}),
            bar(signed, "px", g["signed_h"], {"signal": f"datum[{signed!r}]<0?'{common.ORANGE}':'{common.BLUE}'"}),
        ])


def bar_distribution(width: float, height: float, *, x: str = "X", y: str = "Y", geometry: dict | None = None,
                     palette: list[str] | None = None) -> dict:
    """Vertical bars over an ordinal axis, colour interpolated by value, value labels above and bold axis labels."""
    g = {"plot": [4.5, 562.5], "top": 0, "bottom": 330, "headroom": 1.115, "bar_w": 0.774, "label_pt": 9, "axis_pt": 10,
         "axis_y": 345, "stroke": "#333333", **(geometry or {})}
    pal = palette or ["#f1f1f1", "#d9e8ed", "#c2e0ea", "#abd7e7", "#95cfe3", "#7fc7e0", "#6abfdd", "#56b8d9",
                      "#42b0d6", "#2fa9d3", "#1da2d0"]
    tip = f"{{'Nr of Orders': datum[{x!r}], 'Customers': format(datum[{y!r}], ',')}}"
    dim = {"opacity": {"signal": f"{SELECTED_OFF}?0.25:1"}}
    return common.spec(width, height, data=[
        {"name": "ext", "source": "dataset", "transform": [
            {"type": "aggregate", "fields": [y, y], "ops": ["min", "max"], "as": ["mn", "mx"]}]}],
        signals=[{"name": "ymax", "update": "max(0, length(data('ext'))?data('ext')[0].mx:0)"}],
        scales=[
            {"name": "x", "type": "band", "domain": {"data": "dataset", "field": x, "sort": True},
             "range": g["plot"], "paddingInner": 1 - g["bar_w"], "paddingOuter": (1 - g["bar_w"]) / 2},
            {"name": "y", "type": "linear", "zero": True, "nice": False, "domain": {"signal": f"[0, ymax*{g['headroom']}]"},
             "range": [g["bottom"], g["top"]]},
            {"name": "color", "type": "linear", "domain": {"data": "dataset", "field": y}, "range": pal,
             "interpolate": "rgb", "zero": False}],
        marks=[
            {"type": "rect", "from": {"data": "dataset"}, "encode": {"update": {
                "x": {"scale": "x", "field": x}, "width": {"scale": "x", "band": 1},
                "y": {"scale": "y", "field": y}, "y2": {"scale": "y", "value": 0},
                "fill": {"scale": "color", "field": y}, "stroke": {"value": g["stroke"]}, "strokeWidth": {"value": 1},
                "tooltip": {"signal": tip}, **dim}}},
            common.text({"scale": "x", "field": x, "band": 0.5}, {"scale": "y", "field": y, "offset": -5},
                        signal=f"format(datum[{y!r}], ',')", pt=g["label_pt"], color="#333333", align="center",
                        from_data="dataset", extra=dim),
            common.text({"scale": "x", "field": x, "band": 0.5}, g["axis_y"], signal=f"''+datum[{x!r}]",
                        font="Tableau Bold", pt=g["axis_pt"], color="#000000", align="center", from_data="dataset"),
        ])


def _fmt(expr: str, fmt: str) -> str:
    if fmt == "$":
        return f"(isValid({expr})?({expr}<0?'-':'')+'$'+format(abs({expr}),',.0f'):'')"
    return f"(isValid({expr})?format({expr},{fmt!r}):'')"
