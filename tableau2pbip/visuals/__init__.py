"""Vega spec builders for Tableau components rendered through the Deneb custom visual (lead-owned)."""
from collections.abc import Callable

from .bars import bar_compare, bar_distribution
from .kpi import kpi_card
from .table import ranked_table
from .text import rich_text
from .trends import step_trends

COMPONENTS: dict[str, Callable[..., dict]] = {
    "kpi_card": kpi_card,
    "bar_compare": bar_compare,
    "bar_distribution": bar_distribution,
    "step_trends": step_trends,
    "ranked_table": ranked_table,
    "rich_text": rich_text,
}


def build_spec(component: str, params: dict[str, object], width: float, height: float) -> dict[str, object]:
    """Return a Vega spec (dict) for `component` configured by `params`, sized to the visual container."""
    if component not in COMPONENTS:
        raise ValueError(f"unknown visual component {component!r}; known: {sorted(COMPONENTS)}")
    return COMPONENTS[component](width, height, **params)
