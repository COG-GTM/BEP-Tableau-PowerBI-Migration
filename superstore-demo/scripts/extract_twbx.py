"""Step 1 of the Tableau -> BI migration: open the .twbx, pull the embedded
Hyper extract out as CSV files, and write a plain inventory of what the
workbook contains (data sources, fields, calculated fields, parameters,
worksheets, dashboards).

Usage: python scripts/extract_twbx.py "../course/tableau-files/Section 15 - Tableau Sales & Customer Dashboards.twbx"
Outputs: data/*.csv, part1-tableau-to-powerbi/inventory.json, inventory.md
"""
import csv
import glob
import json
import os
import re
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET

from tableauhyperapi import Connection, HyperProcess, Telemetry

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA_DIR = os.path.join(ROOT, "data")
PART1_DIR = os.path.join(ROOT, "part1-tableau-to-powerbi")


def export_hyper_tables(hyper_path):
    exported = {}
    with HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp, \
            Connection(hp.endpoint, hyper_path) as conn:
        for schema in conn.catalog.get_schema_names():
            for table in conn.catalog.get_table_names(schema):
                raw_name = table.name.unescaped
                short = re.sub(r"\.csv_[0-9A-F]+$", "", raw_name).lower()
                defn = conn.catalog.get_table_definition(table)
                cols = [c.name.unescaped for c in defn.columns]
                rows = conn.execute_list_query(f"SELECT * FROM {table}")
                out = os.path.join(DATA_DIR, f"{short}.csv")
                with open(out, "w", newline="", encoding="utf-8") as fh:
                    w = csv.writer(fh)
                    w.writerow(cols)
                    for r in rows:
                        w.writerow(r)
                exported[short] = {
                    "file": os.path.relpath(out, ROOT),
                    "rows": len(rows),
                    "columns": [{"name": c.name.unescaped, "type": str(c.type)} for c in defn.columns],
                }
    return exported


def parse_workbook(twb_path):
    tree = ET.parse(twb_path)
    root = tree.getroot()

    # Map internal calc names -> captions so formulas become readable.
    name_to_caption = {}
    for col in root.iter("column"):
        if col.get("name") and col.get("caption"):
            name_to_caption[col.get("name")] = col.get("caption")

    def readable(formula):
        def repl(m):
            return "[" + name_to_caption.get(m.group(0), m.group(1)) + "]"
        return re.sub(r"\[([^\]]+)\]", repl, formula)

    AGG = {"sum": "SUM", "ctd": "COUNTD", "cnt": "COUNT", "avg": "AVG", "mn": "MIN", "mx": "MAX",
           "usr": "", "none": "", "yr": "YEAR", "qr": "QUARTER", "mnth": "MONTH", "wk": "WEEK",
           "tmn": "MIN", "tmx": "MAX", "nk": ""}

    def readable_shelf(shelf):
        # Shelf syntax: [datasource].[agg:FieldName:qk] (+ ...). Turn it into SUM([Sales]).
        def repl(m):
            agg, field = m.group(1), m.group(2)
            field = name_to_caption.get("[" + field + "]", field)
            fn = AGG.get(agg, agg.upper())
            return f"{fn}([{field}])" if fn else f"[{field}]"
        out = re.sub(r"\[[^\]]+\]\.\[(\w+):([^:\]]+):[a-z]+\]", repl, shelf)
        out = re.sub(r"\[[^\]]+\]\.\[([^\]]+)\]", r"[\1]", out)
        return out

    datasources, parameters, calcs, seen = [], [], [], set()
    for ds in root.find("datasources"):
        ds_name = ds.get("caption") or ds.get("name")
        conns = [
            {"class": c.get("class"), "filename": c.get("filename"), "dbname": c.get("dbname")}
            for c in ds.iter("connection")
            if c.get("class") not in (None, "federated")
        ]
        relations = sorted({r.get("name") for r in ds.iter("relation") if r.get("name") and r.get("type") == "table"})
        plain_fields = []
        for col in ds.findall("column"):
            calc = col.find("calculation")
            caption = col.get("caption") or col.get("name").strip("[]")
            if ds.get("name") == "Parameters":
                members = [m.get("value") for m in col.iter("member")]
                parameters.append({
                    "name": caption,
                    "datatype": col.get("datatype"),
                    "default": col.get("value"),
                    "allowed_values": members,
                })
            elif calc is not None and calc.get("formula") is not None:
                key = (ds_name, caption)
                if key in seen:
                    continue
                seen.add(key)
                calcs.append({
                    "name": caption,
                    "datatype": col.get("datatype"),
                    "role": col.get("role"),
                    "formula": readable(calc.get("formula")),
                })
            else:
                plain_fields.append({
                    "name": caption,
                    "datatype": col.get("datatype"),
                    "role": col.get("role"),
                })
        datasources.append({
            "name": ds_name,
            "connections": conns,
            "tables": relations,
            "fields": plain_fields,
        })

    worksheets = []
    for ws in root.find("worksheets"):
        deps = set()
        for dep in ws.iter("datasource-dependencies"):
            for col in dep.findall("column"):
                deps.add(col.get("caption") or col.get("name").strip("[]"))
        marks = [m.get("class") for m in ws.iter("mark") if m.get("class")]
        rows = ws.find(".//rows")
        cols = ws.find(".//cols")
        worksheets.append({
            "name": ws.get("name"),
            "mark_type": marks[0] if marks else "Automatic",
            "rows_shelf": readable_shelf(rows.text or "") if rows is not None else "",
            "cols_shelf": readable_shelf(cols.text or "") if cols is not None else "",
            "fields_used": sorted(deps),
        })

    dashboards = []
    for db in root.find("dashboards"):
        size = db.find("size")
        zones = [z.get("name") for z in db.iter("zone") if z.get("name")]
        dashboards.append({
            "name": db.get("name"),
            "size": {"w": size.get("maxwidth"), "h": size.get("maxheight")} if size is not None else None,
            "worksheets": sorted(set(zones)),
        })

    return {
        "workbook": os.path.basename(twb_path),
        "tableau_version": root.get("source-build"),
        "datasources": datasources,
        "parameters": parameters,
        "calculated_fields": calcs,
        "worksheets": worksheets,
        "dashboards": dashboards,
    }


