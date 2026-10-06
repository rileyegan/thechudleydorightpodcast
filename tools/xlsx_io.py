#!/usr/bin/env python3
# =============================================================================
# COMMAND GLOSSARY — tools this script may invoke
# -----
# python3   Runs this CLI. Here: dumps or builds an Excel workbook.
# =============================================================================
"""
Read or write .xlsx workbooks.

Uses openpyxl the same way datastuff Excel exporters do, without the
statement pipeline or pandas.

  python3 tools/xlsx_io.py dump rundown.xlsx
  python3 tools/xlsx_io.py from-csv rundown.csv rundown.xlsx
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from paths import require_module


def require_openpyxl():
    return require_module("openpyxl", "openpyxl")


def extract_xlsx_text(path: Path) -> str:
    openpyxl = require_openpyxl()
    workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
    blocks: list[str] = []
    try:
        for sheet in workbook.worksheets:
            blocks.append(f"# {sheet.title}")
            for row in sheet.iter_rows(values_only=True):
                cells = ["" if cell is None else str(cell) for cell in row]
                if any(cell.strip() for cell in cells):
                    blocks.append("\t".join(cells))
            blocks.append("")
    finally:
        workbook.close()
    return "\n".join(blocks).rstrip() + "\n"


def write_xlsx_from_csv(source: Path, dest: Path, *, sheet_name: str = "Sheet1") -> Path:
    openpyxl = require_openpyxl()
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = sheet_name[:31] or "Sheet1"
    with source.open(newline="", encoding="utf-8") as handle:
        for row in csv.reader(handle):
            sheet.append(row)
    dest.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(dest)
    return dest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dump or create an .xlsx file.")
    sub = parser.add_subparsers(dest="command", required=True)

    dump = sub.add_parser("dump", help="Print sheets as tab-separated text")
    dump.add_argument("xlsx", type=Path)

    writer = sub.add_parser("from-csv", help="Write a CSV file to .xlsx")
    writer.add_argument("csv", type=Path)
    writer.add_argument("xlsx", type=Path)
    writer.add_argument("--sheet", default="Sheet1")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "dump":
        if not args.xlsx.is_file():
            print(f"Not a file: {args.xlsx}", file=sys.stderr)
            return 1
        sys.stdout.write(extract_xlsx_text(args.xlsx))
        return 0

    if not args.csv.is_file():
        print(f"Not a file: {args.csv}", file=sys.stderr)
        return 1
    write_xlsx_from_csv(args.csv, args.xlsx, sheet_name=args.sheet)
    print(f"Wrote {args.xlsx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
