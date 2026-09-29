from __future__ import annotations

import argparse
import json
from pathlib import Path

from tableau2pbip.migrate import convert_workbook, inspect_workbook


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
    arguments = parser.parse_args()
    if arguments.command == "inspect":
        print(json.dumps(inspect_workbook(arguments.workbook), indent=2, ensure_ascii=False))
    else:
        result = convert_workbook(
            arguments.workbook,
            arguments.out,
            arguments.overrides,
            arguments.layout,
        )
    print(json.dumps(result, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
