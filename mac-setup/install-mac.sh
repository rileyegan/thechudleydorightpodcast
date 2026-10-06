#!/bin/sh
# =============================================================================
# COMMAND GLOSSARY — tools this script may invoke
# -----
# uname           Reports the OS. Here: refuse to run on non-Mac.
# xcode-select    Apple command-line tools. Here: required before Homebrew/Python.
# brew            Homebrew. Here: installs Python, and later OBS/ffmpeg via the
#                 Python installer. This script does NOT pipe curl|bash.
# python3         Interpreter. Here: runs install_podcast_stack.py.
# chmod / open    Fix permissions / open brew.sh if Homebrew is missing.
# =============================================================================
#
# Mac bootstrap for The Chudley Do Right Podcast.
# Run from Terminal after unzipping the package:
#
#   chmod +x mac-setup/install-mac.sh
#   ./mac-setup/install-mac.sh
#
# Extra flags are forwarded to install_podcast_stack.py, for example:
#   ./mac-setup/install-mac.sh --check-only
#   ./mac-setup/install-mac.sh --skip-browser
#
set -e

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "The Chudley Do Right Podcast — Mac installer"
echo "Folder: $ROOT"
echo

if [ "$(uname -s)" != "Darwin" ]; then
    echo "This package is for Mac. This computer reports: $(uname -s)"
    exit 1
fi

if ! xcode-select -p >/dev/null 2>&1; then
    echo "Apple's Command Line Tools are missing (needed once for Python/Homebrew)."
    echo "A system dialog should appear. Install them, then run this script again."
    xcode-select --install || true
    exit 1
fi

python_ok() {
    command -v python3 >/dev/null 2>&1 || return 1
    python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)'
}

if ! python_ok; then
    if command -v brew >/dev/null 2>&1; then
        echo "Installing Python 3 with Homebrew…"
        # Safety: official brew formula name; does not pipe curl|bash.
        brew install python
    else
        echo "Python 3.9+ is missing, and Homebrew is not installed."
        echo
        echo "1. Open https://brew.sh and install Homebrew (their official command)."
        echo "2. Close Terminal, open a new window, then run this installer again."
        echo
        echo "This script will not run Homebrew's remote install for you."
        open "https://brew.sh" || true
        exit 1
    fi
fi

if ! python_ok; then
    echo "python3 is still missing or older than 3.9. Open a new Terminal and retry."
    exit 1
fi

echo "Using: $(command -v python3) ($(python3 -c 'import sys; print(sys.version.split()[0])'))"
echo

# Default: skip Discord download. OBS, ffmpeg, Python libs, VDO.Ninja,
# Source Record pages, and Resolve download page still run.
if [ "$#" -eq 0 ]; then
    set -- --skip-optional
fi

# Safety: argv only; never shell=True; never pipes a remote script into bash.
exec python3 "$ROOT/install_podcast_stack.py" "$@"
