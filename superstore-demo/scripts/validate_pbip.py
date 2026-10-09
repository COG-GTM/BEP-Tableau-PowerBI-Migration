"""Static validation of the generated PBIP project (no Power BI Desktop needed).

Checks: every JSON file parses and carries a $schema; every TMDL table/column/measure
parses; every field a visual references exists in the model; every [Measure] and
Table[Column] reference inside a DAX expression resolves; brackets/parentheses balance.
Exit code 1 on any failure. Writes part1-tableau-to-powerbi/validation_report.md.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
P1 = os.path.join(os.path.dirname(HERE), "part1-tableau-to-powerbi")
MODEL = os.path.join(P1, "Superstore.SemanticModel", "definition")
REPORT = os.path.join(P1, "Superstore.Report", "definition")

results = []


def check(ok, msg):
    results.append((ok, msg))
    return ok


def unq(s):
    return s.strip().strip("'")


def parse_tmdl():
    tables = {}
    for fn in sorted(os.listdir(os.path.join(MODEL, "tables"))):
        text = open(os.path.join(MODEL, "tables", fn), encoding="utf-8").read()
        m = re.search(r"^table (.+)$", text, re.M)
        if not check(bool(m), f"TMDL {fn}: has a table declaration"):
            continue
        name = unq(m.group(1))
        cols = [unq(c) for c in re.findall(r"^\tcolumn ('[^']+'|\S+)", text, re.M)]
        measures = {}
        for mm in re.finditer(r"^\tmeasure ('[^']+'|\S+) = (.+)$", text, re.M):
            measures[unq(mm.group(1))] = mm.group(2)
        check(bool(re.search(r"^\tpartition ", text, re.M)), f"TMDL {fn}: has a partition")
        tables[name] = {"columns": cols, "measures": measures}
    return tables


def check_dax(tables):
    all_measures = {m for t in tables.values() for m in t["measures"]}
    for tname, t in tables.items():
        for mname, expr in t["measures"].items():
            check(expr.count("(") == expr.count(")") and expr.count("[") == expr.count("]"),
                  f"DAX [{mname}]: balanced parentheses and brackets")
            for ref_t, ref_c in re.findall(r"('[^']+'|\b[A-Za-z_][\w]*)\[([^\]]+)\]", expr):
                ref_t = unq(ref_t)
                if ref_t in ("VAR", "RETURN", "IF", "SELECTEDVALUE", "CALCULATE"):
                    continue
                check(ref_t in tables and ref_c in tables[ref_t]["columns"],
                      f"DAX [{mname}]: column {ref_t}[{ref_c}] exists")
            for ref_m in re.findall(r"(?<![\w'\]])\[([^\]]+)\]", expr):
                check(ref_m in all_measures, f"DAX [{mname}]: measure [{ref_m}] exists")


def check_json_tree(root):
    n = 0
    for dp, _, files in os.walk(root):
        for f in files:
            if f.endswith((".json", ".pbir", ".pbism", ".pbip", ".platform")):
                p = os.path.join(dp, f)
                try:
                    d = json.load(open(p, encoding="utf-8"))
                    check("$schema" in d, f"JSON {os.path.relpath(p, P1)}: declares $schema")
                    n += 1
                except json.JSONDecodeError as e:
                    check(False, f"JSON {os.path.relpath(p, P1)}: parses ({e})")
    return n


def check_visuals(tables):
    pages = json.load(open(os.path.join(REPORT, "pages", "pages.json")))
    for pg in pages["pageOrder"]:
        pdir = os.path.join(REPORT, "pages", pg)
        check(os.path.exists(os.path.join(pdir, "page.json")), f"page '{pg}' listed in pages.json exists")
        vdir = os.path.join(pdir, "visuals")
        for vn in sorted(os.listdir(vdir)):
            v = json.load(open(os.path.join(vdir, vn, "visual.json")))
            check(v["name"] == vn, f"visual {pg}/{vn}: folder name matches visual name")
            vt = v["visual"]["visualType"]
            for role, spec in v["visual"]["query"]["queryState"].items():
                for proj in spec["projections"]:
                    kind, body = next(iter(proj["field"].items()))
                    ent, prop = body["Expression"]["SourceRef"]["Entity"], body["Property"]
                    if kind == "Measure":
                        ok = ent in tables and prop in tables[ent]["measures"]
                    else:
                        ok = ent in tables and prop in tables[ent]["columns"]
                    check(ok, f"visual {pg}/{vt} ({role}): {kind} {ent}[{prop}] exists in model")


def main():
    tables = parse_tmdl()
    check_dax(tables)
    n = check_json_tree(os.path.dirname(MODEL)) + check_json_tree(os.path.dirname(REPORT))
    check_visuals(tables)
    rels = open(os.path.join(MODEL, "relationships.tmdl")).read()
    for ft, fc, tt, tc in re.findall(r"fromColumn: (\S+)\.'([^']+)'\n\ttoColumn: (\S+)\.'([^']+)'", rels):
        check(fc in tables[ft]["columns"] and tc in tables[tt]["columns"], f"relationship {ft}[{fc}] -> {tt}[{tc}] columns exist")

    passed = sum(1 for ok, _ in results if ok)
    failed = [m for ok, m in results if not ok]
    n_meas = sum(len(t["measures"]) for t in tables.values())
    lines = ["# PBIP validation report", "",
             f"- Tables: {len(tables)}  |  Measures: {n_meas}  |  JSON documents: {n}",
             f"- Checks passed: {passed}/{len(results)}", ""]
    if failed:
        lines += ["## Failures", ""] + [f"- {m}" for m in failed]
    else:
        lines += ["All checks passed.", ""]
    lines += ["", "## What was checked", "",
              "- every JSON/PBIR/PBISM file parses and declares `$schema`",
              "- every TMDL table has a partition; every measure's DAX has balanced `()`/`[]`",
              "- every `Table[Column]` and `[Measure]` referenced in DAX resolves to the model",
              "- every field bound to a report visual resolves to a model column or measure",
              "- every relationship end points at an existing column",
              "", "Not checked here (needs Power BI Desktop / Fabric): DAX evaluation, rendering. Number parity is covered by `scripts/number_check.py`."]
    open(os.path.join(P1, "validation_report.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
