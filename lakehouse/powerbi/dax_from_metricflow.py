from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

_BARE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_NULLIF_DIVISION = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*/\s*NULLIF\s*\(\s*"
    r"([A-Za-z_][A-Za-z0-9_]*)\s*,\s*0(?:\.0+)?\s*\)\s*$",
    re.IGNORECASE,
)


def _read_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise TypeError(f"{path} must contain a YAML mapping")
    return loaded


def _metric_dependencies(metric: dict[str, Any]) -> set[str]:
    dependencies = metric.get("type_params", {}).get("metrics", [])
    if not isinstance(dependencies, list):
        return set()
    return {
        dependency["name"]
        for dependency in dependencies
        if isinstance(dependency, dict) and isinstance(dependency.get("name"), str)
    }


def _has_filter(value: dict[str, Any]) -> bool:
    return any(value.get(key) not in (None, [], {}) for key in ("filter", "filters", "where"))


def generate_measures(
    semantic_models_path: Path, bindings_path: Path
) -> dict[str, str]:
    semantic_config = _read_yaml(semantic_models_path)
    binding_config = _read_yaml(bindings_path)
    semantic_models = semantic_config.get("semantic_models")
    metric_definitions = semantic_config.get("metrics")
    binding_models = binding_config.get("semantic_models")
    if not isinstance(semantic_models, list) or not isinstance(metric_definitions, list):
        raise TypeError(
            f"{semantic_models_path} must define semantic_models and metrics lists"
        )
    if not isinstance(binding_models, dict):
        raise TypeError(f"{bindings_path} must define a semantic_models mapping")

    measure_by_name: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for semantic_model in semantic_models:
        if not isinstance(semantic_model, dict) or not isinstance(
            semantic_model.get("name"), str
        ):
            continue
        model_name = semantic_model["name"]
        measures = semantic_model.get("measures", [])
        if not isinstance(measures, list):
            continue
        for measure in measures:
            if isinstance(measure, dict) and isinstance(measure.get("name"), str):
                measure_by_name.setdefault(measure["name"], []).append(
                    (model_name, measure)
                )

    metric_by_name: dict[str, dict[str, Any]] = {}
    labels: dict[str, str] = {}
    seen_labels: set[str] = set()
    for metric in metric_definitions:
        if not isinstance(metric, dict) or not isinstance(metric.get("name"), str):
            continue
        name = metric["name"]
        label = metric.get("label", name)
        if not isinstance(label, str):
            raise TypeError(f"Metric '{name}': label must be a string")
        if label.casefold() in seen_labels:
            raise ValueError(f"Metric '{label}': duplicate metric label")
        metric_by_name[name] = metric
        labels[name] = label
        seen_labels.add(label.casefold())

    output: dict[str, str] = {}
    for metric_name, metric in metric_by_name.items():
        label = labels[metric_name]
        try:
            if _has_filter(metric):
                raise ValueError("filters are not supported")
            metric_type = metric.get("type")
            type_params = metric.get("type_params", {})
            if not isinstance(type_params, dict) or _has_filter(type_params):
                raise ValueError("filters are not supported")

            if metric_type == "simple":
                measure_name = type_params.get("measure")
                candidates = (
                    measure_by_name.get(measure_name, [])
                    if isinstance(measure_name, str)
                    else []
                )
                if len(candidates) != 1:
                    raise ValueError(f"measure '{measure_name}' is missing or ambiguous")
                semantic_model_name, measure = candidates[0]
                if _has_filter(measure):
                    raise ValueError("measure filters are not supported")
                binding = binding_models.get(semantic_model_name)
                if not isinstance(binding, dict):
                    raise ValueError(
                        f"semantic model '{semantic_model_name}' has no bindings"
                    )
                columns = binding.get("columns")
                expression = measure.get("expr")
                if not isinstance(columns, dict) or not isinstance(expression, str):
                    raise ValueError("measure binding is invalid")
                bare_column = _BARE_IDENTIFIER.fullmatch(expression.strip())
                if bare_column is None:
                    raise ValueError("measure expressions must reference a single column")
                dax_column = columns.get(bare_column.group(0))
                if not isinstance(dax_column, str):
                    raise ValueError(
                        f"column '{bare_column.group(0)}' has no Power BI binding"
                    )
                aggregation = measure.get("agg")
                if aggregation == "sum":
                    dax_expression = f"SUM({dax_column})"
                elif aggregation == "count_distinct":
                    dax_expression = f"DISTINCTCOUNT({dax_column})"
                else:
                    raise ValueError(f"aggregation '{aggregation}' is not supported")
            elif metric_type == "derived":
                expression = type_params.get("expr")
                if not isinstance(expression, str):
                    raise ValueError("derived metric expression must be a string")
                dependencies = _metric_dependencies(metric)
                division = _NULLIF_DIVISION.fullmatch(expression)
                if division is None:
                    raise ValueError(f"derived expression {expression!r} is not supported")
                numerator, denominator = division.groups()
                if {numerator, denominator} - dependencies:
                    raise ValueError(
                        "derived expression operands must be declared dependencies"
                    )
                if numerator not in labels or denominator not in labels:
                    raise ValueError("derived expression references an unknown metric")
                dax_expression = (
                    f"DIVIDE([{labels[numerator]}], [{labels[denominator]}])"
                )
            else:
                raise ValueError(f"metric type '{metric_type}' is not supported")
            output[label] = dax_expression
        except ValueError as error:
            if str(error).startswith(f"Metric '{label}':"):
                raise
            raise ValueError(f"Metric '{label}': {error}") from error

    return output
