#!/usr/bin/env python3
"""Inventory Tableau XML workbooks and validate calculated-field references."""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

from lxml import etree


FIELD_RE = re.compile(r"\[([^\[\]]+)\]")
QUALIFIED_RE = re.compile(r"\[([^\[\]]+)\]\s*\.\s*\[([^\[\]]+)\]")
LOD_RE = re.compile(r"\{\s*(FIXED|INCLUDE|EXCLUDE)\b", re.IGNORECASE)
BUILTIN_FIELDS = {
    "Measure Names",
    "Measure Values",
    "Number of Records",
    "Latitude (generated)",
    "Longitude (generated)",
}


def local_name(element):
    return etree.QName(element).localname


def load_workbook(path: Path):
    if path.suffix.lower() == ".twbx":
        with zipfile.ZipFile(path) as package:
            twb_members = sorted(name for name in package.namelist() if name.lower().endswith(".twb"))
            if not twb_members:
                raise ValueError(f"No .twb workbook found in {path}")
            member = next(
                (name for name in twb_members if Path(name).stem == path.stem),
                twb_members[0],
            )
            contents = package.read(member)
            members = package.namelist()
    elif path.suffix.lower() == ".twb":
        contents = path.read_bytes()
        members = []
        member = path.name
    else:
        raise ValueError("Input must be a .twb or .twbx file")
    parser = etree.XMLParser(resolve_entities=False, no_network=True, recover=False)
    return etree.fromstring(contents, parser), member, members


def source_metadata(root):
    sources = {}
    captions = {}
    field_names = defaultdict(set)
    for datasource in root.xpath("./datasources/datasource"):
        source_id = datasource.get("name", "")
        caption = datasource.get("caption", source_id)
        sources[source_id] = datasource
        captions[caption] = source_id
        captions[source_id] = source_id
        for column in datasource.findall("./column"):
            name = column.get("name", "").strip("[]")
            if name:
                field_names[source_id].add(name)
    for dependencies in root.xpath(".//datasource-dependencies"):
        source_id = dependencies.get("datasource", "")
        for column in dependencies.findall("./column"):
            name = column.get("name", "").strip("[]")
            if name:
                field_names[source_id].add(name)
    return sources, captions, field_names


def calc_records(root):
    records = []
    for datasource in root.xpath("./datasources/datasource"):
        source_id = datasource.get("name", "")
        for column in datasource.findall("./column"):
            calculation = column.find("./calculation")
            if calculation is not None and calculation.get("formula") is not None:
                records.append((source_id, column.get("name", ""), calculation.get("formula", ""), calculation))
    for dependencies in root.xpath(".//datasource-dependencies"):
        source_id = dependencies.get("datasource", "")
        for column in dependencies.findall("./column"):
            calculation = column.find("./calculation")
            if calculation is not None and calculation.get("formula") is not None:
                records.append((source_id, column.get("name", ""), calculation.get("formula", ""), calculation))
    unique = {}
    for source_id, field, formula, calculation in records:
        unique[(source_id, field, formula)] = calculation
    return [(source, field, formula, calc) for (source, field, formula), calc in unique.items()]


def validate_references(records, captions, field_names):
    issues = []
    reference_count = 0
    for source_id, field, formula, _ in records:
        qualified = list(QUALIFIED_RE.finditer(formula))
        qualified_spans = []
        for match in qualified:
            source_label, field_name = match.groups()
            qualified_spans.append(match.span())
            target_source = captions.get(source_label)
            if target_source is None:
                target_source = next(
                    (candidate for candidate, names in field_names.items() if field_name in names),
                    None,
                )
            reference_count += 1
            if target_source is None or field_name not in field_names[target_source]:
                issues.append(
                    f"{source_id} {field}: [{source_label}].[{field_name}] is not defined"
                )
        remaining = list(formula)
        for start, end in qualified_spans:
            remaining[start:end] = " " * (end - start)
        for match in FIELD_RE.finditer("".join(remaining)):
            field_name = match.group(1)
            if field_name in BUILTIN_FIELDS or field_name.endswith(" (generated)"):
                continue
            reference_count += 1
            if field_name in field_names[source_id]:
                continue
            if field_name in field_names.get("Parameters", set()):
                continue
            issues.append(f"{source_id} {field}: [{field_name}] is not defined")
    return reference_count, issues


