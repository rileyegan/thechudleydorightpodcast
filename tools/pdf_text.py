#!/usr/bin/env python3
# =============================================================================
# COMMAND GLOSSARY — tools this script may invoke
# -----
# python3   Runs this CLI. Here: extracts text from a PDF.
# =============================================================================
"""
Extract text from a PDF (guest notes, research, contracts).

Ported from datastuff/scripts/pdf-text.py. Chase/Amex row helpers were not copied.

  python3 tools/pdf_text.py show-notes.pdf
  python3 tools/pdf_text.py show-notes.pdf -o show-notes.txt
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from paths import require_module


def require_pypdf():
    module = require_module("pypdf", "pypdf")
    return module.PdfReader


def extract_pdf_text(path: Path) -> str:
    PdfReader = require_pypdf()
    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract text from a PDF with pypdf."
    )
    parser.add_argument("pdf", type=Path, help="Input PDF")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write text here instead of stdout",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.pdf.is_file():
        print(f"Not a file: {args.pdf}", file=sys.stderr)
        return 1
    text = extract_pdf_text(args.pdf)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(f"Wrote {args.output}")
        return 0
    sys.stdout.write(text)
    if text and not text.endswith("\n"):
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
