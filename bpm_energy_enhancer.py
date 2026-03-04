#!/usr/bin/env python3
"""
bpm_energy_enhancer.py  —  BPM-aware energy rating for Rekordbox library
================================================================================
Reads real BPM from audio file ID3/metadata tags, then re-scores every track's
star rating using a genre-contextual BPM percentile system. Also writes real
BPM values into the XML Bpm field so Rekordbox displays them.

PROBLEM BEING SOLVED
  The keyword-based system assigns a fixed default star rating per genre
  (e.g., all House = 4★, all World = 2★), leaving 58% of tracks at exactly
  3★ with no differentiation. This script uses real BPM data to rank tracks
  WITHIN each genre family — so a fast House track beats a slow one, and
  an energetic World track gets recognised over a chill one.

SCORING METHOD  (per-genre-family BPM percentile)
  Tracks are grouped into broad genre families, then sorted by BPM.
  Each track's percentile position within its family maps to stars:

    80–100th  →  5★  PEAK    (banger / floor-filler / anthem)
    50– 80th  →  4★  HIGH    (floor-builder / peak-hour)
    20– 50th  →  3★  MID     (versatile / mid-set)
     0– 20th  →  2★  LOW     (opener / cool-down / slow for the genre)

  Special overrides (keyword anchors from tag_library are preserved):
    • Rating already 1★ (Tools, Loops, Ambient) → kept as-is, no BPM change
    • Track has no BPM in ID3 tags → keep existing keyword-based rating

FIELDS UPDATED PER TRACK
  Bpm      ←  real BPM from ID3 tags  (e.g. "128.00"; was "0.00" for all)
  Rating   ←  new stars × 51          (Rekordbox scale: 51=★ … 255=★★★★★)
  Comments ←  "SubGenre | ENERGY | 128 BPM"  (e.g. "Tech House | PEAK | 129 BPM")

COLOURS are preserved (encode genre character, not energy).

USAGE
  python3 bpm_energy_enhancer.py              # preview — no files changed
  python3 bpm_energy_enhancer.py --write      # write rekordbox_tagged.xml

WORKFLOW
  1. python3 tag_to_rekordbox.py --write --playlists
  2. python3 organize_event_sets.py --write
  3. python3 bpm_energy_enhancer.py --write   ← this script
  4. Import rekordbox_tagged.xml into Rekordbox
"""

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote
from collections import defaultdict

try:
    import mutagen
    from mutagen.id3 import ID3, ID3NoHeaderError
    from mutagen.flac import FLAC
    from mutagen.mp4 import MP4
    from mutagen import File as MutagenFile
except ImportError:
    print("ERROR: mutagen not installed.")
    print("  Run:  pip install mutagen --break-system-packages")
    sys.exit(1)

# ── Paths ─────────────────────────────────────────────────────────────────────
HERE     = Path(__file__).resolve().parent
XML_PATH = HERE / "rekordbox_tagged.xml"

# Mac → VM path translation
MAC_ROOT = "/Users/Lionmit/Music/"
VM_ROOT  = str(HERE) + "/"          # e.g. /sessions/busy-funny-noether/mnt/Music/

# ── Energy constants ──────────────────────────────────────────────────────────
ENERGY_LABEL = {1: "LOW", 2: "LOW", 3: "MID", 4: "HIGH", 5: "PEAK"}

# ── BPM percentile → star thresholds ─────────────────────────────────────────
def percentile_to_stars(pct: float) -> int:
    """
    Map a BPM percentile (0–100) within a genre family to star rating.
    Intentionally skewed upward: most playable DJ tracks are at least 3★.
    """
    if pct >= 80:  return 5   # top quintile  → PEAK
    if pct >= 50:  return 4   # upper third   → HIGH
    if pct >= 20:  return 3   # middle band   → MID
    return 2                  # bottom quintile → LOW  (slow for the genre)