def inventory(path: Path):
    root, member, members = load_workbook(path)
    sources, captions, fields = source_metadata(root)
    calculations = calc_records(root)
    ref_count, ref_issues = validate_references(calculations, captions, fields)

    print(f"Workbook: {path}")
    print(f"Workbook XML member: {member}")
    if members:
        print(f"Package members: {len(members)}")
    print(f"Data sources ({len(sources)}):")
    for source_id, datasource in sources.items():
        connection = datasource.find("./connection")
        outer_class = connection.get("class", "none") if connection is not None else "none"
        nested = connection.xpath(".//connection") if connection is not None else []
        classes = [item.get("class", "unknown") for item in nested]
        if "postgres" in classes:
            mode = "LIVE"
        elif "hyper" in classes:
            mode = "EXTRACT"
        elif source_id == "Parameters":
            mode = "PARAMETERS"
        elif "textscan" in classes:
            mode = "LIVE"
        else:
            mode = "UNKNOWN"
        connection_attrs = []
        for item in nested:
            attrs = [
                f"{key}={item.get(key)}"
                for key in ("server", "port", "dbname", "username", "sslmode", "directory", "filename")
                if item.get(key) is not None
            ]
            if attrs:
                connection_attrs.append(", ".join(attrs))
        caption = datasource.get("caption", source_id)
        print(
            f"  - {caption} [{source_id}]: connection={outer_class}, "
            f"mode={mode}, nested-classes={','.join(classes) or 'none'}"
        )
        for attr in connection_attrs:
            print(f"      {attr}")
        relationships = []
        for graph in datasource.iter():
            if "object-graph" not in local_name(graph):
                continue
            object_labels = {
                item.get("id", ""): item.get("caption", item.get("id", ""))
                for item in graph.iter()
                if local_name(item) == "object"
            }
            for relationship in graph.iter():
                if local_name(relationship) != "relationship":
                    continue
                endpoints = [
                    item.get("object-id", "")
                    for item in relationship
                    if local_name(item) in {"first-end-point", "second-end-point"}
                ]
                expression_tokens = [
                    item.get("op", "")
                    for item in relationship.iter()
                    if local_name(item) == "expression" and item.get("op")
                ]
                if len(endpoints) == 2:
                    left = object_labels.get(endpoints[0], endpoints[0])
                    right = object_labels.get(endpoints[1], endpoints[1])
                    expression = " = ".join(expression_tokens[1:]) if len(expression_tokens) > 2 else "fields"
                    relationships.append(f"{left} -> {right} on {expression}")
        for relationship in relationships:
            print(f"      relationship: {relationship}")
        if not relationships:
            print("      relationships: none")

    parameters = []
    for datasource in root.xpath("./datasources/datasource"):
        if datasource.get("name") == "Parameters":
            for column in datasource.findall("./column"):
                if column.get("param-domain-type"):
                    parameters.append(column)
    print(f"Parameters ({len(parameters)}):")
    for parameter in parameters:
        print(
            f"  - {parameter.get('caption', parameter.get('name'))}: "
            f"{parameter.get('datatype')} {parameter.get('param-domain-type')} "
            f"default={parameter.get('value')}"
        )

    grouped = {"basic": [], "LOD": [], "table calc": []}
    for source_id, field, formula, calculation in calculations:
        if calculation.find("./table-calc") is not None:
            bucket = "table calc"
        elif LOD_RE.search(formula):
            bucket = "LOD"
        else:
            bucket = "basic"
        grouped[bucket].append((source_id, field, formula))
    print(f"Calculations ({len(calculations)}):")
    for bucket in ("basic", "LOD", "table calc"):
        print(f"  {bucket} ({len(grouped[bucket])}):")
        for source_id, field, formula in grouped[bucket]:
            print(f"    - {source_id} {field}: {formula}")

    sets = []
    for datasource in root.xpath("./datasources/datasource"):
        for group in datasource.iter():
            if local_name(group) == "group" and (
                group.get("ui-builtin") == "set" or group.get("type") == "set"
            ):
                sets.append((datasource.get("caption", datasource.get("name")), group.get("name", "")))
    print(f"Sets ({len(sets)}):")
    for caption, name in sets:
        print(f"  - {caption}: {name}")

    worksheets = [element.get("name", "") for element in root.xpath("./worksheets/worksheet")]
    dashboards = [element.get("name", "") for element in root.xpath("./dashboards/dashboard")]
    print(f"Worksheets ({len(worksheets)}): {', '.join(worksheets)}")
    print(f"Dashboards ({len(dashboards)}): {', '.join(dashboards)}")
    actions = []
    for action in root.xpath("./actions/action"):
        command = action.find("./command")
        actions.append((action.get("caption", action.get("name", "")), command.get("command", "") if command is not None else ""))
    print(f"Actions ({len(actions)}):")
    for caption, command in actions:
        print(f"  - {caption}: {command or 'no command'}")
    if ref_issues:
        print(f"Field-reference check: FAILED ({ref_count} refs, {len(ref_issues)} unresolved)")
        for issue in ref_issues:
            print(f"  ERROR: {issue}")
    else:
        print(f"Field-reference check: OK ({ref_count} references)")
    return not ref_issues


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path, help="Path to .twb or .twbx")
    args = parser.parse_args()
    try:
        valid = inventory(args.workbook)
    except (OSError, ValueError, zipfile.BadZipFile, etree.XMLSyntaxError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
