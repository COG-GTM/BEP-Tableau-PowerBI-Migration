"""Ranked text table (Tableau top-N crosstab): shaded rank column, row dividers, aligned formatted columns."""
from . import common, fonts


def ranked_table(width: float, height: float, *, rank_by: str, columns: list[dict], top: int = 10,
                 geometry: dict | None = None) -> dict:
    """columns: [{field, x, align, format, color}]; format is '#rank', '$', 'int' or '' (raw text)."""
    g = {"rows": [1, 312], "x0": 3, "x1": 561, "rank_bg": [4, 47], "rank_bg_color": "#f5f5f5",
         "divider": "#cbcbcb", "baseline_offset": 3.5, **(geometry or {})}
    band = (g["rows"][1] - g["rows"][0]) / top
    _, px = fonts.resolve(None, None)
    marks: list[dict] = [
        {"type": "rect", "encode": {"update": {
            "x": {"value": g["rank_bg"][0]}, "x2": {"value": g["rank_bg"][1]}, "y": {"value": g["rows"][0] + 1},
            "y2": {"signal": f"{g['rows'][0]}+{band}*length(data('ranked'))"},
            "fill": {"value": g["rank_bg_color"]}}}},
        {"type": "rule", "from": {"data": "dividers"}, "encode": {"update": {
            "x": {"value": g["x0"]}, "x2": {"value": g["x1"]}, "y": {"signal": f"{g['rows'][0]}+{band}*datum.data"},
            "stroke": {"value": g["divider"]}, "strokeWidth": {"value": 1}}}},
    ]
    tip = "{" + ", ".join(f"{c['field']!r}: {_cell(c)}" for c in columns if c.get("format") != "#rank") + "}"
    for c in columns:
        marks.append(common.text(
            c["x"], {"signal": f"{g['rows'][0]}+{band}*(datum.rank-0.5)+{g['baseline_offset'] + fonts.cap_height(px) / 2 - 4.4}"},
            signal=_cell(c), color=c.get("color", "#333333"), align=c.get("align", "left"), from_data="ranked",
            extra={"tooltip": {"signal": tip}, "opacity": {"signal": "datum.__selected__=='off'?0.25:1"}}))
    return common.spec(width, height, marks, data=[
        {"name": "ranked", "source": "dataset", "transform": [
            {"type": "filter", "expr": f"isValid(datum[{rank_by!r}])"},
            {"type": "window", "sort": {"field": rank_by, "order": "descending"}, "ops": ["row_number"], "as": ["rank"]},
            {"type": "filter", "expr": f"datum.rank<={top}"}]},
        {"name": "dividers", "values": [], "transform": [
            {"type": "sequence", "start": 0, "stop": {"signal": "length(data('ranked'))+1"}}]}],
        )


def _cell(c: dict) -> str:
    v, fmt = f"datum[{c['field']!r}]", c.get("format", "")
    if fmt == "#rank":
        return "'#'+datum.rank"
    if fmt == "$":
        return f"(isValid({v})?({v}<0?'-':'')+'$'+format(abs({v}),',.0f'):'')"
    if fmt == "int":
        return f"(isValid({v})?format({v},',.0f'):'')"
    if fmt == "date":
        return f"(isValid({v})?timeFormat(toDate({v}),'%-m/%-d/%Y'):'')"
    return f"(isValid({v})?''+{v}:'')"
