"""
Shared paths and vendor imports for podcast document/audio helpers.

Ported from datastuff/scripts/paths.py (vendor-on-sys.path pattern only).
Bank-statement folders and pipeline paths were not copied.

Run CLIs from the repo root, for example:
  python3 tools/pdf_text.py notes.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT: Path = Path(__file__).resolve().parents[1]
TOOLS_DIR: Path = Path(__file__).resolve().parent
VENDOR: Path = REPO_ROOT / "vendor"
REQUIREMENTS: Path = REPO_ROOT / "requirements.txt"

PIP_HINT = (
    "From the repo root:\n"
    "  python3 -m pip install -r requirements.txt -t vendor\n"
    "or: python3 -m pip install -r requirements.txt"
)


def setup_python_path() -> None:
    """Vendor packages first, then this directory for local imports."""
    for folder in (VENDOR, TOOLS_DIR):
        if folder.is_dir():
            rendered = str(folder)
            if rendered not in sys.path:
                sys.path.insert(0, rendered)


def require_module(module_name: str, pip_name: str):
    """Import a vendored package or exit with the same install hint datastuff uses."""
    setup_python_path()
    try:
        return __import__(module_name)
    except ImportError as exc:
        raise SystemExit(
            f"{pip_name} is required. {PIP_HINT}"
        ) from exc
