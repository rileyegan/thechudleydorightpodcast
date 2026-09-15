#!/usr/bin/env python3
# =============================================================================
# COMMAND GLOSSARY — tools this script may invoke
# -----
# python3   Runs this publisher. Here: creates a GitHub repo and pushes files.
# gh        GitHub CLI. Here: `gh repo create` under your logged-in account.
# git       Version control. Here: init, commit, set remote, push.
# shutil    Finds executables. Here: confirms `gh` and `git` exist.
# subprocess  Runs gh/git. Here: no shell pipes; explicit argv only.
# =============================================================================
"""
Create github.com/<you>/thechudleydorightpodcast and push this folder as main.

Run on YOUR machine (needs your GitHub login via `gh auth login`):

  python3 publish_github_repo.py
  python3 publish_github_repo.py --private
  python3 publish_github_repo.py --owner rileyegan --name thechudleydorightpodcast

Safety notes:
  - Creates a NEW GitHub repository (irreversible name claim until you delete it).
  - Makes an initial commit of the files in this directory.
  - Pushes to origin main. Does not force-push.
  - Will refuse to run if this folder is already inside another git work tree
    unless you pass --allow-nested.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from shutil import which

DEFAULT_NAME = "thechudleydorightpodcast"
DEFAULT_OWNER = "rileyegan"
DEFAULT_DESC = (
    "Free three-stream podcast setup (OBS + VDO.Ninja + Source Record + Resolve)"
)

ROOT = Path(__file__).resolve().parent


def run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a command with argv list (never shell=True)."""
    print("+", " ".join(args))
    return subprocess.run(args, cwd=ROOT, text=True, check=check, capture_output=False)


def inside_foreign_git() -> bool:
    """True if this folder is tracked by a parent git repo (e.g. datastuff)."""
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        return False
    top = Path(proc.stdout.strip()).resolve()
    return top != ROOT


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--owner", default=DEFAULT_OWNER, help="GitHub user/org")
    p.add_argument("--name", default=DEFAULT_NAME, help="Repository name")
    p.add_argument(
        "--private",
        action="store_true",
        help="Create a private repo (default: public)",
    )
    p.add_argument(
        "--allow-nested",
        action="store_true",
        help="Allow publishing even if this folder currently sits inside another git repo",
    )
    p.add_argument(
        "--skip-push",
        action="store_true",
        help="Create the GitHub repo and local commit, but do not push",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if which("gh") is None:
        print("ERROR: GitHub CLI (`gh`) not found. Install from https://cli.github.com")
        return 1
    if which("git") is None:
        print("ERROR: `git` not found on PATH.")
        return 1

    # Confirm gh is logged in as a human user (not a limited bot token).
    auth = subprocess.run(
        ["gh", "auth", "status"],
        text=True,
        capture_output=True,
    )
    print(auth.stdout or auth.stderr)
    if auth.returncode != 0:
        print("ERROR: `gh auth status` failed. Run: gh auth login")
        return 1

    if inside_foreign_git() and not args.allow_nested:
        print(
            "ERROR: this folder is inside another git repository.\n"
            "Copy/move it somewhere else, OR re-run with --allow-nested\n"
            "after you understand it will create a nested .git here."
        )
        return 1

    visibility = "private" if args.private else "public"
    full = f"{args.owner}/{args.name}"
    remote = f"https://github.com/{full}.git"
    git_dir = ROOT / ".git"

    if not git_dir.exists():
        # --- 1. Local git init + first commit ---
        # Action: start version control for this folder only.
        # Safety: creates .git here; does not delete anything.
        run(["git", "init", "-b", "main"])
        run(["git", "add", "."])
        run(
            [
                "git",
                "commit",
                "-m",
                "Initial commit: podcast stack installer and docs",
            ]
        )
    else:
        print("Local .git already present — skipping init/commit.")

    # --- 2. Create GitHub repo from this folder and push ---
    # Action: claim the repo name and upload commits.
    # Safety: irreversible until you delete the repo in GitHub settings.
    # Does not force-push. No README template (avoids unrelated remote history).
    if args.skip_push:
        create = [
            "gh",
            "repo",
            "create",
            full,
            f"--{visibility}",
            "--description",
            DEFAULT_DESC,
            "--source",
            str(ROOT),
            "--remote",
            "origin",
        ]
    else:
        create = [
            "gh",
            "repo",
            "create",
            full,
            f"--{visibility}",
            "--description",
            DEFAULT_DESC,
            "--source",
            str(ROOT),
            "--remote",
            "origin",
            "--push",
        ]

    proc = subprocess.run(create, cwd=ROOT, text=True, capture_output=True)
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        already = "already exists" in err.lower() or "name already exists" in err.lower()
        if already:
            print(f"Repo {full} already exists — setting remote and pushing.")
            subprocess.run(
                ["git", "remote", "remove", "origin"],
                cwd=ROOT,
                capture_output=True,
            )
            run(["git", "remote", "add", "origin", remote])
            if not args.skip_push:
                # Action: upload commits to the existing empty/compatible remote.
                # Safety: non-force push.
                run(["git", "push", "-u", "origin", "main"])
        else:
            print(err)
            print(
                "\nIf `gh repo create` is blocked, create an EMPTY repo named "
                f"{args.name} on github.com/{args.owner} (no README), then:\n"
                f"  cd {ROOT}\n"
                "  git init -b main && git add . && git commit -m 'Initial commit'\n"
                f"  git remote add origin {remote}\n"
                "  git push -u origin main"
            )
            return 1
    else:
        if proc.stdout:
            print(proc.stdout)
        print(f"Created/pushed https://github.com/{full}")

    if args.skip_push:
        print("Skipping push (--skip-push). When ready:")
        print(f"  cd {ROOT}")
        print("  git push -u origin main")
        return 0

    print(f"\nDone: https://github.com/{full}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
