"""Rich text: Tableau formatted-text runs (mixed fonts/colours, ⬤ glyphs, dynamic field values) laid out in Vega."""
import re

from . import common, fonts

PLACEHOLDER = re.compile(r"\{([^{}:]+)(?::([^{}]*))?\}")
CIRCLE = "⬤"
CIRCLE_DIAMETER = 0.76  # × font px, measured from Tableau legends
CIRCLE_ADVANCE = 1.0
CIRCLE_RAISE = 0.36
LINE_KEYS = {"x", "baseline", "align", "runs"}
RUN_KEYS = {"text", "font", "size", "color", "charset"}


def _segments(text: str) -> list[tuple[str, str, str]]:
    """Split run text into ('static', text, ''), ('field', name, d3format) and ('circle', '', '') pieces."""
    out: list[tuple[str, str, str]] = []
    pos = 0
    for m in PLACEHOLDER.finditer(text):
        out.extend(_static(text[pos:m.start()]))
        out.append(("field", m.group(1), m.group(2) or ""))
        pos = m.end()
    out.extend(_static(text[pos:]))
    return out


def _static(text: str) -> list[tuple[str, str, str]]:
    parts = text.split(CIRCLE)
    out: list[tuple[str, str, str]] = []
    for i, p in enumerate(parts):
        if i:
            out.append(("circle", "", ""))
        if p:
            out.append(("static", p, ""))
    return out


def _value_expr(name: str, fmt: str) -> str:
    v = common.first(name)
    return f"(isValid({v})?format({v},{fmt!r}):'')" if fmt else f"(isValid({v})?''+{v}:'')"


def line_marks(line: dict) -> list[dict]:
    unknown = set(line) - LINE_KEYS
    if unknown:
        raise ValueError(f"unknown rich_text line keys {sorted(unknown)}")
    align = line.get("align", "left")
    pieces = []
    for run in line["runs"]:
        bad = set(run) - RUN_KEYS
        if bad:
            raise ValueError(f"unknown rich_text run keys {sorted(bad)}")
        weight, px = fonts.resolve(run.get("font"), run.get("size"))
        for kind, val, fmt in _segments(run["text"]):
            if kind == "static":
                width = repr(round(fonts.text_width(val, weight, px), 3))
                expr = None
            elif kind == "field":
                expr = _value_expr(val, fmt)
                chars = run.get("charset", fonts.NUMERIC_CHARS)
                width = fonts.width_expr(expr, weight, px, chars)
            else:
                width, expr = repr(round(CIRCLE_ADVANCE * px, 3)), None
            pieces.append((kind, val, expr, width, run, px))
    total = "+".join(p[3] for p in pieces) or "0"
    x = line["x"]
    start = {"left": f"{x}", "right": f"{x}-({total})", "center": f"{x}-({total})/2"}[align]
    marks, offset = [], []
    for kind, val, expr, width, run, px in pieces:
        xs = "+".join([start] + offset)
        color = run.get("color", common.DARK)
        if kind == "circle":
            d = CIRCLE_DIAMETER * px
            marks.append({"type": "symbol", "encode": {"update": {
                "x": {"signal": f"{xs}+{CIRCLE_ADVANCE * px / 2}"}, "y": {"value": line["baseline"] - CIRCLE_RAISE * px},
                "shape": {"value": "circle"}, "size": {"value": round(d * d, 3)}, "fill": {"value": color}}}})
        elif expr is None:
            body = val.lstrip()
            weight, _ = fonts.resolve(run.get("font"), run.get("size"))
            lead = round(fonts.text_width(val[: len(val) - len(body)], weight, px), 3)
            if body.strip():
                marks.append(common.text({"signal": f"{xs}+{lead}"}, line["baseline"], value=body.rstrip(),
                                         font=run.get("font"), pt=run.get("size"), color=color))
        else:
            marks.append(common.text({"signal": xs}, line["baseline"], value=None,
                                     signal=expr, font=run.get("font"), pt=run.get("size"), color=color))
        offset.append(width)
    return marks


def rich_text(width: float, height: float, lines: list[dict], background: str | None = None) -> dict:
    marks = [m for line in lines for m in line_marks(line)]
    return common.spec(width, height, marks, background=background)