def write_markdown(inv, path):
    L = [f"# Tableau workbook inventory: {inv['workbook']}", ""]
    L.append(f"Built with Tableau {inv['tableau_version']}.")
    L.append("")
    L.append("## Data")
    for n, t in inv["tables"].items():
        L.append(f"- `{n}` — {t['rows']:,} rows, {len(t['columns'])} columns → `{t['file']}`")
    L.append("")
    L.append("## Parameters")
    for p in inv["parameters"]:
        L.append(f"- **{p['name']}** ({p['datatype']}), default `{p['default']}`, values {p['allowed_values']}")
    L.append("")
    L.append(f"## Calculated fields ({len(inv['calculated_fields'])})")
    L.append("")
    L.append("| Name | Type | Tableau formula |")
    L.append("|---|---|---|")
    for c in inv["calculated_fields"]:
        f = c["formula"].replace("\r\n", " ").replace("\n", " ").replace("|", "\\|")
        L.append(f"| {c['name']} | {c['datatype']} | `{f}` |")
    L.append("")
    L.append(f"## Worksheets ({len(inv['worksheets'])})")
    L.append("")
    L.append("| Worksheet | Mark | Columns shelf | Rows shelf |")
    L.append("|---|---|---|---|")
    for w in inv["worksheets"]:
        L.append(f"| {w['name']} | {w['mark_type']} | `{w['cols_shelf']}` | `{w['rows_shelf']}` |")
    L.append("")
    L.append(f"## Dashboards ({len(inv['dashboards'])})")
    for d in inv["dashboards"]:
        L.append(f"- **{d['name']}** ({d['size']['w']}x{d['size']['h']}): " + ", ".join(d["worksheets"]))
    L.append("")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))


def main(twbx):
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(PART1_DIR, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(twbx) as z:
            z.extractall(tmp)
        twb = glob.glob(os.path.join(tmp, "*.twb"))[0]
        hyper = glob.glob(os.path.join(tmp, "**", "*.hyper"), recursive=True)[0]
        inv = parse_workbook(twb)
        inv["tables"] = export_hyper_tables(hyper)
    with open(os.path.join(PART1_DIR, "inventory.json"), "w", encoding="utf-8") as fh:
        json.dump(inv, fh, indent=2)
    write_markdown(inv, os.path.join(PART1_DIR, "inventory.md"))
    print(f"tables: {list(inv['tables'])}")
    print(f"calculated fields: {len(inv['calculated_fields'])}, worksheets: {len(inv['worksheets'])}, dashboards: {len(inv['dashboards'])}")


if __name__ == "__main__":
    main(sys.argv[1])
