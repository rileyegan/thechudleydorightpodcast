# Live stream framework — The Chudley Do Right Podcast

Record the way you already do (VDO.Ninja → OBS → Source Record). When you
want a public audience, OBS sends the **same mixed program** to an ingest
host, and whichever website you pick embeds that host's player.

Nothing here goes live until you copy the example config, choose a site,
and fill in the blanks.

```
VDO.Ninja (Riley, Bobby, guest)
        │
        ▼
      OBS mix ──► disk  (Source Record + program recording)
        │
        └──► RTMP ingest ──► YouTube / Twitch / custom
                                  │
                                  ▼
                         website embed player
                         (Riley's site or Bobby's)
```

## 1. Pick the website (later)

Copy the example and edit the real file (gitignored — may point at secrets):

```bash
# =============================================================================
# COMMAND GLOSSARY
# -----
# cp        Copy a file. Here: start a private destination file from the example.
# python3   Run the checker. Here: tell you what is still blank.
# =============================================================================

cp live-stream/destination.example.json live-stream/destination.json
```

Set `website.which` to `"riley"` or `"bobby"`, and put the live page URL in
`website.url` (for example `https://example.com/live`).

Paste candidate site URLs into `website.candidates` anytime — you do not
have to choose yet.

## 2. Pick the ingest host (later)

Set `ingest.platform` to one of:

| Platform | OBS → Settings → Stream | What the website embeds |
| --- | --- | --- |
| `youtube` | Service **YouTube - RTMPS**, stream key from YouTube Studio → Go live | YouTube iframe (`embed_src` in the recipe) |
| `twitch` | Service **Twitch**, stream key from Twitch Creator Dashboard | Twitch player; `parent` **must** be the website hostname |
| `custom_rtmp` | Service **Custom**, server URL + stream key from that host | That host's player URL |

Copy the matching object under `recipes` into `ingest` and `player`. Leave
the stream key **out** of git. Put it in OBS, or in a local `.env` as
`CHUDLEY_STREAM_KEY` (see `.env.example` at the repo root).

Suggested OBS output for a talking-head show (already in the example file):
1080p30, ~4500 kbps video, 160 kbps AAC audio, hardware H.264.

## 3. Drop the player on the chosen site

`embed.example.html` is a complete `/live` page. You can:

- Host the file as-is on Riley's or Bobby's site, or
- Copy the player markup into an existing CMS page

Then set `window.CHUDLEY_LIVE.embedSrc` (and `watchUrl`) to the values from
`destination.json`. Until those are filled, the page shows an offline
placeholder instead of a broken iframe.

## 4. Check that the framework is complete

```bash
python3 live-stream/check_destination.py
```

Exit code `0` means website, ingest, and player fields are filled and the
checker did not find a stream key in the JSON. It does **not** start a
stream and does **not** prove the website is online.

## Day-of (once configured)

1. Mix and record as usual (`session-checklist.md`).
2. Confirm OBS stream settings match `destination.json`.
3. Do a short unlisted / test stream before guests arrive.
4. **Start Recording** (and Source Record) first, then **Start Streaming**.
5. After the show: **Stop Streaming**, then stop recordings.

VDO.Ninja is only for the three people in the room. Viewers watch the
website player, not a VDO.Ninja link.
