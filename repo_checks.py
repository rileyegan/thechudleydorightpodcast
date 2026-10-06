#!/usr/bin/env python3
"""CI checks: version clarity / bump, and PII in tracked files.

Usage:
  python3 repo_checks.py version
  python3 repo_checks.py pii

On pull_request CI, the version job also compares VERSION to the base branch
(via GITHUB_BASE_REF, or pass --base). Other file changes require a higher
X.Y.Z and a CHANGELOG.md table row for the new version with Bumped true.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, NamedTuple, Optional, Sequence, Tuple

from version import VersionError, load_version, load_version_text, parse_semver

REPO_ROOT = Path(__file__).resolve().parent
VERSION_PATH = REPO_ROOT / "VERSION"
CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"
SKIP_SUFFIXES = {
    ".csv",
    ".xlsx",
    ".xls",
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".zip",
    ".gguf",
    ".bin",
    ".pyc",
}

CHANGELOG_HEADERS = ("timestamp", "type", "notes", "version", "bumped")
CHANGELOG_TYPES = frozenset(
    {"added", "changed", "fixed", "removed", "security", "docs", "chore"}
)
TABLE_SEP_CELL = re.compile(r"^:?-+:?$")
VAGUE_NOTES = {"tbd", "todo", "wip", "n/a", "...", "tba", "coming soon"}
VERSION_ONLY_FILES = {"VERSION", "CHANGELOG.md"}

# Emails on these hosts are documentation/test placeholders, not personal data.
EMAIL_OK_DOMAINS = {"example.com", "example.org", "example.net", "invalid", "localhost"}
HOME_OK_USERS = {
    "you",
    "user",
    "username",
    "your-username",
    "your_username",
    "YOUR_USER",
    "someone",
    "name",
}

EMAIL_RE = re.compile(
    r"\b[A-Z0-9._%+-]+@([A-Z0-9.-]+\.[A-Z]{2,})\b",
    re.IGNORECASE,
)
SSN_RE = re.compile(r"\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0000)\d{4}\b")
PHONE_RE = re.compile(
    r"(?<!\d)(?:\+1[-.\s])?(?:\(?\d{3}\)?[-.\s])\d{3}[-.\s]\d{4}(?!\d)"
)
AWS_KEY_RE = re.compile(r"\bAKIA[0-9A-Z]{16}\b")
GITHUB_TOKEN_RE = re.compile(r"\b(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{20,}\b")
SLACK_TOKEN_RE = re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")
OPENAI_KEY_RE = re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")
PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----")
HOME_PATH_RE = re.compile(r"(?:/Users/|/home/)([A-Za-z0-9._-]+)/")
PEM_FILE_RE = re.compile(
    r"(?:^|/)(?:id_rsa|id_dsa|id_ecdsa|id_ed25519|\.env|\.p12|\.pfx)$"
)


class Finding:
    def __init__(self, rel_path: str, line_no: int, rule: str, snippet: str) -> None:
        self.rel_path = rel_path
        self.line_no = line_no
        self.rule = rule
        self.snippet = snippet

    def format(self) -> str:
        return "{0}:{1}: {2}: {3}".format(
            self.rel_path, self.line_no, self.rule, self.snippet
        )


def _git(root: Path, args: Sequence[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root)] + list(args),
        capture_output=True,
        check=False,
    )


def tracked_rels(root: Path) -> List[str]:
    proc = _git(root, ["ls-files", "-z"])
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError("git ls-files failed in {0}: {1}".format(root, err))
    parts = proc.stdout.split(b"\0")
    return sorted(p.decode("utf-8", errors="replace") for p in parts if p)


def version_at_ref(root: Path, git_ref: str) -> Optional[str]:
    proc = _git(root, ["show", "{0}:VERSION".format(git_ref)])
    if proc.returncode != 0:
        return None
    text = proc.stdout.decode("utf-8", errors="replace")
    if not text.strip():
        return None
    return load_version_text(text)


def changed_files_since(root: Path, git_ref: str) -> List[str]:
    proc = _git(root, ["diff", "--name-only", "{0}...HEAD".format(git_ref)])
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(
            "git diff against {0} failed: {1}".format(git_ref, err)
        )
    return [line for line in proc.stdout.decode("utf-8").splitlines() if line]


def infer_base_ref(explicit: Optional[str] = None) -> Optional[str]:
    if explicit:
        return explicit
    if os.environ.get("GITHUB_EVENT_NAME") == "pull_request":
        base = (os.environ.get("GITHUB_BASE_REF") or "").strip()
        if base:
            return "origin/{0}".format(base)
    return None


class ChangelogRow(NamedTuple):
    timestamp: str
    change_type: str
    notes: str
    version: str
    bumped: bool
    line_no: int


def _split_md_row(line: str) -> Optional[List[str]]:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    parts = [part.strip() for part in stripped.strip("|").split("|")]
    return parts or None


def _is_separator_row(cells: Sequence[str]) -> bool:
    return bool(cells) and all(TABLE_SEP_CELL.match(cell) for cell in cells)


def parse_timestamp(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


def parse_bool_cell(value: str) -> Optional[bool]:
    key = value.strip().lower()
    if key == "true":
        return True
    if key == "false":
        return False
    return None


def parse_changelog_table(text: str) -> Tuple[List[ChangelogRow], List[str]]:
    """Parse the first markdown table. Returns (rows, structural errors)."""
    lines = text.replace("\r\n", "\n").split("\n")
    header_at = None
    headers: List[str] = []
    for i, line in enumerate(lines):
        cells = _split_md_row(line)
        if cells is None:
            continue
        names = tuple(cell.lower() for cell in cells)
        if names == CHANGELOG_HEADERS:
            header_at = i
            headers = cells
            break
    if header_at is None:
        return [], [
            "CHANGELOG.md must have a markdown table with columns "
            "Timestamp, Type, Notes, Version, Bumped."
        ]
    if header_at + 1 >= len(lines):
        return [], ["CHANGELOG.md table is missing a separator row and data rows."]
    sep = _split_md_row(lines[header_at + 1])
    if sep is None or not _is_separator_row(sep) or len(sep) != len(headers):
        return [], ["CHANGELOG.md table is missing a markdown separator row."]

    rows: List[ChangelogRow] = []
    errors: List[str] = []
    for line_no, line in enumerate(lines[header_at + 2 :], start=header_at + 3):
        if not line.strip():
            if rows:
                break
            continue
        cells = _split_md_row(line)
        if cells is None:
            break
        if _is_separator_row(cells):
            continue
        if len(cells) != len(headers):
            errors.append(
                "CHANGELOG.md:{0}: row must have {1} cells "
                "(Timestamp, Type, Notes, Version, Bumped).".format(
                    line_no, len(headers)
                )
            )
            continue
        timestamp, change_type, notes, version, bumped_text = cells
        row_errors: List[str] = []
        if not timestamp:
            row_errors.append("timestamp is empty")
        else:
            try:
                parse_timestamp(timestamp)
            except ValueError:
                row_errors.append(
                    "timestamp {0!r} is not an ISO date or datetime".format(timestamp)
                )
        kind = change_type.lower()
        if kind not in CHANGELOG_TYPES:
            row_errors.append(
                "type {0!r} is not one of {1}".format(
                    change_type, ", ".join(sorted(CHANGELOG_TYPES))
                )
            )
        if not notes:
            row_errors.append("notes are empty")
        try:
            parse_semver(version)
        except VersionError:
            row_errors.append("version {0!r} is not X.Y.Z".format(version))
        bumped = parse_bool_cell(bumped_text)
        if bumped is None:
            row_errors.append("bumped {0!r} must be true or false".format(bumped_text))
        if row_errors:
            errors.append(
                "CHANGELOG.md:{0}: {1}.".format(line_no, "; ".join(row_errors))
            )
            continue
        rows.append(
            ChangelogRow(
                timestamp=timestamp,
                change_type=kind,
                notes=notes,
                version=version,
                bumped=bumped,
                line_no=line_no,
            )
        )
    if not rows and not errors:
        errors.append("CHANGELOG.md table has no data rows.")
    return rows, errors


def check_changelog_table(text: str, version: str) -> List[str]:
    rows, errors = parse_changelog_table(text)
    if errors:
        return errors
    matching = [row for row in rows if row.version == version]
    if not matching:
        return [
            "CHANGELOG.md must have a table row whose Version is {0}.".format(version)
        ]
    notes = [row.notes for row in matching]
    if all(note.lower().rstrip(".") in VAGUE_NOTES for note in notes):
        return [
            "CHANGELOG.md rows for {0} are not clear "
            "(only TBD/TODO/WIP placeholders).".format(version)
        ]
    if not any(row.bumped for row in matching):
        return [
            "CHANGELOG.md has rows for {0} but none have Bumped true.".format(version)
        ]
    return []


def check_version_consistency(root: Path) -> List[str]:
    errors: List[str] = []
    version_path = root / VERSION_PATH.name
    changelog_path = root / CHANGELOG_PATH.name
    try:
        version = load_version(version_path)
    except VersionError as exc:
        return [str(exc)]
    if not changelog_path.is_file():
        return ["CHANGELOG.md is missing."]
    text = changelog_path.read_text(encoding="utf-8")
    errors.extend(check_changelog_table(text, version))
    return errors


def check_version_updated(root: Path, base_ref: str) -> List[str]:
    proc = _git(root, ["rev-parse", "--verify", base_ref])
    if proc.returncode != 0:
        return [
            "Cannot resolve base ref {0!r} to check that VERSION was updated.".format(
                base_ref
            )
        ]
    try:
        current = load_version(root / VERSION_PATH.name)
    except VersionError as exc:
        return [str(exc)]
    try:
        base_version = version_at_ref(root, base_ref)
    except VersionError as exc:
        return ["VERSION on {0} is invalid: {1}".format(base_ref, exc)]
    try:
        changed = changed_files_since(root, base_ref)
    except RuntimeError as exc:
        return [str(exc)]
    material = [path for path in changed if path not in VERSION_ONLY_FILES]
    if not material:
        if base_version is not None and parse_semver(current) <= parse_semver(
            base_version
        ):
            return [
                "VERSION is {0} on this branch and on {1}. "
                "Bump X.Y.Z when you change VERSION or CHANGELOG.md.".format(
                    current, base_ref
                )
            ]
        return []
    if base_version is None:
        return []
    if parse_semver(current) <= parse_semver(base_version):
        return [
            "Files besides VERSION/CHANGELOG.md changed since {0}, "
            "but VERSION stayed at {1}. Bump it and add a CHANGELOG.md "
            "row for the new value with Bumped true.".format(base_ref, current)
        ]
    return []


def run_version_check(root: Path, base_ref: Optional[str] = None) -> List[str]:
    errors = check_version_consistency(root)
    resolved = infer_base_ref(base_ref)
    if resolved:
        errors.extend(check_version_updated(root, resolved))
    return errors


def _snippet(line: str, limit: int = 80) -> str:
    stripped = line.strip()
    if len(stripped) <= limit:
        return stripped
    return stripped[: limit - 3] + "..."


def _email_ok(domain: str) -> bool:
    return domain.lower() in EMAIL_OK_DOMAINS


def scan_text(rel_path: str, text: str) -> List[Finding]:
    findings: List[Finding] = []
    posix = rel_path.replace("\\", "/")
    if PEM_FILE_RE.search(posix):
        findings.append(Finding(posix, 1, "secret-filename", posix))
    for line_no, line in enumerate(text.splitlines(), start=1):
        for match in EMAIL_RE.finditer(line):
            if not _email_ok(match.group(1)):
                findings.append(
                    Finding(posix, line_no, "email", _snippet(match.group(0)))
                )
        if SSN_RE.search(line):
            findings.append(Finding(posix, line_no, "ssn", _snippet(line)))
        if PHONE_RE.search(line):
            findings.append(Finding(posix, line_no, "phone", _snippet(line)))
        if AWS_KEY_RE.search(line):
            findings.append(Finding(posix, line_no, "aws-access-key", _snippet(line)))
        if GITHUB_TOKEN_RE.search(line):
            findings.append(Finding(posix, line_no, "github-token", _snippet(line)))
        if SLACK_TOKEN_RE.search(line):
            findings.append(Finding(posix, line_no, "slack-token", _snippet(line)))
        if OPENAI_KEY_RE.search(line):
            findings.append(Finding(posix, line_no, "openai-key", _snippet(line)))
        if PRIVATE_KEY_RE.search(line):
            findings.append(Finding(posix, line_no, "private-key", _snippet(line)))
        for match in HOME_PATH_RE.finditer(line):
            user = match.group(1)
            if user not in HOME_OK_USERS and user != "<user>":
                findings.append(
                    Finding(posix, line_no, "home-path", _snippet(match.group(0)))
                )
    return findings


def _looks_binary(raw: bytes) -> bool:
    return b"\0" in raw[: 8 * 1024]


def scan_tracked_pii(root: Path, rels: Optional[Iterable[str]] = None) -> List[Finding]:
    findings: List[Finding] = []
    names = list(rels) if rels is not None else tracked_rels(root)
    for rel in names:
        suffix = Path(rel).suffix.lower()
        if suffix in SKIP_SUFFIXES:
            continue
        path = root / rel
        if not path.is_file():
            continue
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        if _looks_binary(raw):
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        findings.extend(scan_text(rel, text))
    return findings


def run_pii_check(root: Path) -> List[str]:
    findings = scan_tracked_pii(root)
    return [item.format() for item in findings]


def _print_errors(label: str, errors: Sequence[str]) -> int:
    if not errors:
        print("{0}: ok".format(label))
        return 0
    print("{0}: failed ({1})".format(label, len(errors)), file=sys.stderr)
    for item in errors:
        print(item, file=sys.stderr)
    return 1


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail CI when VERSION/CHANGELOG are unclear or when tracked files look like PII."
    )
    parser.add_argument("check", choices=["version", "pii"])
    parser.add_argument(
        "--root",
        default=str(REPO_ROOT),
        help="Git checkout to scan (default: this repo)",
    )
    parser.add_argument(
        "--base",
        default=None,
        help="Git ref to compare VERSION against (default: origin/$GITHUB_BASE_REF on pull_request)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    root = Path(args.root).resolve()
    if args.check == "version":
        return _print_errors("version", run_version_check(root, args.base))
    return _print_errors("pii", run_pii_check(root))


if __name__ == "__main__":
    raise SystemExit(main())
