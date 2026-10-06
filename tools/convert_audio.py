#!/usr/bin/env python3
# =============================================================================
# COMMAND GLOSSARY — tools this script may invoke
# -----
# python3   Runs this CLI. Here: wraps ffmpeg for audio extract/convert.
# ffmpeg    Converts or remuxes audio. Here: OBS/Resolve files → mp3/wav/m4a.
# =============================================================================
"""
Convert or extract audio with ffmpeg.

Uses the same ffmpeg invocation style as
datastuff/soundcloud-likes-downloader (no shell=True, -y, -loglevel error).
The SoundCloud downloader itself was not copied.

Decoding a lossy file to .wav is not a lossless upgrade — this prints a
warning, matching that downloader's "never fake-convert" rule.

  python3 tools/convert_audio.py mix.mkv -o episode.mp3
  python3 tools/convert_audio.py host-a.wav --to mp3
  python3 tools/convert_audio.py mix.mkv -o mix.m4a --copy
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

FFMPEG_HINT = (
    "ffmpeg is required. On macOS: brew install ffmpeg. "
    "On Ubuntu: sudo apt install ffmpeg. "
    "On Windows: winget install Gyan.FFmpeg."
)
LOSSY_SUFFIXES = {".mp3", ".m4a", ".aac", ".ogg", ".opus", ".wma"}
LOSSLESS_SUFFIXES = {".wav", ".aiff", ".aif", ".flac", ".alac"}
AUDIO_ENCODERS = {
    ".mp3": ["-c:a", "libmp3lame", "-q:a", "2"],
    ".m4a": ["-c:a", "aac", "-b:a", "192k"],
    ".aac": ["-c:a", "aac", "-b:a", "192k"],
    ".wav": ["-c:a", "pcm_s16le", "-ar", "44100"],
    ".flac": ["-c:a", "flac"],
}


def ffmpeg_path() -> str | None:
    return shutil.which("ffmpeg")


def convert_audio(
    source: Path,
    dest: Path,
    *,
    copy: bool = False,
    overwrite: bool = False,
) -> Path:
    binary = ffmpeg_path()
    if not binary:
        raise SystemExit(FFMPEG_HINT)
    if dest.exists() and not overwrite:
        raise SystemExit(f"Refusing to overwrite {dest} (pass --overwrite)")

    suffix = dest.suffix.lower()
    if copy:
        codec = ["-c", "copy"]
    else:
        encoder = AUDIO_ENCODERS.get(suffix)
        if encoder is None:
            raise SystemExit(
                f"Unsupported output type {suffix}. Use "
                + ", ".join(sorted(AUDIO_ENCODERS))
            )
        codec = encoder

    dest.parent.mkdir(parents=True, exist_ok=True)
    command = [
        binary,
        "-y",
        "-loglevel",
        "error",
        "-i",
        str(source),
        "-vn",
        *codec,
        str(dest),
    ]
    # Safety: argv list only; never shell=True; never pipes a remote script.
    proc = subprocess.run(command, capture_output=True, text=True)
    if proc.returncode != 0 or not dest.exists():
        err = (proc.stderr or proc.stdout or "").strip()[:400]
        raise SystemExit(f"ffmpeg failed: {err or 'no output file'}")
    return dest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract/convert audio with ffmpeg (podcast publish helper)."
    )
    parser.add_argument("source", type=Path, help="Input audio or video file")
    parser.add_argument("-o", "--output", type=Path, help="Destination file")
    parser.add_argument(
        "--to",
        choices=sorted(ext.lstrip(".") for ext in AUDIO_ENCODERS),
        help="Output type when --output is omitted (replaces the suffix)",
    )
    parser.add_argument(
        "--copy",
        action="store_true",
        help="Remux with -c copy (no re-encode; fails if codecs do not match)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the destination if it already exists",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.source.is_file():
        print(f"Not a file: {args.source}", file=sys.stderr)
        return 1
    dest = args.output
    if dest is None:
        if not args.to:
            print("Pass -o dest or --to mp3|wav|m4a|aac|flac", file=sys.stderr)
            return 1
        dest = args.source.with_suffix("." + args.to)
    dest_suffix = dest.suffix.lower()
    src_suffix = args.source.suffix.lower()
    if dest_suffix in LOSSLESS_SUFFIXES and src_suffix in LOSSY_SUFFIXES:
        print(
            "Note: this decodes a lossy file to a lossless container. "
            "It does not restore original quality.",
            file=sys.stderr,
        )
    convert_audio(args.source, dest, copy=args.copy, overwrite=args.overwrite)
    print(f"Wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