# ── Genre family mapping ──────────────────────────────────────────────────────
def genre_family(genre: str) -> str:
    """
    Map a specific Genre/subgenre string to a broad family for BPM percentile
    grouping. Tracks within the same family compete on BPM together.
    """
    g = (genre or "").lower()

    # Electronic (all electronic subgenres — ranked by BPM within the family)
    if any(x in g for x in (
        'trance', 'techno', 'drum & bass', 'drum and bass', 'd&b', 'dnb',
        'psytrance', 'psy ', ' psy', 'goa', 'edm', 'big room', 'future bass',
        'breakbeat', 'electro', 'synth', 'trip-hop', 'lo-fi', 'lo fi',
        'indie electronic', 'electronic', 'bass', 'dubstep', 'global bass',
        'nitzhonot', 'new wave', 'industrial', 'hyperpop', 'ambient',
        'organic bass', 'downtempo', 'chillout', 'progressive psy',
        'melodic house', 'french house',
    )):
        return 'Electronic'

    # House (BPM range 118–135; higher = more intense)
    if any(x in g for x in (
        'house', 'disco', 'uk dance', 'afro house', 'afro tech',
        'deep house', 'tech house', 'progressive house', 'club/dance pop',
    )):
        return 'House'

    # Hip-Hop (BPM range 70–115; higher BPM = more upbeat)
    if any(x in g for x in (
        'hip-hop', 'hip hop', 'hiphop', 'trap', 'boom bap', 'r&b',
        'neo soul', 'new school', 'rap',
    )):
        return 'Hip-Hop'

    # Israeli (mixed tempo; percentile relative to the whole Israeli family)
    if any(x in g for x in (
        'israeli', 'hebrew', 'mizrahi', 'mediterranean trap', 'ethno-fusion',
        'ethno fusion', 'eurovision', 'shirei', 'israeli & hebrew',
    )):
        return 'Israeli'

    # Pop (commercial / dance pop — varied BPM)
    if any(x in g for x in (
        'pop', 'commercial', 'dance pop',
    )):
        return 'Pop'

    # Rock (60–160 BPM; harder/faster = more energy)
    if any(x in g for x in (
        'rock', 'alternative', 'punk', 'metal', 'grunge', 'indie rock',
    )):
        return 'Rock'

    # World (ecstatic dance, global bass, African, Latin — varied but BPM-correlated)
    if any(x in g for x in (
        'world', 'ecstatic', 'afro', 'african', 'latin', 'reggae',
        'ska', 'cumbia', 'salsa', 'amapiano', 'folk', 'celtic',
        'dub', 'roots',
    )):
        return 'World'

    # Classics (50s–90s pop/rock — varied BPM)
    if any(x in g for x in (
        'classic', 'oldies', 'vintage', '50s', '60s', '70s', '80s', '90s',
        '60', '70', '80', '90',
    )):
        return 'Classics'

    return 'Other'


# ── Path translation ──────────────────────────────────────────────────────────
def mac_to_vm(location_url: str) -> str | None:
    """
    Convert a Rekordbox Location URL to a VM filesystem path.
    Returns None if translation fails.
    """
    try:
        path = unquote(location_url.replace("file://", ""))
        if path.startswith(MAC_ROOT):
            vm_path = VM_ROOT + path[len(MAC_ROOT):]
            return vm_path
        # Already a VM path or unrecognised prefix
        return path if Path(path).exists() else None
    except Exception:
        return None


# ── BPM reader ────────────────────────────────────────────────────────────────
def read_bpm(vm_path: str) -> float | None:
    """
    Read BPM from audio file ID3/metadata tags.
    Handles MP3 (TBPM), FLAC (bpm), M4A (tmpo), AIFF (ID3 TBPM).
    Returns float or None.
    """
    try:
        p = Path(vm_path)
        if not p.exists():
            return None
        suffix = p.suffix.lower()

        if suffix == '.mp3':
            try:
                tags = ID3(str(p))
                tbpm = tags.get('TBPM')
                if tbpm:
                    raw = str(tbpm.text[0]).strip().split()[0]
                    bpm = float(raw)
                    return bpm if 20 <= bpm <= 300 else None
            except (ID3NoHeaderError, Exception):
                pass

        elif suffix == '.flac':
            try:
                tags = FLAC(str(p))
                for key in ('bpm', 'BPM', 'Bpm'):
                    val = tags.get(key)
                    if val:
                        bpm = float(str(val[0]).strip().split()[0])
                        return bpm if 20 <= bpm <= 300 else None
            except Exception:
                pass

        elif suffix in ('.m4a', '.mp4'):
            try:
                tags = MP4(str(p))
                tmpo = tags.get('tmpo')
                if tmpo:
                    bpm = float(tmpo[0])
                    return bpm if 20 <= bpm <= 300 else None
            except Exception:
                pass

        elif suffix in ('.aiff', '.aif'):
            try:
                f = MutagenFile(str(p))
                if f and f.tags:
                    for key in ('TBPM', 'BPM', 'bpm'):
                        val = f.tags.get(key)
                        if val:
                            raw = val[0] if isinstance(val, (list, tuple)) else val
                            bpm_str = str(getattr(raw, 'text', [raw])[0] if hasattr(raw, 'text') else raw)
                            bpm = float(bpm_str.strip().split()[0])
                            return bpm if 20 <= bpm <= 300 else None
            except Exception:
                pass

        # Generic fallback using mutagen auto-detection
        try:
            f = MutagenFile(str(p), easy=True)
            if f:
                for key in ('bpm', 'BPM'):
                    val = f.get(key)
                    if val:
                        bpm = float(str(val[0]).strip().split()[0])
                        return bpm if 20 <= bpm <= 300 else None
        except Exception:
            pass

    except Exception:
        pass

    return None


