# Document and audio helpers

Ported from **datastuff** for this podcast repo. Same libraries and the same
vendor-install pattern; domain pipelines (bank statements, jobs, rebates,
SoundCloud likes) stayed in datastuff.

```bash
# =============================================================================
# COMMAND GLOSSARY
# -----
# python3  Interpreter. Here: installs packages into ./vendor and runs CLIs.
# pip      Package installer. Here: -t vendor keeps system Python clean.
# ffmpeg   Media converter. Here: OBS/Resolve files to mp3/wav/m4a.
# =============================================================================

python3 -m pip install -r requirements.txt -t vendor
python3 tools/check_tools.py --self-test
```

`python3 install_podcast_stack.py` also installs these packages into `vendor/`
and will try to install ffmpeg via brew / apt / winget.

| CLI | Source in datastuff | What it does here |
| --- | --- | --- |
| `tools/pdf_text.py` | `scripts/pdf-text.py` | Extract text from a PDF |
| `tools/pdf_merge.py` | `apps/menards-rebates/.../packets.py` (`merge_pdfs`) | Concatenate PDFs |
| `tools/docx_io.py` | `riley-job-stuff` (`python-docx`) | Dump or write a `.docx` |
| `tools/xlsx_io.py` | `openpyxl` exporters | Dump a workbook or build one from CSV |
| `tools/convert_audio.py` | SoundCloud downloader's ffmpeg argv | Extract/convert audio (no SoundCloud) |

Examples (from the repo root):

```bash
python3 tools/pdf_text.py guest-bio.pdf -o guest-bio.txt
python3 tools/pdf_merge.py -o packet.pdf bio.pdf questions.pdf
python3 tools/docx_io.py dump show-notes.docx
python3 tools/docx_io.py from-text show-notes.txt show-notes.docx
python3 tools/xlsx_io.py dump rundown.xlsx
python3 tools/xlsx_io.py from-csv rundown.csv rundown.xlsx
python3 tools/convert_audio.py mix.mkv -o episode.mp3
```

Scanned PDFs with no text layer will extract empty — that is a pypdf limit,
same as datastuff. Image OCR was not in datastuff and is not here.

Not ported (not needed for recording/publishing this show):

- Chase / Wells / Amex / Ally statement parsers
- Family ledger and spend taxonomy
- Resume/cover templates
- Menards rebate app (only `merge_pdfs` came over)
- SoundCloud likes downloader
- Parquet / Google Sheet job import / `.ics` gameday tools
