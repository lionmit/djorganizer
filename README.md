# DJOrganizer

Auto-sort your DJ music library into genre folders. No code, no API keys, no internet — just double-click and go.

**1,500+ artist and genre keywords** refined across 17 versions. Tested on a 3,700+ track library with 95.6% classification accuracy.

---

## How It Works

DJOrganizer reads your track filenames, matches them against a curated keyword engine (artist names, labels, genre terms, language markers), and sorts them into genre folders. Unclassified tracks go to `00_INBOX/` for your manual review.

**No audio analysis.** No external services. Works offline, runs in seconds.

---

## Quick Start (Mac)

1. **Download** — Click the green "Code" button above → "Download ZIP". Unzip it.
2. **Double-click** `DJOrganizer.command` — if macOS blocks it, right-click → Open → Open.
3. **Tell it where your music is** — drag your music folder into the terminal window
4. **Preview** — see where every track will go (nothing moves yet)
5. **Confirm** — type `y` to sort for real

That's it. If you use Rekordbox, open it after and do: **File → Library → Relocate → Auto Relocate** to reconnect your cue points.

---

## Quick Start (Windows)

1. Download and unzip
2. Open Command Prompt (press Windows key, type `cmd`, press Enter)
3. Navigate to the folder: `cd Desktop\djorganizer`
4. Run: `python sort_main_crate.py`
5. Follow the prompts

---

## Works With Any Folder

Internal drive, USB stick, external SSD, SD card — DJOrganizer asks you where your music is on first run. Your settings are saved so you only configure once.

To reconfigure anytime: `python3 sort_main_crate.py --reset`

---

## Genre Folders

| Folder | What Goes Here |
|--------|---------------|
| `01 Hip-Hop & R&B` | Hip-hop, rap, R&B, grime, drill |
| `02 House` | House, deep house, disco, dance, tech house |
| `03 Techno` | Techno, hardstyle, hardcore, industrial |
| `04 Trance & Psy` | Psytrance, goa, uplifting trance, vocal trance |
| `05 Bass & DnB` | Drum & bass, dubstep, bass music, riddim |
| `06 Electronic` | Ambient, downtempo, synth, IDM, trip-hop |
| `07 Pop & Commercial` | Pop, indie-pop, commercial hits |
| `08 Rock & Alternative` | Rock, punk, indie, metal, shoegaze |
| `09 Latin` | Reggaeton, salsa, bachata, Brazilian, cumbia |
| `10 Afrobeats & Amapiano` | Afrobeats, amapiano, dancehall, soca, gqom |
| `11 World & Ecstatic` | World music, reggae, Arabic, Indian, ecstatic |
| `12 Classics & Oldies` | Pre-1990 / golden era music |
| `13 Israeli & Hebrew` | Mizrahi, Israeli pop, Hebrew-language music |
| `14 Tools & FX` | Stems, acapellas, samples, DJ tools |
| `15 Remixes` | Unclassified remixes |
| `00_INBOX` | Unclassified — needs your manual review |

---

## Command Reference

| Command | What It Does |
|---------|-------------|
| `python3 sort_main_crate.py` | Interactive mode — setup + preview + confirm |
| `python3 sort_main_crate.py --preview` | Preview only (no files moved) |
| `python3 sort_main_crate.py --execute` | Sort files for real |
| `python3 sort_main_crate.py --reset` | Clear saved settings |

---

## Tracks in the Wrong Folder?

The keyword engine is community-powered. If a track gets misclassified:

1. [Open an issue](https://github.com/lionmit/djorganizer/issues/new) with the filename and correct genre
2. Or edit the keyword lists in `sort_main_crate.py` directly and submit a pull request

---

## The Story

DJOrganizer was built without writing a single line of code manually. The entire tool — from first prototype to the version you're using now — was created through conversation with [Claude Code](https://claude.ai/claude-code).

It started at Midburn (the Israeli Burning Man) with two phones and an analog mixer. 3,700+ tracks and 17 versions later, the library sorts itself in seconds.

Read the full build log: [creative-gym-67.vercel.app/log.html](https://creative-gym-67.vercel.app/log.html)

---

## Requirements

- **Python 3.6+** (free from [python.org/downloads](https://python.org/downloads))
- That's it. No pip install, no dependencies, no packages.

---

## License

CC-BY 4.0 — Lionel Mitelpunkt