# ── Main processor ────────────────────────────────────────────────────────────
def process(write: bool):
    # ── Parse XML ─────────────────────────────────────────────────────────────
    print(f"\n  Loading {XML_PATH.name} …", end=" ", flush=True)
    tree = ET.parse(XML_PATH)
    root = tree.getroot()
    collection = root.find("COLLECTION")
    tracks = collection.findall("TRACK")
    print(f"{len(tracks)} tracks")

    # ── First pass: read BPM from every audio file ────────────────────────────
    print("  Reading BPM from audio files …", flush=True)

    track_data = []   # list of dicts per track
    bpm_found  = 0
    bpm_miss   = 0
    no_file    = 0

    total = len(tracks)
    for i, track in enumerate(tracks):
        if i % 500 == 0:
            print(f"    {i:>5}/{total}  BPM found so far: {bpm_found}", flush=True)

        location  = track.get("Location", "")
        genre     = track.get("Genre", "")
        rating    = int(track.get("Rating", "0"))
        stars     = rating // 51
        comments  = track.get("Comments", "")
        bpm_xml   = track.get("Bpm", "0.00")

        # Subgenre prefix from current Comments ("Tech House | HIGH" → "Tech House")
        subgenre_prefix = comments.split(" | ")[0].strip() if " | " in comments else genre

        vm_path = mac_to_vm(location)
        bpm = None
        if vm_path:
            bpm = read_bpm(vm_path)

        if bpm is not None:
            bpm_found += 1
        elif vm_path:
            bpm_miss += 1
        else:
            no_file += 1

        family = genre_family(genre)

        track_data.append({
            "elem":    track,
            "genre":   genre,
            "family":  family,
            "stars":   stars,           # current keyword-based stars
            "bpm":     bpm,             # float or None
            "subgenre_prefix": subgenre_prefix,
            "comments": comments,
        })

    print(f"    {total}/{total}  BPM found: {bpm_found} ({bpm_found/total*100:.0f}%)")
    print(f"    BPM missing: {bpm_miss}  |  File not found: {no_file}")

    # ── Second pass: compute per-family BPM percentiles ───────────────────────
    print("  Computing genre-family BPM distributions …")

    # Group tracks with BPM by family
    family_bpms: dict[str, list] = defaultdict(list)
    for d in track_data:
        if d['bpm'] is not None:
            family_bpms[d['family']].append(d['bpm'])

    # For each family, sort and build a list to enable percentile lookups
    family_sorted: dict[str, list] = {}
    for family, bpms in family_bpms.items():
        family_sorted[family] = sorted(bpms)
        lo, hi, med = min(bpms), max(bpms), sorted(bpms)[len(bpms)//2]
        print(f"    {family:<15} n={len(bpms):>4}  BPM range {lo:.0f}–{hi:.0f}  "
              f"median {med:.0f}")

    # ── Third pass: assign new stars and update XML ───────────────────────────
    print("  Applying BPM-percentile star ratings …")

    stats = {
        "bpm_updated": 0,
        "no_bpm_kept": 0,
        "tool_kept":   0,
        "star_before": defaultdict(int),
        "star_after":  defaultdict(int),
        "family_updated": defaultdict(int),
    }

    changes_log = []  # for preview report

    for d in track_data:
        old_stars = d['stars']
        stats["star_before"][old_stars] += 1

        bpm = d['bpm']
        family = d['family']

        # ── Rule 1: Tools/ambient (1★) — never touched ─────────────────────
        if old_stars == 1:
            stats["star_after"][old_stars] += 1
            stats["tool_kept"] += 1
            continue

        # ── Rule 2: No BPM data — keep existing keyword rating ─────────────
        if bpm is None:
            stats["star_after"][old_stars] += 1
            stats["no_bpm_kept"] += 1
            continue

        # ── Rule 3: BPM available — compute percentile within family ────────
        sorted_bpms = family_sorted.get(family, [])
        if not sorted_bpms:
            stats["star_after"][old_stars] += 1
            stats["no_bpm_kept"] += 1
            continue

        # Percentile rank: what fraction of tracks in this family have lower BPM?
        below = sum(1 for b in sorted_bpms if b < bpm)
        pct = (below / len(sorted_bpms)) * 100.0
        new_stars = percentile_to_stars(pct)

        stats["star_after"][new_stars] += 1
        stats["bpm_updated"] += 1
        stats["family_updated"][family] += 1

        # Build updated fields
        energy_label = ENERGY_LABEL[new_stars]
        new_rating   = new_stars * 51
        new_bpm_str  = f"{bpm:.2f}"
        # Reconstruct comment: preserve subgenre prefix, update energy, add BPM
        prefix = d['subgenre_prefix']
        new_comment = f"{prefix} | {energy_label} | {bpm:.0f} BPM"

        if write:
            d['elem'].set("Rating",   str(new_rating))
            d['elem'].set("Bpm",      new_bpm_str)
            d['elem'].set("Comments", new_comment)

        # Log notable changes for preview
        if new_stars != old_stars:
            name = d['elem'].get("Name", "")[:50]
            changes_log.append(
                (d['genre'], bpm, pct, old_stars, new_stars, name)
            )

    # ── Write XML ─────────────────────────────────────────────────────────────
    if write:
        # Re-indent / clean the tree before writing
        tree.write(XML_PATH, encoding="unicode", xml_declaration=True)

    # ── Report ────────────────────────────────────────────────────────────────
    print()
    print("=" * 70)
    mode = "PREVIEW (no files changed)" if not write else "WRITE MODE"
    print(f"  bpm_energy_enhancer.py  —  {mode}")
    print("=" * 70)
    print(f"  Total tracks           : {total:>5}")
    print(f"  BPM data read          : {bpm_found:>5}  ({bpm_found/total*100:.0f}%)")
    print(f"  Ratings updated by BPM : {stats['bpm_updated']:>5}")
    print(f"  Kept (no BPM / tool)   : {stats['no_bpm_kept'] + stats['tool_kept']:>5}")
    print()
    print("  STAR DISTRIBUTION  (before → after)")
    for s in range(1, 6):
        before = stats["star_before"].get(s, 0)
        after  = stats["star_after"].get(s, 0)
        bar    = "█" * (after // 30)
        print(f"    {s}★ : {before:>5}  →  {after:>5}  {bar}")
    print()
    print("  TRACKS UPDATED BY GENRE FAMILY:")
    for fam, cnt in sorted(stats["family_updated"].items(), key=lambda x: -x[1]):
        print(f"    {fam:<15}  {cnt:>5}")
    print()

    # Show sample star changes for preview
    if not write and changes_log:
        print("  SAMPLE CHANGES (star rating changed; first 20):")
        print(f"  {'Genre':<30} {'BPM':>6} {'Pct':>6}  {'Old':>4} → {'New':<4}  Track")
        print("  " + "-" * 66)
        for genre, bpm, pct, old_s, new_s, name in changes_log[:20]:
            arrow = "↑" if new_s > old_s else "↓"
            print(f"  {genre:<30} {bpm:>6.1f} {pct:>5.0f}%  {old_s}★  {arrow} {new_s}★  {name}")
        if len(changes_log) > 20:
            print(f"  … and {len(changes_log) - 20} more changes")
        print()

    if write:
        print(f"  ✅  Written: {XML_PATH.name}")
        print()
        print("  NEXT STEPS IN REKORDBOX:")
        print("    File → Import → Import rekordbox Library…")
        print(f"    Select:  {XML_PATH.name}")
        print("    ✓  Star ratings and BPM updated on all tracks with ID3 BPM data.")
        print("    ✓  Comments updated to 'SubGenre | ENERGY | BPM'.")
        print("    ✓  Cue points, loops and beat-grid data are unchanged.")
    else:
        print("  Run with --write to apply changes.")

    print("=" * 70)
    print()


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="BPM-aware energy rating enhancer for Rekordbox XML"
    )
    ap.add_argument(
        "--write", action="store_true",
        help="Write changes to rekordbox_tagged.xml (default: preview only)"
    )
    args = ap.parse_args()
    process(write=args.write)
