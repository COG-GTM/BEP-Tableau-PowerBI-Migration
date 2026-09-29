"""Tableau font substitution and Segoe UI text metrics for laying out mixed text runs in Vega."""
import json
from functools import lru_cache
from pathlib import Path

FAMILY = "Segoe UI"
PT_TO_PX = 4 / 3
# Font-specific size adjustments are measured against Tableau renders to keep line lengths and positions aligned.
TABLEAU_SCALE = 1.045
TABLEAU_SCALE_BY_FONT = {"Tableau Bold": 1.01, "Tableau Medium": 1.09}
TABLEAU_WEIGHTS = {
    "Tableau Light": 300,
    "Tableau Book": 400,
    "Tableau Regular": 400,
    "Tableau Medium": 400,
    "Tableau Semibold": 600,
    "Tableau Bold": 700,
}
DEFAULT_FONT = "Tableau Book"
DEFAULT_PT = 9.0
NUMERIC_CHARS = "0123456789,.-%$K▲▼ #/"


@lru_cache(maxsize=1)
def _metrics() -> dict:
    return json.loads(Path(__file__).with_name("segoe_metrics.json").read_text(encoding="utf-8"))


def resolve(fontname: str | None, pt: float | None) -> tuple[int, float]:
    """(css weight, px size) for a Tableau font name and point size."""
    name = fontname or DEFAULT_FONT
    if name not in TABLEAU_WEIGHTS:
        raise ValueError(f"unknown Tableau font {name!r}")
    return TABLEAU_WEIGHTS[name], (pt or DEFAULT_PT) * PT_TO_PX * TABLEAU_SCALE_BY_FONT.get(name, TABLEAU_SCALE)


def _advances(weight: int) -> dict[str, int]:
    m = _metrics()["weights"]
    return m[str(weight)] if str(weight) in m else m["400"]


def text_width(text: str, weight: int, px: float) -> float:
    adv = _advances(weight)
    fallback = adv["0"]
    return sum(adv.get(c, fallback) for c in text) * px / _metrics()["unitsPerEm"]


def ascent(px: float) -> float:
    return _metrics()["winAscent"] / _metrics()["unitsPerEm"] * px


def cap_height(px: float) -> float:
    return _metrics()["capHeight"] / _metrics()["unitsPerEm"] * px


def width_expr(s_expr: str, weight: int, px: float, charset: str = NUMERIC_CHARS) -> str:
    """Vega expression for the rendered width of string expression `s_expr` whose characters come from `charset`."""
    groups: dict[float, list[str]] = {}
    for c in dict.fromkeys(charset):
        groups.setdefault(round(text_width(c, weight, px), 4), []).append(c)
    terms = []
    for w, chars in groups.items():
        cls = "".join("\\" + c if c in r"\^]-/[" else c for c in chars)
        terms.append(f"(length({s_expr})-length(replace({s_expr},/[{cls}]/g,'')))*{w}")
    return "(" + "+".join(terms) + ")"
