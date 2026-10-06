# Mac setup — The Chudley Do Right Podcast

Unzip the package. You should see `START-HERE.txt` in the folder.

## Terminal (recommended)

```bash
# =============================================================================
# COMMAND GLOSSARY
# -----
# cd      Enter the unzipped folder (edit the path if yours differs).
# chmod   Mark the installer executable. Here: once per unzip.
# ./…     Run the Mac bootstrap, which then runs install_podcast_stack.py.
# =============================================================================

cd ~/Downloads/ChudleyDoRight-MacSetup
chmod +x mac-setup/install-mac.sh
./mac-setup/install-mac.sh
```

If Finder put the folder on the Desktop, use `~/Desktop/ChudleyDoRight-MacSetup` instead.

Check what is already installed (no downloads):

```bash
./mac-setup/install-mac.sh --check-only
```

## Finder

Double-click `mac-setup/install.command`. If macOS blocks it: right-click the
file → Open → Open. Or in Terminal:

```bash
xattr -cr ~/Downloads/ChudleyDoRight-MacSetup
```

then double-click again.

## What it installs / opens

| Item | Automatic? |
| --- | --- |
| OBS Studio | Yes, via Homebrew if needed |
| ffmpeg | Yes, via Homebrew if needed |
| Python PDF/Word/Excel helpers | Yes, into this folder's `vendor/` |
| VDO.Ninja | Opens in your browser (no install) |
| Source Record (OBS plugin) | Opens the download page — pick the macOS build for your OBS |
| DaVinci Resolve | Opens Blackmagic's site — free account required |
| Homebrew / Python 3.9+ | Installs Python via brew if brew is already there; otherwise opens https://brew.sh |

It does **not** pipe `curl | bash`. It does **not** install Discord unless you
run `python3 install_podcast_stack.py` without `--skip-optional`.

## Session join link (Host B — Bobby)

https://vdo.ninja/?room=thechudleydorightpodcast&push=bobby&label=Bobby

Headphones on before you allow camera + mic. Riley should have the director
page open first: `https://vdo.ninja/?director=thechudleydorightpodcast`

## Hardware

- Webcam and microphone
- Wired headphones if you can (stops echo)
- Ethernet if you can; otherwise solid Wi-Fi
