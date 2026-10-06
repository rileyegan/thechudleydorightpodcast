#!/usr/bin/env python3
# =============================================================================
# COMMAND GLOSSARY — tools this script may invoke
# -----
# python3   Runs this checker. Here: validates live-stream/destination.json.
# =============================================================================
"""
Report whether the live-stream destination file is filled in enough to go live.

Does not start a stream, open OBS, or contact the website.

  python3 live-stream/check_destination.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
DEST_PATH = ROOT / "destination.json"
EXAMPLE_PATH = ROOT / "destination.example.json"
ALLOWED_WHICH = {"riley", "bobby"}
ALLOWED_PLATFORMS = {"youtube", "twitch", "custom_rtmp"}
SECRET_KEYS = {"stream_key", "streamkey", "key", "password", "token"}


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def is_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def looks_like_secret_field(data: Any, path: str, issues: list[str]) -> None:
    if isinstance(data, dict):
        for key, value in data.items():
            here = f"{path}.{key}" if path else key
            if key.lower() in SECRET_KEYS and str(value).strip():
                issues.append(
                    f"{here} looks like a secret — keep keys in OBS or .env, not git"
                )
            looks_like_secret_field(value, here, issues)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            looks_like_secret_field(item, f"{path}[{i}]", issues)


def check(dest: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    looks_like_secret_field(dest, "", issues)

    status = str(dest.get("status") or "").strip()
    if status != "ready":
        issues.append(
            f"status is {status!r} (set to 'ready' when website + ingest + player are filled)"
        )

    website = dest.get("website") or {}
    which = str(website.get("which") or "").strip()
    if which not in ALLOWED_WHICH:
        issues.append("website.which must be 'riley' or 'bobby'")
    url = str(website.get("url") or "").strip()
    if not is_http_url(url):
        issues.append("website.url must be the public https:// page that hosts the player")

    ingest = dest.get("ingest") or {}
    platform = str(ingest.get("platform") or "").strip()
    if platform not in ALLOWED_PLATFORMS:
        issues.append(
            "ingest.platform must be 'youtube', 'twitch', or 'custom_rtmp'"
        )
    if platform == "custom_rtmp":
        server = str(ingest.get("server") or "").strip()
        if not server.startswith("rtmp"):
            issues.append("ingest.server must be an rtmp:// or rtmps:// URL for custom ingest")

    player = dest.get("player") or {}
    embed_src = str(player.get("embed_src") or "").strip()
    if not is_http_url(embed_src):
        issues.append("player.embed_src must be the iframe/player https:// URL")
    if platform == "twitch":
        parent = str(player.get("twitch_parent_host") or "").strip()
        if not parent or parent.startswith("YOUR_"):
            issues.append(
                "player.twitch_parent_host must be the website hostname (no https://)"
            )
        if "parent=" not in embed_src:
            issues.append("Twitch player.embed_src must include &parent=YOUR_SITE_DOMAIN")

    return issues


def main() -> int:
    print("The Chudley Do Right Podcast — live-stream destination check")
    dest_label = rel(DEST_PATH)
    if not DEST_PATH.exists():
        print(f"[NEED] {dest_label}: missing")
        print(f"       → cp {rel(EXAMPLE_PATH)} {dest_label} and fill it in")
        return 1

    try:
        dest = load_json(DEST_PATH)
    except json.JSONDecodeError as exc:
        print(f"[NEED] {dest_label}: invalid JSON ({exc})")
        return 1

    issues = check(dest)
    if issues:
        print(f"[NEED] {dest_label}: {len(issues)} item(s) still blank")
        for issue in issues:
            print(f"       → {issue}")
        return 1

    which = dest["website"]["which"]
    platform = dest["ingest"]["platform"]
    print(f"[OK]   {dest_label}: ready ({which}'s site, {platform} ingest)")
    print("       Paste player.embed_src into embed.example.html before publishing.")
    print("       Put the stream key in OBS (or CHUDLEY_STREAM_KEY), never in git.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
