"""Shared Vega building blocks: Tableau palette, spec skeleton and text marks."""
from . import fonts

VEGA_SCHEMA = "https://vega.github.io/schema/vega/v5.json"
DARK = "#212121"
GRAY_TEXT = "#898989"
AXIS_TEXT = "#999999"
PY_GRAY = "#cecece"
BLUE = "#1da2d0"
ORANGE = "#ff5500"
MARK_OPACITY = 0.706


def spec(width: float, height: float, marks: list, data: list | None = None, signals: list | None = None,
         scales: list | None = None, background: str | None = None) -> dict:
    s: dict = {"$schema": VEGA_SCHEMA, "width": width, "height": height, "padding": 0, "autosize": "none",
               "data": [{"name": "dataset"}] + (data or []), "signals": signals or [], "scales": scales or [],
               "marks": marks}
    if background:
        s["background"] = background
    return s


def text(x, y, *, value: str | None = None, signal: str | None = None, font: str | None = None,
         pt: float | None = None, color: str = DARK, align: str = "left", baseline: str = "alphabetic",
         from_data: str | None = None, extra: dict | None = None) -> dict:
    weight, px = fonts.resolve(font, pt)
    enc = {"x": x if isinstance(x, dict) else {"value": x}, "y": y if isinstance(y, dict) else {"value": y},
           "font": {"value": fonts.FAMILY}, "fontSize": {"value": round(px, 3)}, "fontWeight": {"value": weight},
           "fill": {"value": color}, "align": {"value": align}, "baseline": {"value": baseline},
           "text": {"signal": signal} if signal is not None else {"value": value}}
    enc.update(extra or {})
    m: dict = {"type": "text", "encode": {"update": enc}}
    if from_data:
        m["from"] = {"data": from_data}
    return m


def first(field: str, default: str = "null") -> str:
    """Signal expression reading `field` from the first dataset row."""
    return f"(length(data('dataset'))?data('dataset')[0][{field!r}]:{default})"
