#!/usr/bin/env python3
# =============================================================================
# COMMAND GLOSSARY — tools this script may invoke
# -----
# python3   Runs this checker. Here: verifies vendored libs and ffmpeg.
# ffmpeg    Optional self-test convert of a short silent WAV.
# =============================================================================
"""
Report whether the ported document/audio helpers can run.

Does not read your show files.

  python3 tools/check_tools.py
  python3 tools/check_tools.py --self-test
"""

from __future__ import annotations

import argparse
import tempfile
import wave
from pathlib import Path

from paths import PIP_HINT, require_module, setup_python_path


def _ok(name: str, detail: str) -> None:
    print(f"[OK]   {name}: {detail}")


def _need(name: str, detail: str) -> None:
    print(f"[NEED] {name}: {detail}")


def check_python_modules() -> list[str]:
    setup_python_path()
    issues: list[str] = []
    mapping = {
        "pypdf": "pypdf",
        "openpyxl": "openpyxl",
        "docx": "python-docx",
    }
    for module_name, pip_name in mapping.items():
        try:
            require_module(module_name, pip_name)
            _ok(pip_name, "import ok")
        except SystemExit:
            issues.append(pip_name)
            _need(pip_name, "not importable")
    if issues:
        issues.append(PIP_HINT)
    return issues


def check_ffmpeg() -> list[str]:
    from convert_audio import FFMPEG_HINT, ffmpeg_path

    found = ffmpeg_path()
    if found:
        _ok("ffmpeg", found)
        return []
    _need("ffmpeg", "not on PATH")
    return [FFMPEG_HINT]


def write_silence_wav(path: Path, *, seconds: float = 0.05, rate: int = 44100) -> None:
    frames = int(rate * seconds)
    with wave.open(str(path), "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\x00\x00" * frames)


def self_test() -> list[str]:
    from convert_audio import convert_audio, ffmpeg_path
    from docx_io import extract_docx_text, write_docx_from_text
    from pdf_merge import merge_pdfs
    from pypdf import PdfReader, PdfWriter
    from xlsx_io import extract_xlsx_text, write_xlsx_from_csv

    issues: list[str] = []
    with tempfile.TemporaryDirectory() as raw:
        folder = Path(raw)

        first = folder / "a.pdf"
        second = folder / "b.pdf"
        merged = folder / "merged.pdf"
        for dest in (first, second):
            writer = PdfWriter()
            writer.add_blank_page(width=72, height=72)
            with dest.open("wb") as handle:
                writer.write(handle)
        merge_pdfs([first, second], merged)
        if len(PdfReader(str(merged)).pages) != 2:
            issues.append("pdf merge did not produce 2 pages")
        else:
            _ok("pdf merge", "2-page round trip")

        source_text = folder / "notes.txt"
        docx = folder / "notes.docx"
        source_text.write_text("Host A\nHost B\n", encoding="utf-8")
        write_docx_from_text(source_text.read_text(encoding="utf-8"), docx)
        dumped = extract_docx_text(docx)
        if "Host A" not in dumped or "Host B" not in dumped:
            issues.append("docx round trip lost paragraph text")
        else:
            _ok("docx", "round trip")

        csv_path = folder / "rundown.csv"
        xlsx = folder / "rundown.xlsx"
        csv_path.write_text("item,who\nintro,Riley\n", encoding="utf-8")
        write_xlsx_from_csv(csv_path, xlsx)
        table = extract_xlsx_text(xlsx)
        if "intro" not in table or "Riley" not in table:
            issues.append("xlsx round trip lost cells")
        else:
            _ok("xlsx", "round trip")

        if ffmpeg_path():
            wav = folder / "silence.wav"
            mp3 = folder / "silence.mp3"
            write_silence_wav(wav)
            convert_audio(wav, mp3, overwrite=True)
            if not mp3.is_file() or mp3.stat().st_size == 0:
                issues.append("ffmpeg produced an empty mp3")
            else:
                _ok("ffmpeg convert", "wav → mp3")
        else:
            _need("ffmpeg convert", "skipped (ffmpeg missing)")

    return issues


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify podcast document/audio helper dependencies."
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Write tiny temp files and round-trip PDF/DOCX/XLSX (and WAV→MP3 if ffmpeg exists).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    print("The Chudley Do Right Podcast — document/audio tool check")
    issues = check_python_modules()
    if args.self_test:
        if any(item in {"pypdf", "openpyxl", "python-docx"} for item in issues):
            print("Skipping --self-test until Python packages install.")
        else:
            issues.extend(self_test())
    issues.extend(check_ffmpeg())
    if issues:
        print()
        for issue in issues:
            for line in str(issue).splitlines():
                print(f"       → {line}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
