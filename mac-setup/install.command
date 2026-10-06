#!/bin/bash
# Double-click this in Finder, or run it from Terminal.
# Pauses at the end so a double-clicked window does not vanish.
set -e
DIR="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
"$DIR/install-mac.sh" --skip-optional
status=$?
echo
echo "Installer finished (exit ${status})."
echo "Press Return to close this window."
read -r || true
exit "${status}"
