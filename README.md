# 🎵 DJOrganizer v21

**Turn noise into clarity.** Drop your music folder, see everything tagged, sort in one click.

Built for hobby DJs playing gigs with unorganized libraries — 2,000+ tracks scattered everywhere, and it feels like you need a miracle to sort them. This is that miracle.

## Quick Start

**Mac:** Double-click `DJOrganizer.command` → app opens in your browser.

**Windows:** Double-click `DJOrganizer.bat` → app opens in your browser.

That's it. No terminal, no commands, no setup.

## What It Does

- **13 genres** — House, Amapiano, Afrobeats, Reggae & Dancehall, Hip-Hop & R&B, Latin, Bass DnB & Garage, Pop, Funk Disco Soul, Rock, Electronic, Classics, Country
- **12 auto-tags** — Genre, Energy (Low/Mid/High), Clean/Explicit, Year, Language, BPM, Key, Mix Type, Vocal Type, Duration, Date Added, Era
- **Locale detection** — Hebrew, Arabic, Russian, Korean, Japanese, Hindi, Turkish tracks auto-detected by characters
- **Energy system** — BPM-based + keyword detection + genre defaults. The killer feature.
- **Copy-safe** — Files are copied by default, originals stay untouched
- **Undo** — One click to reverse any sort
- **CSV export** — Full tag spreadsheet, importable into Rekordbox

## How It Works

1. **Drop** your music folder (or browse/paste path)
2. **Review** all tracks with 12 auto-detected tags in a sortable, filterable table
3. **Sort** into genre folders with one click

## After Sorting: reconnect your DJ software

By default DJOrganizer **copies**, so your originals stay exactly where they are and your DJ software keeps working untouched. Budget disk space accordingly: sorting a 96 GB library needs another 96 GB free. The app checks before it starts.

If you turn copy-safe off and let it **move** files, your DJ software will show the tracks as missing until you point it at their new home. **Your cue points and BPM analysis are not lost.** They live in the software's own database, keyed to the track, not to the folder. You are only repairing a broken path. Do it immediately after sorting, not weeks later.

| Software | What to do |
|---|---|
| **rekordbox** | File → Library → Relocate → **Auto Relocate** |
| **DJUCED** | Song Library → All Songs → gear icon → **Check Library**. Re-links everything in one pass. Single track: right-click → **Relocate** |
| **Serato** | Files panel → drag the new parent folder onto the missing tracks, or Relocate Lost Files |
| **Traktor** | Right-click the track or playlist → **Relocate**, then point at the new parent folder |

**Playing on CDJs?** No DJ software except rekordbox can write the database Pioneer/AlphaTheta players read. Sort here, then import into rekordbox, analyse, build playlists, and export to a FAT32 USB from rekordbox itself.

## Privacy

All data stays on your computer. Nothing is uploaded or shared. The app runs entirely on localhost.

## For DJs

See our [research page](https://djorganizer.vercel.app/research.html) for the methodology behind the genre and energy systems.

## The Story

This entire tool was built without writing a single line of code manually — 100% AI-generated through conversation with Claude Code. It's part of [Lionel's Creative Gym](https://lionelmitelpunkt.com), where we help people build real things with AI.

## Requirements

- Python 3.6+
- macOS or Windows
- No internet required

## License

MIT — © 2026 Lionel Mitelpunkt
