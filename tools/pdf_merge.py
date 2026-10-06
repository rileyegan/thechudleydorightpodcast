#!/usr/bin/env python3
# =============================================================================
# COMMAND GLOSSARY — tools this script may invoke
# -----
# python3   Runs this CLI. Here: concatenates PDF pages into one file.
# =============================================================================
"""
Merge PDFs in order (guest packet, show-notes bundle).

Ported from datastuff/apps/menards-rebates/menards_rebates/packets.py
(merge_pdfs only — rebate packet naming was not copied).

  python3 tools/pdf_merge.py -o packet.pdf bio.pdf questions.pdf
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from paths import require_module


def require_pypdf():
    module = require_module("pypdf", "pypdf")
    return module.PdfReader, module.PdfWriter


def merge_pdfs(inputs: list[Path], dest: Path) -> Path:
    PdfReader, PdfWriter = require_pypdf()
    writer = PdfWriter()
    for path in inputs:
        reader = PdfReader(str(path))
        for page in reader.pages:
            writer.add_page(page)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as handle:
        writer.write(handle)
    return dest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Concatenate PDF files.")
    parser.add_argument("pdfs", nargs="+", type=Path, help="Input PDFs in order")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=True,
        help="Merged PDF to write",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    missing = [str(path) for path in args.pdfs if not path.is_file()]
    if missing:
        print("Missing: " + ", ".join(missing), file=sys.stderr)
        return 1
    merge_pdfs(args.pdfs, args.output)
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
