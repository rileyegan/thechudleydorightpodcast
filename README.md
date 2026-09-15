# The Chudley Do Right Podcast

Free three-stream interview setup: two hosts + one remote guest, each with a
dedicated video feed and audio level in OBS.

## What you need (hardware)

- Webcam + microphone for each host (you already have these)
- Headphones for **everyone** (wired preferred — stops echo)
- Stable internet for the guest (Ethernet if possible)
- Roughly **40+ GB** free disk for a one-hour three-cam record

## Software this repo installs / opens

| Tool | Role | Cost |
| --- | --- | --- |
| [OBS Studio](https://obsproject.com) | Mix + record | Free |
| [VDO.Ninja](https://vdo.ninja) | Three separate remote A/V streams | Free |
| [Source Record](https://obsproject.com/forum/resources/source-record.1285/) | One file (video+audio) per person | Free |
| [DaVinci Resolve](https://www.blackmagicdesign.com/products/davinciresolve) | Sync, edit, export | Free tier |
| Discord (optional) | Backup talk track only | Free |

## Quick start

```bash
# =============================================================================
# COMMAND GLOSSARY — tools used below
# -----
# cd       Change directory. Here: enter this repo folder.
# python3  Python interpreter. Here: run the installer script.
# =============================================================================

# Enter the podcast repo folder (adjust the path if yours differs).
# Safety: only changes the shell's working directory.
cd thechudleydorightpodcast

# Install/verify OBS and open pages for Source Record, Resolve, VDO.Ninja.
# Safety: may call brew/winget/flatpak/apt (can ask for your password).
# Does NOT pipe curl|bash. Resolve still needs a free Blackmagic account.
python3 install_podcast_stack.py
```

Check-only mode (no installs, no browser):

```bash
# Report what is already installed. Changes nothing.
python3 install_podcast_stack.py --check-only
```

## Session flow

1. One host is **director** in OBS.
2. Open VDO.Ninja; create **one guest link per person** (Host A, Host B, Guest).
3. In OBS, add three **Browser Sources** (one per person).
4. Set **per-person levels** in the OBS audio mixer (aim about −12 to −6 dB).
5. Turn on **Source Record** for each source so you get three separate files.
6. Everyone wears headphones. Clap once on camera for sync.
7. Record the hour. Later, sync the three clips in DaVinci Resolve.

## Publish this folder as its own GitHub repo

This cloud agent cannot create `rileyegan/thechudleydorightpodcast` (token is
scoped to other repos). On your Mac/PC, after cloning or copying this folder:

```bash
# =============================================================================
# COMMAND GLOSSARY
# -----
# cd     Enter the project folder.
# python3  Run the publisher. Here: gh repo create + git push.
# =============================================================================

# Create github.com/rileyegan/thechudleydorightpodcast and push these files.
# Safety: needs your logged-in `gh` CLI; creates a NEW public repo; pushes main.
python3 publish_github_repo.py
```

Or do it by hand with `gh repo create` (see comments inside that script).

## License

Setup scripts and docs in this folder are for the podcast project. Third-party
apps keep their own licenses (OBS GPL, etc.).
