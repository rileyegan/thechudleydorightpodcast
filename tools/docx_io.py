#!/usr/bin/env python3
# =============================================================================
# COMMAND GLOSSARY — tools this script may invoke
# -----
# python3   Runs this CLI. Here: reads or writes a Word .docx.
# =============================================================================
"""
Read or write Word documents.

Read path is new. Write path follows datastuff/riley-job-stuff
(python-docx Document + paragraphs). Resume/cover templates and contact
PII were not copied.

  python3 tools/docx_io.py dump notes.docx
  python3 tools/docx_io.py from-text notes.txt notes.docx
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from paths import require_module


def require_docx():
    return require_module("docx", "python-docx")


def extract_docx_text(path: Path) -> str:
    document = require_docx().Document(str(path))
    parts: list[str] = [paragraph.text for paragraph in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            parts.append("\t".join(cell.text for cell in row.cells))
    return "\n".join(parts)


def write_docx_from_text(text: str, dest: Path) -> Path:
    document = require_docx().Document()
    body = text.replace("\r\n", "\n")
    if not body.endswith("\n"):
        body += "\n"
    for block in body.split("\n"):
        document.add_paragraph(block)
    dest.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(dest))
    return dest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Dump or create a .docx file.")
    sub = parser.add_subparsers(dest="command", required=True)

    dump = sub.add_parser("dump", help="Print paragraph and table text")
    dump.add_argument("docx", type=Path)

    writer = sub.add_parser("from-text", help="Write a plaintext file to .docx")
    writer.add_argument("text", type=Path)
    writer.add_argument("docx", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "dump":
        if not args.docx.is_file():
            print(f"Not a file: {args.docx}", file=sys.stderr)
            return 1
        text = extract_docx_text(args.docx)
        sys.stdout.write(text)
        if text and not text.endswith("\n"):
            sys.stdout.write("\n")
        return 0

    if not args.text.is_file():
        print(f"Not a file: {args.text}", file=sys.stderr)
        return 1
    write_docx_from_text(args.text.read_text(encoding="utf-8"), args.docx)
    print(f"Wrote {args.docx}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
