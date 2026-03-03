# DJ Music Crate Sorter

Auto-sort script for a DJ music library using filename keyword analysis.
Built for **Lionel Mitelpunkt** · Pioneer DDJ-FLX4 · Rekordbox 7

---

## What It Does

`sort_main_crate.py` classifies every file in your Main Crate into genre sub-folders under `DJ_MUSIC/`, using a keyword-matching classifier against the audio filename. No audio analysis, no API calls — pure fast Python.

**Folder structure created:**

| Folder | Genre |
|--------|-------|
| `01 Israeli & Hebrew` | Israeli / Hebrew-language music |
| `02 Hip-Hop & R&B` | Hip-hop, rap, R&B, soul |
| `03 House & Dance` | House, deep house, disco, dance |
| `04 Electronic` | Electronic, techno, drum & bass, ambient |
| `05 Pop & Commercial` | Pop, indie-pop, commercial |
| `06 Rock & Alternative` | Rock, punk, indie, metal, shoegaze |
| `07 Latin` | Latin, reggaeton, salsa, bossa nova |
| `08 Classics & Oldies` | Pre-1990 / golden era music |
| `09 World & Ecstatic` | World music, African, reggae, Afrobeats |
| `10 Remixes` | Unclassified remixes (catch-all) |
| `00_INBOX` | Unclassified — requires manual review |

---

## Quick Start

```bash
# 1. Preview — shows what would move where (NO files touched)
python3 sort_main_crate.py --preview

# 2. Execute — actually moves the files
python3 sort_main_crate.py --execute
```

**Always run `--preview` first and sanity-check the output before executing.**

---

## Rekordbox 7 Workflow

After running `--execute`, Rekordbox 7 won't know your files moved. Fix this in one step:

1. Open **Rekordbox 7**
2. Go to **File → Library → Relocate → Auto Relocate**
3. Rekordbox will scan and reconnect all moved files to their existing cue points, loops, and beat grids

No cue data is lost. Auto Relocate handles it automatically.

---

## Configuration

Edit the top of `sort_main_crate.py`:

```python
MAIN_CRATE    = Path("/Users/Lionmit/Music/Main Crate")
DJ_MUSIC_ROOT = Path("/Users/Lionmit/Music/DJ_MUSIC")
```

Change these paths to match your system if needed.

---

## How Classification Works

1. Each filename is lowercased and Unicode-normalized (NFC)
2. Files with Hebrew characters (U+0590–U+05FF) → `01 Israeli & Hebrew`
3. Files matching the `tools` list (stems, acapellas, etc.) → separate tools folder
4. Each genre has a keyword list; **first match wins** (order matters)
5. Songs with years 1900–1989 in parentheses or brackets → `08 Classics & Oldies`
6. Anything unmatched → `00_INBOX` for manual review

**Key design choices:**
- Trailing spaces on keywords (e.g. `"ghost "`) prevent false substring matches
- Underscore variants (e.g. `"a_certain_ratio"`) handle filenames with underscores instead of spaces
- Accent variants (e.g. `"the marías"` alongside `"the marias"`) handle NFC-normalized filenames
- Artist nationality ≠ genre (e.g. Dennis Lloyd → Pop, not Israeli)
- Remix rule runs last — known artists still go to their genre first

---

## Progress History

| Version | INBOX | Tracks Rescued | Notes |
|---------|-------|----------------|-------|
| Baseline | 26.3% (993) | — | Starting point |
| v7+v8 | 22.0% (831) | 162 | 80+ artists, all genres |
| v9 | 20.7% (781) | 50 | Electronic / house deep-dive |
| v10 | 19.3% (730) | 51 | Rock, pop, classics, world |
| v11 | 18.1% (683) | 47 | Accent fixes, underscore variants |
| **v12** | **16.4% (619)** | **64** | **60+ artists, song-title keywords** ✅ |

Target: **15–20% INBOX** (reached at v11, improved further at v12)
Total library: **3,776 tracks**

---

## Simulation Tool

`simulate.py` lets you test the classifier against a tracklist without touching any files:

```bash
python3 simulate.py sort_main_crate.py tracklist.txt
```

`tracklist.txt` should be a plain-text file with one filename per line.
Results are printed with folder distribution and INBOX percentage.
INBOX filenames are written to `/tmp/inbox_v6.txt` for analysis.

---

## Adding More Keywords

To improve classification, edit `sort_main_crate.py` and add entries to the relevant genre's keyword list. Guidelines:

- Add both `"artist name"` and `"artist_name"` if files may use underscores
- Add both accented and unaccented variants: `"rosalía"` and `"rosalia "`
- Use a trailing space on short/common words to avoid false matches: `"ghost "` not `"ghost"`
- Song-title keywords work well for tracks where the artist isn't in the filename
- Re-run simulation after each batch to verify improvement

---

## Files

| File | Description |
|------|-------------|
| `sort_main_crate.py` | Main classifier script (v12) |
| `simulate.py` | Simulation tool — test without moving files |
| `tracklist.txt` | Your library tracklist (one filename per line) |
| `README.md` | This file |
