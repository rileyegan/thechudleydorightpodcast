"""Single source of truth for this repo's release number (`VERSION`)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent
VERSION_PATH = REPO_ROOT / "VERSION"

SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


class VersionError(RuntimeError):
    """VERSION is missing, empty, or not a clear X.Y.Z value."""


def parse_semver(text: str) -> Tuple[int, int, int]:
    stripped = text.strip()
    match = SEMVER.match(stripped)
    if not match:
        raise VersionError(
            "VERSION must be a single X.Y.Z line (got {0!r}).".format(stripped)
        )
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def load_version_text(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) != 1:
        raise VersionError("VERSION must contain exactly one non-empty line.")
    parse_semver(lines[0])
    return lines[0]


def load_version(path: Optional[Path] = None) -> str:
    """Return the version string. *path* defaults to this repo's VERSION file."""
    target = path if path is not None else VERSION_PATH
    if not target.is_file():
        raise VersionError("VERSION file is missing: {0}".format(target))
    return load_version_text(target.read_text(encoding="utf-8"))


__version__ = load_version()
