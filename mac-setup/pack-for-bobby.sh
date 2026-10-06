#!/bin/sh
# =============================================================================
# COMMAND GLOSSARY — tools this script may invoke
# -----
# mktemp   Creates a throwaway folder. Here: staging copy for the zip.
# rsync    Copies files. Here: repo minus git, vendor, caches.
# chmod    Sets executable bits on the Mac installers.
# ditto    Makes a zip on macOS. zip(1) is the fallback.
# cp       Copies the zip to Desktop when that folder is writable.
# rm       Deletes the staging folder.
# =============================================================================
#
# Build ChudleyDoRight-MacSetup.zip from this checkout (no .git, no vendor).
#
#   ./mac-setup/pack-for-bobby.sh
#
set -e

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
DIST="$ROOT/dist"
NAME="ChudleyDoRight-MacSetup"
STAGING="$(mktemp -d "${TMPDIR:-/tmp}/${NAME}.XXXXXX")"
STAGE="$STAGING/$NAME"
DESKTOP="${HOME}/Desktop"
OUT="$DIST/${NAME}.zip"

mkdir -p "$DIST" "$STAGE"

# Avoid AppleDouble (._) files in the zip Bobby unzips.
COPYFILE_DISABLE=1
export COPYFILE_DISABLE

# Safety: copy only this repo tree; no network; no git history; no vendored wheels.
rsync -a \
    --exclude '.git/' \
    --exclude 'vendor/' \
    --exclude 'dist/' \
    --exclude '__pycache__/' \
    --exclude '*.py[cod]' \
    --exclude '.DS_Store' \
    --exclude 'setup-status.json' \
    --exclude '.env' \
    --exclude 'live-stream/destination.json' \
    --exclude '.venv/' \
    --exclude '.index/' \
    --exclude '.chats/' \
    "$ROOT/" "$STAGE/"

cp "$ROOT/mac-setup/START-HERE.txt" "$STAGE/START-HERE.txt"
chmod +x "$STAGE/mac-setup/install-mac.sh" "$STAGE/mac-setup/install.command" \
    "$STAGE/mac-setup/pack-for-bobby.sh"

rm -f "$OUT"
if command -v ditto >/dev/null 2>&1; then
    # Finder-friendly zip without resource-fork sidecars.
    ditto -c -k --norsrc --noextattr --noqtn --keepParent "$STAGE" "$OUT"
else
    (CDPATH= cd -- "$STAGING" && zip -r "$OUT" "$NAME" >/dev/null)
fi

rm -rf "$STAGING"

echo "Wrote $OUT"
if [ -d "$DESKTOP" ]; then
    cp "$OUT" "$DESKTOP/${NAME}.zip"
    echo "Copied $DESKTOP/${NAME}.zip"
fi
echo
echo "Send Bobby that zip plus mac-setup/MESSAGE-TO-BOBBY.txt"
