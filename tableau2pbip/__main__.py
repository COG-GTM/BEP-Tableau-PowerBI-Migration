from __future__ import annotations

import argparse
import json
from pathlib import Path

from tableau2pbip.migrate import convert_workbook, inspect_workbook
from tableau2pbip.scaffold import scaffold_workbook


def main() -> None:
    parser = argparse.ArgumentParser(prog="tableau2pbip")
    commands = parser.add_subparsers(dest="command", required=True)
    inspect = commands.add_parser("inspect", help="Print workbook inventory as JSON")
    inspect.add_argument("workbook", type=Path)
    convert = commands.add_parser("convert", help="Convert a workbook to a PBIP stub")
    convert.add_argument("workbook", type=Path)
    convert.add_argument("--out", required=True, type=Path)
    convert.add_argument("--overrides", type=Path)
    convert.add_argument("--layout", type=Path)
    scaffold = commands.add_parser(
        "scaffold", help="Generate a starter report layout from a Tableau workbook"
    )
    scaffold.add_argument("workbook", type=Path)
    scaffold.add_argument("--out", required=True, type=Path)
    scaffold.add_argument("--force", action="store_true")
    arguments = parser.parse_args()
    if arguments.command == "inspect":
        result = inspect_workbook(arguments.workbook)
    elif arguments.command == "convert":
        result = convert_workbook(
            arguments.workbook,
            arguments.out,
            arguments.overrides,
            arguments.layout,
        )
    else:
        result = scaffold_workbook(
            arguments.workbook,
            arguments.out,
            force=arguments.force,
        )
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
