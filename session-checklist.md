# Day-of recording checklist — The Chudley Do Right Podcast

## Before guests join

- [ ] Headphones on for Host A, Host B, and Guest
- [ ] Mic gain set (OBS meters peak roughly -12 to -6 dB, not clipping)
- [ ] Three VDO.Ninja links ready (one per person)
- [ ] OBS has three Browser Sources, labeled by name
- [ ] Source Record enabled on each source; confirm files are writing
- [ ] Program (mixed) recording armed as a safety net
- [ ] Disk space checked (comfortable with 40+ GB free)
- [ ] 30-second guest test send completed

## Live stream (skip until destination.json is filled in)

See `live-stream/README.md`. Do not block recording on this.

- [ ] `python3 live-stream/check_destination.py` reports ready
- [ ] OBS → Settings → Stream matches `live-stream/destination.json`
- [ ] Stream key is in OBS (or `.env`), not in git
- [ ] Website `/live` page is published on Riley's or Bobby's site
- [ ] Short test stream completed (unlisted / test key) before guests arrive

## Roll record

- [ ] All three Source Record outputs show “recording”
- [ ] If going live: Start Streaming after recordings are already rolling
- [ ] On-camera clap / “3-2-1” sync mark
- [ ] Do the interview (~1 hour)

## After

- [ ] If live: Stop Streaming first
- [ ] Stop all recordings; confirm three (or four) files on disk
- [ ] Back up files before editing
- [ ] Import into DaVinci Resolve; sync on the clap; balance levels; export
- [ ] Optional: `python3 tools/convert_audio.py mix.mkv -o episode.mp3` for a publish copy
