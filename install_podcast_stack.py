#!/usr/bin/env python3
# =============================================================================
# COMMAND GLOSSARY — tools this script may invoke
# -----
# python3   Runs this installer. Here: detects OS and drives setup steps.
# platform  Stdlib OS detector. Here: chooses macOS / Windows / Linux paths.
# shutil    Stdlib path helper. Here: finds brew, winget, flatpak, etc.
# subprocess  Runs shell commands. Here: installs apps via package managers.
# webbrowser  Opens URLs. Here: VDO.Ninja, Resolve download, plugin pages.
# pathlib   Path helpers. Here: plugin folders and status checks.
# urllib.request  Downloads files. Here: Source Record plugin when possible.
# =============================================================================
"""
Install and verify the free three-stream podcast stack:

  - OBS Studio (record / mix)
  - VDO.Ninja (three separate remote A/V feeds)
  - OBS Source Record plugin (one file per person)
  - DaVinci Resolve free (edit / sync) — download page only; Blackmagic
    requires a free account, so silent install is not reliable

Run:
  python3 install_podcast_stack.py
  python3 install_podcast_stack.py --check-only
  python3 install_podcast_stack.py --skip-browser
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Links (free tools + docs)
# ---------------------------------------------------------------------------
VDO_NINJA_URL = "https://vdo.ninja"
VDO_NINJA_DOCS_URL = "https://docs.vdo.ninja"
OBS_DOWNLOAD_URL = "https://obsproject.com/download"
OBS_SOURCE_RECORD_URL = (
    "https://obsproject.com/forum/resources/source-record.1285/"
)
# Community builds are also mirrored on GitHub releases for some platforms.
SOURCE_RECORD_GITHUB = "https://github.com/exeldro/obs-source-record/releases"
RESOLVE_DOWNLOAD_URL = (
    "https://www.blackmagicdesign.com/products/davinciresolve"
)
DISCORD_URL = "https://discord.com/download"
HEADPHONES_REMINDER = (
    "Everyone needs headphones (wired preferred) so speakers do not bleed "
    "into mics. Separate tracks will not fix echo."
)


@dataclass
class StepResult:
    name: str
    ok: bool
    detail: str
    action_needed: str = ""


@dataclass
class Report:
    results: list[StepResult] = field(default_factory=list)

    def add(self, result: StepResult) -> None:
        self.results.append(result)

    def print_summary(self) -> None:
        print("\n" + "=" * 64)
        print("The Chudley Do Right Podcast — setup summary")
        print("=" * 64)
        for r in self.results:
            mark = "OK" if r.ok else "NEED"
            print(f"[{mark}] {r.name}: {r.detail}")
            if r.action_needed:
                print(f"       → {r.action_needed}")
        print("=" * 64)
        print(HEADPHONES_REMINDER)
        print()
        print("Quick session flow:")
        print("  1. Open VDO.Ninja director room; send one link per person.")
        print("  2. In OBS, add each person as a separate Browser Source.")
        print("  3. Set levels per person in the OBS audio mixer.")
        print("  4. Enable Source Record on each source (separate files).")
        print("  5. Clap once on camera for sync, then record ~1 hour.")
        print("  6. Sync/edit the three files in DaVinci Resolve.")


def which(cmd: str) -> Optional[str]:
    """Locate an executable on PATH. Returns None if missing."""
    return shutil.which(cmd)


def run(
    args: list[str],
    *,
    check: bool = False,
    capture: bool = True,
) -> subprocess.CompletedProcess[str]:
    """
    Run a subprocess command.
    Safety: never uses shell=True; never pipes remote scripts into bash.
    """
    return subprocess.run(
        args,
        check=check,
        text=True,
        capture_output=capture,
    )


def open_url(url: str, *, skip_browser: bool) -> None:
    """Open a URL in the default browser unless --skip-browser was passed."""
    print(f"  Open: {url}")
    if skip_browser:
        return
    try:
        webbrowser.open(url)
    except Exception as exc:  # noqa: BLE001 — report and continue
        print(f"  Could not open browser automatically: {exc}")


def detect_os() -> str:
    """Return one of: macos, windows, linux, other."""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    if system == "windows":
        return "windows"
    if system == "linux":
        return "linux"
    return "other"


# ---------------------------------------------------------------------------
# OBS Studio
# ---------------------------------------------------------------------------
def obs_installed() -> bool:
    """True if OBS looks installed on this machine."""
    os_id = detect_os()
    if which("obs") or which("obs64") or which("obs32"):
        return True
    if os_id == "macos":
        return Path("/Applications/OBS.app").exists()
    if os_id == "windows":
        candidates = [
            Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
            / "obs-studio"
            / "bin"
            / "64bit"
            / "obs64.exe",
            Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
            / "obs-studio"
            / "bin"
            / "64bit"
            / "obs64.exe",
        ]
        return any(p.exists() for p in candidates)
    if os_id == "linux":
        # Flatpak app id is common on Linux desktops.
        if which("flatpak"):
            proc = run(["flatpak", "info", "com.obsproject.Studio"])
            if proc.returncode == 0:
                return True
        return False
    return False


def install_obs() -> StepResult:
    """Install OBS Studio with the platform package manager when possible."""
    if obs_installed():
        return StepResult("OBS Studio", True, "Already installed")

    os_id = detect_os()
    print("\nInstalling OBS Studio…")

    try:
        if os_id == "macos":
            if not which("brew"):
                return StepResult(
                    "OBS Studio",
                    False,
                    "Homebrew not found",
                    "Install Homebrew from https://brew.sh then re-run, "
                    "or download OBS from https://obsproject.com/download",
                )
            # Action: install OBS via Homebrew cask.
            # Safety: uses official brew cask name; does not pipe curl|bash.
            proc = run(["brew", "install", "--cask", "obs"], capture=False)
            if proc.returncode == 0 or obs_installed():
                return StepResult("OBS Studio", True, "Installed via Homebrew")
            return StepResult(
                "OBS Studio",
                False,
                "brew install failed",
                f"Download manually: {OBS_DOWNLOAD_URL}",
            )

        if os_id == "windows":
            winget = which("winget")
            if not winget:
                return StepResult(
                    "OBS Studio",
                    False,
                    "winget not found",
                    f"Install from Microsoft Store / winget, or {OBS_DOWNLOAD_URL}",
                )
            # Action: install OBS with winget (Windows package manager).
            # Safety: official package id OBSProject.OBSStudio; may prompt UAC.
            proc = run(
                [
                    "winget",
                    "install",
                    "--id",
                    "OBSProject.OBSStudio",
                    "-e",
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                ],
                capture=False,
            )
            if proc.returncode == 0 or obs_installed():
                return StepResult("OBS Studio", True, "Installed via winget")
            return StepResult(
                "OBS Studio",
                False,
                "winget install failed",
                f"Download manually: {OBS_DOWNLOAD_URL}",
            )

        if os_id == "linux":
            if which("flatpak"):
                # Action: install OBS from Flathub.
                # Safety: known app id; may ask for sudo/user confirmation.
                run(
                    [
                        "flatpak",
                        "install",
                        "-y",
                        "flathub",
                        "com.obsproject.Studio",
                    ],
                    capture=False,
                )
                if obs_installed():
                    return StepResult(
                        "OBS Studio", True, "Installed via Flatpak"
                    )
            if which("apt-get"):
                # Action: try distro package (name varies by Ubuntu/Debian).
                # Safety: may require sudo password in your terminal.
                run(["sudo", "apt-get", "update"], capture=False)
                run(
                    ["sudo", "apt-get", "install", "-y", "obs-studio"],
                    capture=False,
                )
                if obs_installed():
                    return StepResult(
                        "OBS Studio", True, "Installed via apt"
                    )
            return StepResult(
                "OBS Studio",
                False,
                "No automatic installer succeeded",
                f"Install Flatpak + Flathub, or download: {OBS_DOWNLOAD_URL}",
            )
    except FileNotFoundError as exc:
        return StepResult(
            "OBS Studio",
            False,
            f"Missing tool: {exc}",
            f"Download manually: {OBS_DOWNLOAD_URL}",
        )

    return StepResult(
        "OBS Studio",
        False,
        f"Unsupported OS: {platform.system()}",
        f"Download manually: {OBS_DOWNLOAD_URL}",
    )


# ---------------------------------------------------------------------------
# Source Record plugin
# ---------------------------------------------------------------------------
def obs_plugin_dirs() -> list[Path]:
    """Likely OBS plugin directories for the current user/OS."""
    home = Path.home()
    os_id = detect_os()
    dirs: list[Path] = []
    if os_id == "macos":
        dirs.append(home / "Library/Application Support/obs-studio/plugins")
    elif os_id == "windows":
        dirs.append(home / "AppData/Roaming/obs-studio/plugins")
        program = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        dirs.append(program / "obs-studio/obs-plugins")
    else:
        dirs.append(home / ".config/obs-studio/plugins")
        dirs.append(Path("/usr/lib/obs-plugins"))
        dirs.append(Path("/usr/lib64/obs-plugins"))
    return dirs


def source_record_installed() -> bool:
    """Heuristic: look for source-record plugin files under OBS plugin dirs."""
    needles = ("source-record", "source_record", "obs-source-record")
    for folder in obs_plugin_dirs():
        if not folder.exists():
            continue
        for path in folder.rglob("*"):
            name = path.name.lower()
            if any(n in name for n in needles):
                return True
    return False


def install_source_record(*, skip_browser: bool) -> StepResult:
    """
    Source Record is an OBS plugin — distribution varies by OS/OBS version.
    We verify presence and open the official install pages when missing.
    """
    if source_record_installed():
        return StepResult("OBS Source Record", True, "Plugin files detected")

    print("\nSource Record plugin not detected.")
    print("Opening install pages (download the build matching your OBS)…")
    open_url(OBS_SOURCE_RECORD_URL, skip_browser=skip_browser)
    open_url(SOURCE_RECORD_GITHUB, skip_browser=skip_browser)

    plugin_hint = obs_plugin_dirs()[0]
    return StepResult(
        "OBS Source Record",
        False,
        "Not detected yet (manual install required)",
        f"Install the plugin, restart OBS, re-run with --check-only. "
        f"Typical plugin folder: {plugin_hint}",
    )


# ---------------------------------------------------------------------------
# DaVinci Resolve / VDO.Ninja / Discord
# ---------------------------------------------------------------------------
def resolve_installed() -> bool:
    """True if DaVinci Resolve looks installed."""
    os_id = detect_os()
    if os_id == "macos":
        return Path("/Applications/DaVinci Resolve/DaVinci Resolve.app").exists()
    if os_id == "windows":
        base = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        return (base / "Blackmagic Design/DaVinci Resolve").exists()
    if os_id == "linux":
        return bool(
            which("davinci-resolve")
            or Path("/opt/resolve").exists()
            or Path("/opt/DaVinciResolve").exists()
        )
    return False


def setup_resolve(*, skip_browser: bool) -> StepResult:
    """Resolve needs a Blackmagic account — open the download page."""
    if resolve_installed():
        return StepResult("DaVinci Resolve", True, "Already installed")

    print("\nDaVinci Resolve (free) requires a Blackmagic Design account.")
    print("Opening the official download page…")
    open_url(RESOLVE_DOWNLOAD_URL, skip_browser=skip_browser)
    return StepResult(
        "DaVinci Resolve",
        False,
        "Download page opened — complete install manually",
        "Create a free Blackmagic account, download Resolve Free, install it.",
    )


def setup_vdo_ninja(*, skip_browser: bool) -> StepResult:
    """VDO.Ninja is browser-based — no local install, just open it."""
    print("\nOpening VDO.Ninja (browser-based; no install)…")
    open_url(VDO_NINJA_URL, skip_browser=skip_browser)
    open_url(VDO_NINJA_DOCS_URL, skip_browser=skip_browser)
    return StepResult(
        "VDO.Ninja",
        True,
        "Web app — no install required",
        "Director creates one guest link per person; add each in OBS.",
    )


def setup_discord_optional(*, skip_browser: bool) -> StepResult:
    """Optional backup talk track if VDO.Ninja has issues."""
    print("\nOptional: Discord as a backup call (not the primary recorder).")
    open_url(DISCORD_URL, skip_browser=skip_browser)
    return StepResult(
        "Discord (optional)",
        True,
        "Download page opened if needed",
        "Use only as talkback/backup — record in OBS, not Discord.",
    )


def check_disk_space() -> StepResult:
    """Warn if free space is tight for ~1 hour × 3 video recordings."""
    # Rough target: encourage ≥40 GB free for comfort.
    target_gb = 40
    try:
        usage = shutil.disk_usage(Path.home())
        free_gb = usage.free / (1024**3)
        ok = free_gb >= target_gb
        return StepResult(
            "Disk space",
            ok,
            f"About {free_gb:.0f} GB free on home volume",
            None
            if ok
            else f"Free up space — aim for ≥{target_gb} GB before a 1-hour "
            "three-cam record.",
        )
    except OSError as exc:
        return StepResult("Disk space", False, f"Could not check: {exc}")


def check_headphones_note() -> StepResult:
    """Always surface the headphones requirement."""
    return StepResult(
        "Headphones",
        True,
        "Reminder only (cannot detect automatically)",
        "All three people should wear headphones before recording.",
    )


def write_status_json(report: Report, path: Path) -> None:
    """Write a machine-readable status file next to this script."""
    payload = [
        {
            "name": r.name,
            "ok": r.ok,
            "detail": r.detail,
            "action_needed": r.action_needed,
        }
        for r in report.results
    ]
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote status: {path}")


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Install/verify free tools for a three-stream podcast "
            "(OBS + VDO.Ninja + Source Record + Resolve)."
        )
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Do not install or open browsers; only report what is present.",
    )
    parser.add_argument(
        "--skip-browser",
        action="store_true",
        help="Print URLs instead of opening the default browser.",
    )
    parser.add_argument(
        "--skip-optional",
        action="store_true",
        help="Skip Discord download page.",
    )
    parser.add_argument(
        "--status-file",
        type=Path,
        default=Path(__file__).resolve().parent / "setup-status.json",
        help="Where to write JSON status (default: ./setup-status.json).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    report = Report()

    print("The Chudley Do Right Podcast — dependency installer")
    print(f"OS: {platform.system()} {platform.release()} ({detect_os()})")
    print(f"Python: {sys.version.split()[0]}")

    if args.check_only:
        report.add(
            StepResult(
                "OBS Studio",
                obs_installed(),
                "Found" if obs_installed() else "Not found",
                None if obs_installed() else f"Install from {OBS_DOWNLOAD_URL}",
            )
        )
        report.add(
            StepResult(
                "OBS Source Record",
                source_record_installed(),
                "Found" if source_record_installed() else "Not found",
                None
                if source_record_installed()
                else f"Install from {OBS_SOURCE_RECORD_URL}",
            )
        )
        report.add(
            StepResult(
                "DaVinci Resolve",
                resolve_installed(),
                "Found" if resolve_installed() else "Not found",
                None
                if resolve_installed()
                else f"Download from {RESOLVE_DOWNLOAD_URL}",
            )
        )
        report.add(
            StepResult(
                "VDO.Ninja",
                True,
                "Browser app — visit https://vdo.ninja when recording",
            )
        )
    else:
        report.add(install_obs())
        report.add(install_source_record(skip_browser=args.skip_browser))
        report.add(setup_resolve(skip_browser=args.skip_browser))
        report.add(setup_vdo_ninja(skip_browser=args.skip_browser))
        if not args.skip_optional:
            report.add(setup_discord_optional(skip_browser=args.skip_browser))

    report.add(check_disk_space())
    report.add(check_headphones_note())
    write_status_json(report, args.status_file)
    report.print_summary()

    # Non-zero if required pieces are still missing after an install attempt.
    required = {"OBS Studio", "OBS Source Record", "DaVinci Resolve"}
    missing = [
        r for r in report.results if r.name in required and not r.ok
    ]
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
