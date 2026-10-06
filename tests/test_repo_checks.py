from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from repo_checks import (
    check_version_consistency,
    check_version_updated,
    parse_changelog_table,
    run_pii_check,
    run_version_check,
    scan_text,
    scan_tracked_pii,
)
from tests.conftest import init_git_repo
from version import VersionError, load_version, load_version_text, parse_semver

REPO_ROOT = Path(__file__).resolve().parents[1]

CHANGELOG_OK = (
    "# Changelog\n\n"
    "| Timestamp | Type | Notes | Version | Bumped |\n"
    "| --- | --- | --- | --- | --- |\n"
    "| 2026-08-15 | added | first release notes that are actually specific. | 0.1.0 | true |\n"
)


def _write_versioned_repo(root: Path, version: str = "0.1.0") -> None:
    changelog = CHANGELOG_OK.replace("0.1.0", version)
    (root / "VERSION").write_text(version + "\n", encoding="utf-8")
    (root / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
    (root / "app.py").write_text("print({0!r})\n".format(version), encoding="utf-8")


def _commit(repo: Path, message: str) -> None:
    subprocess.run(["git", "add", "-A"], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=str(repo),
        check=True,
        capture_output=True,
    )


def test_parse_semver_rejects_unclear_values():
    with pytest.raises(VersionError, match="X.Y.Z"):
        parse_semver("1.0")
    with pytest.raises(VersionError, match="X.Y.Z"):
        parse_semver("v0.1.0")
    with pytest.raises(VersionError, match="X.Y.Z"):
        parse_semver("latest")


def test_load_version_text_requires_one_line():
    with pytest.raises(VersionError, match="exactly one"):
        load_version_text("0.1.0\n0.2.0\n")
    assert load_version_text("0.1.0\n") == "0.1.0"


def test_load_version_from_this_repo():
    assert parse_semver(load_version()) == (0, 1, 0)


def test_consistency_ok(tmp_path: Path):
    _write_versioned_repo(tmp_path)
    assert check_version_consistency(tmp_path) == []


def test_parse_changelog_accepts_iso_datetime():
    text = (
        "# Changelog\n\n"
        "| Timestamp | Type | Notes | Version | Bumped |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 2026-08-15T20:17:00-05:00 | changed | table format notes that are specific. | 0.1.0 | false |\n"
        "| 2026-08-15T00:00:00Z | added | first release notes that are actually specific. | 0.1.0 | true |\n"
    )
    rows, errors = parse_changelog_table(text)
    assert errors == []
    assert [row.change_type for row in rows] == ["changed", "added"]
    assert rows[0].bumped is False
    assert rows[1].bumped is True


def test_this_repo_changelog_matches_version():
    assert check_version_consistency(REPO_ROOT) == []
    rows, errors = parse_changelog_table(
        (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    )
    assert errors == []
    assert rows
    assert any(row.version == load_version() and row.bumped for row in rows)


def test_consistency_fails_without_changelog_table(tmp_path: Path):
    (tmp_path / "VERSION").write_text("0.1.0\n", encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [0.1.0]\n\n- notes\n",
        encoding="utf-8",
    )
    errors = check_version_consistency(tmp_path)
    assert errors
    assert any("table" in item.lower() for item in errors)


def test_consistency_fails_without_timestamp(tmp_path: Path):
    (tmp_path / "VERSION").write_text("0.1.0\n", encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n"
        "| Timestamp | Type | Notes | Version | Bumped |\n"
        "| --- | --- | --- | --- | --- |\n"
        "|  | added | notes that are actually specific. | 0.1.0 | true |\n",
        encoding="utf-8",
    )
    errors = check_version_consistency(tmp_path)
    assert errors
    assert any("timestamp" in item.lower() for item in errors)


def test_consistency_fails_unknown_type(tmp_path: Path):
    (tmp_path / "VERSION").write_text("0.1.0\n", encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n"
        "| Timestamp | Type | Notes | Version | Bumped |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 2026-08-15 | tweak | notes that are actually specific. | 0.1.0 | true |\n",
        encoding="utf-8",
    )
    errors = check_version_consistency(tmp_path)
    assert errors
    assert any("type" in item.lower() for item in errors)


def test_consistency_fails_bad_bumped(tmp_path: Path):
    (tmp_path / "VERSION").write_text("0.1.0\n", encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n"
        "| Timestamp | Type | Notes | Version | Bumped |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 2026-08-15 | added | notes that are actually specific. | 0.1.0 | yes |\n",
        encoding="utf-8",
    )
    errors = check_version_consistency(tmp_path)
    assert errors
    assert any("bumped" in item.lower() for item in errors)


def test_consistency_fails_vague_changelog(tmp_path: Path):
    (tmp_path / "VERSION").write_text("0.1.0\n", encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n"
        "| Timestamp | Type | Notes | Version | Bumped |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 2026-08-15 | added | TBD | 0.1.0 | true |\n"
        "| 2026-08-15 | added | TODO | 0.1.0 | false |\n",
        encoding="utf-8",
    )
    errors = check_version_consistency(tmp_path)
    assert errors
    assert any("not clear" in item for item in errors)


def test_consistency_fails_without_bumped_row(tmp_path: Path):
    (tmp_path / "VERSION").write_text("0.1.0\n", encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(
        "# Changelog\n\n"
        "| Timestamp | Type | Notes | Version | Bumped |\n"
        "| --- | --- | --- | --- | --- |\n"
        "| 2026-08-15 | added | notes that are actually specific. | 0.1.0 | false |\n",
        encoding="utf-8",
    )
    errors = check_version_consistency(tmp_path)
    assert errors
    assert any("Bumped true" in item for item in errors)


def test_consistency_fails_when_changelog_version_differs(tmp_path: Path):
    (tmp_path / "VERSION").write_text("0.2.0\n", encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(CHANGELOG_OK, encoding="utf-8")
    errors = check_version_consistency(tmp_path)
    assert any("0.2.0" in item for item in errors)


def test_version_must_increase_when_code_changes(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_versioned_repo(repo, "0.1.0")
    init_git_repo(repo)
    (repo / "app.py").write_text("print('changed')\n", encoding="utf-8")
    _commit(repo, "change app")
    errors = check_version_updated(repo, "HEAD~1")
    assert errors
    assert any("Bump" in item for item in errors)


def test_version_increase_allows_code_changes(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _write_versioned_repo(repo, "0.1.0")
    init_git_repo(repo)
    _write_versioned_repo(repo, "0.1.1")
    (repo / "app.py").write_text("print('changed')\n", encoding="utf-8")
    _commit(repo, "bump")
    assert check_version_updated(repo, "HEAD~1") == []
    assert run_version_check(repo, "HEAD~1") == []


def test_first_version_on_branch_without_base_file_is_ok(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "app.py").write_text("print(1)\n", encoding="utf-8")
    init_git_repo(repo)
    _write_versioned_repo(repo, "0.1.0")
    _commit(repo, "add version")
    assert check_version_updated(repo, "HEAD~1") == []


def test_scan_text_flags_email_ssn_home_and_secrets():
    email = "name@" + "host.tld"
    ssn = "-".join(["078", "05", "1120"])
    phone = "(" + "555) " + "010-0100"
    aws = "AKIA" + ("A" * 16)
    home = "/Users/" + "alex/src/proj"
    key = "-----BEGIN " + "RSA PRIVATE KEY-----"
    text = "\n".join([email, ssn, phone, aws, home, key, ""])
    rules = {item.rule for item in scan_text("notes.md", text)}
    assert "email" in rules
    assert "ssn" in rules
    assert "phone" in rules
    assert "aws-access-key" in rules
    assert "home-path" in rules
    assert "private-key" in rules


def test_scan_text_allows_example_email_and_placeholder_home():
    text = "write to podcast-test@example.com from /Users/you/src/GitHub/thechudleydorightpodcast/\n"
    assert scan_text("README.md", text) == []


def test_pii_check_on_tmp_repo(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "ok.md").write_text("contact user@example.com\n", encoding="utf-8")
    (repo / "bad.md").write_text("mail " + "name@" + "host.tld" + "\n", encoding="utf-8")
    init_git_repo(repo)
    hits = run_pii_check(repo)
    assert any("bad.md" in item and "email" in item for item in hits)
    assert not any("ok.md" in item for item in hits)


def test_scan_skips_gitignored_secret_filename_contents(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".gitignore").write_text("secret.txt\n", encoding="utf-8")
    (repo / "ok.md").write_text("hello\n", encoding="utf-8")
    (repo / "secret.txt").write_text(
        "mail " + "name@" + "host.tld" + "\n", encoding="utf-8"
    )
    init_git_repo(repo)
    assert scan_tracked_pii(repo) == []
