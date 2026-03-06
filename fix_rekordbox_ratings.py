#!/usr/bin/env python3
"""
fix_rekordbox_ratings.py  v6  (pyrekordbox — Rekordbox 6 & 7)
Full DJ-ready metadata sync: Rating, Genre, Year, Comment, Color for entire collection.

DJ-ACTIONABLE SYSTEM:
  Comments → "Genre | ENERGY | DJ-ROLE | BPM"
             e.g. "House | HIGH | DRIVER | 126 BPM"
  Colors   → Energy-based (Red=BANGER, Orange=DRIVER, Yellow=GROOVE,
             Green=WARMUP, Blue=COOLDOWN)
  Stars    → 5★=BANGER, 4★=DRIVER, 3★=GROOVE, 2★=WARMUP, 1★=COOLDOWN

THREE-PASS STRATEGY
  Pass 1 — exact full-path match
            → writes Rating, Genre, Year, DJ Comment, Energy Color from XML

  Pass 2 — normalised filename fallback (en-dash vs hyphen, relocated tracks)
            → same fields from XML

  Pass 3 — BPM-percentile rating + ID3 tags for ALL remaining LOCAL tracks
            • Skips /Volumes/ (external drives — deferred)
            • Skips spotify: URIs and empty paths
            • Rating  → BPM percentile within genre family
            • Genre   → ID3 tag from audio file (mutagen)
            • Year    → ID3 tag from audio file
            • Comment → DJ-actionable (Genre | ENERGY | ROLE | BPM)
            • Color   → Energy-based from star rating
            • Tracks with no BPM → 3★ (neutral mid rating)

RESULT → Every local track gets stars + DJ-actionable comments & energy colors.

INSTALL ONCE (if not already done):
    pip3 install pyrekordbox mutagen

Run in Terminal with Rekordbox CLOSED:
    python3 ~/Music/fix_rekordbox_ratings.py          # preview only
    python3 ~/Music/fix_rekordbox_ratings.py --write  # apply changes
"""

from __future__ import annotations

import sys
import shutil
import argparse
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote

XML_PATH = Path.home() / "Music/rekordbox_tagged.xml"
DB_PATH  = Path.home() / "Library/Pioneer/rekordbox/master.db"

# Rekordbox internal DB stores star ratings as simple integers 0-5.
# (The XML export uses 0/51/102/153/204/255, but the DB does NOT.)
STARS_TO_DB = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5}

DASH_CHARS = ['\u2013', '\u2014', '\u2012', '\u2015', '\u2212', '\u2010', '\u2011']


# ── Path / filename helpers ───────────────────────────────────────────────────

def norm_filename(path: str) -> str:
    name = Path(path).name.lower()
    for ch in DASH_CHARS:
        name = name.replace(ch, '-')
    return name


def is_local(path: str) -> bool:
    """True if this is a local file we should rate (skip /Volumes/ and URIs)."""
    if not path:
        return False
    if path.startswith('spotify:') or path.startswith('http'):
        return False
    if path.startswith('/Volumes/'):
        return False
    return True


# ── BPM helper ────────────────────────────────────────────────────────────────

def get_track_bpm(track) -> float | None:
    """
    Read BPM from pyrekordbox track object.
    Rekordbox 6 stores BPM × 100 as integer (12800 = 128.00 BPM).
    """
    for attr in ('BPM', 'Bpm', 'bpm'):
        val = getattr(track, attr, None)
        if val is not None and val != 0:
            try:
                v = float(val)
                bpm = v / 100.0 if v > 300 else v
                if 20.0 <= bpm <= 300.0:
                    return bpm
            except (TypeError, ValueError):
                pass
    return None


# ── Genre family ─────────────────────────────────────────────────────────────

def genre_family(genre: str) -> str:
    g = (genre or '').lower()

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

    if any(x in g for x in (
        'house', 'disco', 'uk dance', 'afro house', 'afro tech',
        'deep house', 'tech house', 'progressive house', 'club/dance pop',
    )):
        return 'House'

    if any(x in g for x in (
        'hip-hop', 'hip hop', 'hiphop', 'trap', 'boom bap', 'r&b',
        'neo soul', 'new school', 'rap',
    )):
        return 'Hip-Hop'

    if any(x in g for x in (
        'israeli', 'hebrew', 'mizrahi', 'mediterranean trap', 'ethno-fusion',
        'ethno fusion', 'eurovision', 'shirei', 'israeli & hebrew',
    )):
        return 'Israeli'

    if any(x in g for x in ('pop', 'commercial', 'dance pop')):
        return 'Pop'

    if any(x in g for x in (
        'rock', 'alternative', 'punk', 'metal', 'grunge', 'indie rock',
    )):
        return 'Rock'

    if any(x in g for x in (
        'world', 'ecstatic', 'afro', 'african', 'latin', 'reggae',
        'ska', 'cumbia', 'salsa', 'amapiano', 'folk', 'celtic', 'dub', 'roots',
    )):
        return 'World'

    if any(x in g for x in (
        'classic', 'oldies', 'vintage', '50s', '60s', '70s', '80s', '90s',
    )):
        return 'Classics'

    return 'Other'


def percentile_to_stars(pct: float) -> int:
    if pct >= 80: return 5
    if pct >= 50: return 4
    if pct >= 20: return 3
    return 2


# ── DJ-actionable role & colour helpers ──────────────────────────────────────

def dj_role(stars: int, bpm: float | None) -> str:
    """
    Determine DJ role from star rating + BPM.
    Returns one of: BANGER, DRIVER, GROOVE, WARMUP, COOLDOWN.

    Logic:
      5★ → BANGER  (peak energy tracks)
      4★ → DRIVER  (high energy, keep the floor moving)
      3★ → GROOVE  (mid energy, solid body of the set)
      2★ → WARMUP  (low energy, opening & transitions)
      1★ → COOLDOWN (wind-down, closing tracks)
      0★ → GROOVE  (fallback)
    """
    if stars >= 5:
        return 'BANGER'
    if stars == 4:
        return 'DRIVER'
    if stars == 3:
        return 'GROOVE'
    if stars == 2:
        return 'WARMUP'
    if stars == 1:
        return 'COOLDOWN'
    return 'GROOVE'


# Rekordbox colour codes: 1=Pink, 2=Red, 3=Orange, 4=Yellow, 5=Green,
#                          6=Aqua, 7=Blue, 8=Purple
# Energy-based colour mapping (user-approved system):
#   BANGER  (5★) → Red    (code 2)
#   DRIVER  (4★) → Orange (code 3)
#   GROOVE  (3★) → Yellow (code 4)
#   WARMUP  (2★) → Green  (code 5)
#   COOLDOWN(1★) → Blue   (code 7)
#   unrated (0★) → no colour
ENERGY_TO_COLOUR_CODE = {
    5: 2,   # Red    = BANGER
    4: 3,   # Orange = DRIVER
    3: 4,   # Yellow = GROOVE
    2: 5,   # Green  = WARMUP
    1: 7,   # Blue   = COOLDOWN
    0: 0,   # no colour
}


def energy_colour_code(stars: int) -> int:
    """Map star rating → Rekordbox colour code for energy-based colouring."""
    return ENERGY_TO_COLOUR_CODE.get(stars, 0)


def build_dj_comment(genre: str, stars: int, bpm: float | None) -> str:
    """
    Build a DJ-actionable comment string.
    Format: Genre | ENERGY | DJ-ROLE | BPM
    Example: "House | HIGH | DRIVER | 126 BPM"
    """
    # Energy label from stars
    energy_map = {5: 'PEAK', 4: 'HIGH', 3: 'MID', 2: 'LOW', 1: 'LOW', 0: 'MID'}
    energy = energy_map.get(stars, 'MID')

    role = dj_role(stars, bpm)

    bpm_str = f"{bpm:.0f} BPM" if bpm else "? BPM"

    # Use genre family if specific genre is too long or empty
    g = genre.strip() if genre else 'Unknown'
    if len(g) > 40:
        g = genre_family(g)

    return f"{g} | {energy} | {role} | {bpm_str}"


# ── Genre DB helpers ─────────────────────────────────────────────────────────

def build_genre_cache(db) -> dict:
    """Load all existing genres from DB. Returns {name: id}."""
    cache = {}
    try:
        from sqlalchemy import text
        rows = db.session.execute(
            text("SELECT ID, Name FROM djmdGenre")
        ).fetchall()
        for row in rows:
            if row[1]:
                cache[row[1]] = row[0]
    except Exception as e:
        print(f"  [WARN] Could not load genre table: {e}")
    return cache


def get_or_create_genre_id(
    db, genre_name: str, cache: dict, do_create: bool
) -> int | None:
    """Return DB ID for genre_name. Creates a new row when do_create=True."""
    if not genre_name:
        return None
    if genre_name in cache:
        return cache[genre_name]
    if not do_create:
        return None   # preview mode: don't insert
    try:
        from sqlalchemy import text
        result = db.session.execute(
            text("INSERT INTO djmdGenre (Name) VALUES (:name)"),
            {'name': genre_name}
        )
        db.session.flush()
        new_id = result.lastrowid
        cache[genre_name] = new_id
        return new_id
    except Exception as e:
        print(f"  [WARN] Could not create genre '{genre_name}': {e}")
        return None


def track_genre_str(track) -> str:
    """Safely extract genre as a plain string from a pyrekordbox track object."""
    raw = getattr(track, 'Genre', None)
    if raw is None:
        return ''
    if hasattr(raw, 'Name'):
        return raw.Name or ''
    return str(raw)


# ── ID3 tag reader (mutagen) ─────────────────────────────────────────────────

def read_id3_tags(filepath: str) -> dict:
    """Read genre, year, comment from audio file using mutagen EasyID3/Easy tags."""
    result = {'genre': '', 'year': 0, 'comment': ''}
    try:
        from mutagen import File as MuFile
        audio = MuFile(filepath, easy=True)
        if audio is None:
            return result

        genres = audio.get('genre', [])
        if genres:
            result['genre'] = str(genres[0]).strip()

        dates = audio.get('date', [])
        if dates:
            yr = str(dates[0])[:4]
            if yr.isdigit():
                result['year'] = int(yr)

        # 'comment' is not always in EasyID3; try both keys
        for key in ('comment', 'description'):
            comments = audio.get(key, [])
            if comments:
                result['comment'] = str(comments[0]).strip()
                break

    except Exception:
        pass
    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main(write: bool) -> None:
    try:
        from pyrekordbox.db6 import Rekordbox6Database
    except ImportError:
        print("ERROR: pyrekordbox not installed.  Run: pip3 install pyrekordbox")
        sys.exit(1)

    mutagen_ok = False
    try:
        import mutagen  # noqa: F401
        mutagen_ok = True
    except ImportError:
        print("  [WARN] mutagen not installed — Pass 3 ID3 reading disabled.")
        print("         Run: pip3 install mutagen")

    # ── load XML ──────────────────────────────────────────────────────────────
    if not XML_PATH.exists():
        print(f"ERROR: XML not found at {XML_PATH}")
        sys.exit(1)

    print(f"Reading {XML_PATH} …")
    tree = ET.parse(XML_PATH)
    root = tree.getroot()
    col  = root.find("COLLECTION")

    xml_exact: dict[str, dict] = {}   # normalised path → data dict
    xml_fuzzy: dict[str, list] = {}   # norm filename   → [(path, data)]

    for t in col.findall("TRACK"):
        loc = t.get("Location", "")
        if not loc:
            continue

        stars_raw = int(t.get("Rating", "0")) // 51
        path = unquote(
            loc.replace("file://localhost", "").replace("file://", "")
        )

        yr_str = (t.get("Year") or "0").strip()
        year = int(yr_str) if yr_str.isdigit() else 0

        colour_str = (t.get("Colour") or "0").strip()
        colour = int(colour_str) if colour_str.isdigit() else 0

        genre_str = (t.get("Genre") or "").strip()
        stars = STARS_TO_DB[stars_raw]

        # Extract BPM from XML (AverageBpm attribute)
        xml_bpm_str = t.get("AverageBpm", "0")
        try:
            xml_bpm = float(xml_bpm_str)
            if xml_bpm < 20 or xml_bpm > 300:
                xml_bpm = None
        except (TypeError, ValueError):
            xml_bpm = None

        # Build DJ-actionable comment and energy-based colour
        dj_comment = build_dj_comment(genre_str, stars, xml_bpm)
        dj_colour  = energy_colour_code(stars)

        data = {
            'rating':  stars,
            'genre':   genre_str,
            'year':    year,
            'comment': dj_comment,
            'colour':  dj_colour,       # energy-based colour code (not XML colour)
            'bpm':     xml_bpm,
        }

        xml_exact[path] = data
        xml_fuzzy.setdefault(norm_filename(path), []).append((path, data))

    print(f"  {len(xml_exact):,} tracks loaded from XML")

    # ── open DB ───────────────────────────────────────────────────────────────
    if not DB_PATH.exists():
        print(f"ERROR: Rekordbox database not found at {DB_PATH}")
        sys.exit(1)

    print(f"Opening Rekordbox database …")
    try:
        db = Rekordbox6Database(DB_PATH)
    except Exception as e:
        print(f"ERROR opening database: {e}")
        print("Tip: make sure Rekordbox is fully closed (Cmd+Q, not just hidden).")
        sys.exit(1)

    all_tracks = list(db.get_content())
    print(f"  {len(all_tracks):,} tracks in Rekordbox database\n")

    # Build genre lookup
    genre_cache = build_genre_cache(db)
    print(f"  {len(genre_cache):,} genres already in DB")

    # Build colour lookup  (XML Colour int  →  djmdColor.ID string)
    from sqlalchemy import text as _text
    _color_rows = db.session.execute(
        _text("SELECT ID, ColorCode FROM djmdColor")
    ).fetchall()
    color_code_to_id: dict[int, str] = {}
    for row in _color_rows:
        cid, code = row[0], row[1]
        try:
            # ColorCode is NULL in some Rekordbox versions;
            # fall back to using the ID value as the key in that case.
            # (ID '1'=Pink, '2'=Red, '3'=Orange, '4'=Yellow,
            #  '5'=Green, '6'=Aqua, '7'=Blue, '8'=Purple)
            key = int(code) if code is not None else int(cid)
            color_code_to_id[key] = str(cid)
        except (TypeError, ValueError):
            pass
    # Also map 0 (no colour) → None so we can clear it
    color_code_to_id[0] = None          # type: ignore[assignment]
    print(f"  {len(_color_rows):,} colours in djmdColor table\n")

    # ── Pass 1 & 2: XML-matched tracks ───────────────────────────────────────
    xml_used: set[str]  = set()
    updates:  list      = []

    exact_matched = fuzzy_matched = pass3_rated = pass3_default = skipped = 0
    unmatched_local: list = []

    star_before: dict[int, int] = defaultdict(int)
    star_after:  dict[int, int] = defaultdict(int)
    meta_counts: dict[str, int] = defaultdict(int)   # field → # tracks changed

    for track in all_tracks:
        db_path   = track.FolderPath or ""
        cur_rb    = track.Rating or 0
        cur_stars = cur_rb          # DB stores 0-5 directly
        star_before[cur_stars] += 1

        data      = None
        match_how = None

        # Pass 1: exact
        if db_path in xml_exact:
            data      = xml_exact[db_path]
            match_how = "exact"
            xml_used.add(db_path)

        # Pass 2: normalised filename
        if data is None:
            nf    = norm_filename(db_path)
            fresh = [(xp, xd) for xp, xd in xml_fuzzy.get(nf, [])
                     if xp not in xml_used]
            if len(fresh) == 1:
                xml_path, data = fresh[0]
                match_how = "fuzzy"
                xml_used.add(xml_path)

        if data is not None:
            if match_how == "exact":
                exact_matched += 1
            else:
                fuzzy_matched += 1

            new_rb = data['rating']
            star_after[new_rb] += 1

            upd = {}

            # Rating
            if new_rb != cur_rb:
                upd['Rating'] = new_rb
                meta_counts['Rating'] += 1

            # Genre
            new_genre = data['genre']
            if new_genre:
                gid     = get_or_create_genre_id(db, new_genre, genre_cache, do_create=write)
                cur_gid = getattr(track, 'GenreID', None)
                if gid is not None and gid != cur_gid:
                    upd['GenreID'] = gid
                    meta_counts['Genre'] += 1

            # Year
            new_year = data['year']
            cur_year = getattr(track, 'ReleaseYear', 0) or 0
            if new_year and new_year != cur_year:
                upd['ReleaseYear'] = new_year
                meta_counts['Year'] += 1

            # Comment  (DJ-actionable: Genre | ENERGY | ROLE | BPM)
            new_comment = data['comment']
            cur_comment = getattr(track, 'Commnt', '') or ''
            if new_comment and new_comment != cur_comment:
                upd['Comment'] = new_comment
                meta_counts['Comment'] += 1

            # Color  (energy-based: Red=BANGER, Orange=DRIVER, etc.)
            # Force-apply on ALL XML-matched tracks — ensures every rated track
            # gets the correct energy colour regardless of what was stored before.
            new_colour_int = data['colour']   # already energy-based code
            new_colour_id  = color_code_to_id.get(new_colour_int)
            upd['ColorID'] = new_colour_id
            meta_counts['Color'] += 1

            if upd:
                updates.append((track, upd))

        else:
            if not is_local(db_path):
                skipped += 1
                star_after[cur_stars] += 1
            else:
                unmatched_local.append(track)

    # ── Pass 3: BPM-percentile + ID3 for unmatched local tracks ─────────────
    print(f"  Pass 1 exact matches    : {exact_matched:,}")
    print(f"  Pass 2 filename matches : {fuzzy_matched:,}")
    print(f"  Pass 3 candidates       : {len(unmatched_local):,}  (local, not in XML)")
    print(f"  Skipped (/Volumes etc.) : {skipped:,}\n")
    print(f"  Computing BPM-percentile + ID3 metadata for {len(unmatched_local):,} tracks …")

    p3_data: list[dict] = []
    for track in unmatched_local:
        db_path = track.FolderPath or ''
        bpm     = get_track_bpm(track)
        genre   = track_genre_str(track)
        family  = genre_family(genre)
        p3_data.append({
            'track':   track,
            'db_path': db_path,
            'bpm':     bpm,
            'genre':   genre,
            'family':  family,
        })

    # Per-family BPM distributions
    family_bpms: dict[str, list[float]] = defaultdict(list)
    for d in p3_data:
        if d['bpm'] is not None:
            family_bpms[d['family']].append(d['bpm'])

    family_sorted = {fam: sorted(bpms) for fam, bpms in family_bpms.items()}

    for fam, bpms in sorted(family_sorted.items()):
        lo  = min(bpms)
        hi  = max(bpms)
        med = sorted(bpms)[len(bpms) // 2]
        print(f"    {fam:<15}  n={len(bpms):>4}  BPM {lo:.0f}–{hi:.0f}  median {med:.0f}")

    for d in p3_data:
        track   = d['track']
        db_path = d['db_path']
        bpm     = d['bpm']
        family  = d['family']
        cur_rb  = track.Rating or 0

        # ── Star rating ──────────────────────────────────────────────────────
        if bpm is None:
            new_rb = 3
            pass3_default += 1
        else:
            sorted_bpms = family_sorted.get(family, [])
            if not sorted_bpms:
                new_rb = 3
                pass3_default += 1
            else:
                below  = sum(1 for b in sorted_bpms if b < bpm)
                pct    = (below / len(sorted_bpms)) * 100.0
                stars  = percentile_to_stars(pct)
                new_rb = stars
                pass3_rated += 1

        new_stars = new_rb  # DB stores 0-5 directly
        star_after[new_stars] += 1

        upd = {}

        if new_rb != cur_rb:
            upd['Rating'] = new_rb
            meta_counts['Rating'] += 1

        # ── ID3 metadata ─────────────────────────────────────────────────────
        id3_genre = ''
        if mutagen_ok and db_path:
            id3 = read_id3_tags(db_path)

            # Genre from ID3 (only if DB genre is empty)
            id3_genre = id3.get('genre', '')
            if id3_genre:
                cur_gid = getattr(track, 'GenreID', None)
                # Only set if track has no genre yet (don't clobber Rekordbox's own analysis)
                if cur_gid is None:
                    gid = get_or_create_genre_id(
                        db, id3_genre, genre_cache, do_create=write
                    )
                    if gid is not None:
                        upd['GenreID'] = gid
                        meta_counts['Genre'] += 1

            # Year from ID3
            id3_year = id3.get('year', 0)
            cur_year = getattr(track, 'ReleaseYear', 0) or 0
            if id3_year and id3_year != cur_year:
                upd['ReleaseYear'] = id3_year
                meta_counts['Year'] += 1

        # ── DJ-actionable comment (Genre | ENERGY | ROLE | BPM) ──────────
        # Use best available genre: ID3 tag, existing DB genre, or family
        comment_genre = id3_genre or d['genre'] or family
        dj_comment = build_dj_comment(comment_genre, new_rb, bpm)
        cur_comment = getattr(track, 'Commnt', '') or ''
        if dj_comment and dj_comment != cur_comment:
            upd['Comment'] = dj_comment
            meta_counts['Comment'] += 1

        # ── Energy-based colour ──────────────────────────────────────────
        new_colour_int = energy_colour_code(new_rb)
        new_colour_id  = color_code_to_id.get(new_colour_int)
        cur_colour_id  = getattr(track, 'ColorID', None) or None
        if new_colour_id != cur_colour_id:
            upd['ColorID'] = new_colour_id
            meta_counts['Color'] += 1

        if upd:
            updates.append((track, upd))

    # ── summary ───────────────────────────────────────────────────────────────
    total_rated = exact_matched + fuzzy_matched + len(unmatched_local)
    print(f"\n  ── SUMMARY ──────────────────────────────────────────")
    print(f"  XML-matched  (Pass 1+2)  : {exact_matched + fuzzy_matched:,}")
    print(f"  BPM-rated    (Pass 3)    : {pass3_rated:,}")
    print(f"  Default 3★   (no BPM)   : {pass3_default:,}")
    print(f"  Total local tracks rated : {total_rated:,}")
    print(f"  Skipped /Volumes/Spotify : {skipped:,}")
    print(f"  DB records to update     : {len(updates):,}")

    print(f"\n  METADATA FIELDS TO UPDATE:")
    for field in ('Rating', 'Genre', 'Year', 'Comment', 'Color'):
        n = meta_counts.get(field, 0)
        print(f"    {field:<10}: {n:,} tracks")

    print("\n  STAR DISTRIBUTION  (DB before → after)")
    for s in sorted(set(list(star_before) + list(star_after))):
        b = star_before.get(s, 0)
        a = star_after.get(s, 0)
        label = f"{s}★" if s > 0 else "0★ (unrated)"
        flag  = "" if b == a else "  ← changed"
        print(f"    {label:<16}: {b:5,}  →  {a:5,}{flag}")

    if not write:
        print("\n  [PREVIEW — run with --write to apply changes]")
        db.close()
        return

    # ── write ─────────────────────────────────────────────────────────────────
    backup = DB_PATH.with_suffix(".db.backup")
    shutil.copy2(DB_PATH, backup)
    print(f"\n  ✅ Backup saved: {backup}")

    # ALL writes go through ORM setattr so pyrekordbox's
    # RekordboxAgentRegistry tracks every change and assigns proper
    # rb_local_usn values during commit().  Without correct USN's
    # Rekordbox ignores the changes even though they sit in the DB.
    #
    # Map from our internal update-dict key → actual ORM attribute name
    field_to_attr = {
        'Rating':      'Rating',
        'GenreID':     'GenreID',
        'ReleaseYear': 'ReleaseYear',
        'Comment':     'Commnt',      # Rekordbox schema abbreviation
        'ColorID':     'ColorID',
    }

    write_count = 0
    for track, upd in updates:
        for key, value in upd.items():
            attr = field_to_attr.get(key)
            if attr:
                setattr(track, attr, value)
                write_count += 1

    db.commit()
    db.close()
    print(f"  ✅ {len(updates):,} tracks updated via ORM with USN tracking")
    print(f"     ({write_count:,} field writes across {len(updates):,} tracks)")

    # ── Force WAL checkpoint ──────────────────────────────────────────────
    # pyrekordbox closes the SQLAlchemy session but does NOT checkpoint the
    # WAL (Write-Ahead Log).  All our changes may still be sitting in
    # master.db-wal rather than merged into master.db itself.  Rekordbox
    # reads the main DB file, so we MUST force a full checkpoint.
    print("\n  Forcing WAL checkpoint …")
    try:
        from sqlcipher3 import dbapi2 as sqlcipher
        from pyrekordbox.db6.database import deobfuscate, BLOB

        key = deobfuscate(BLOB)
        conn = sqlcipher.connect(str(DB_PATH))
        conn.execute(f'pragma key="{key}"')

        # Verify we can read the DB
        jm = conn.execute("PRAGMA journal_mode").fetchone()
        print(f"    Journal mode: {jm[0]}")

        if jm[0] == "wal":
            # TRUNCATE mode: checkpoint all WAL pages into main DB,
            # then truncate the WAL file to zero bytes
            result = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            busy, log_pages, checkpointed = result
            print(f"    WAL checkpoint: busy={busy}, log={log_pages}, checkpointed={checkpointed}")
            if busy == 0 and log_pages == 0:
                print("    ✅ WAL fully merged into main DB")
            elif busy == 0:
                print(f"    ✅ Checkpointed {checkpointed}/{log_pages} pages")
            else:
                print("    ⚠️  Database was busy — some pages may not have checkpointed")
        else:
            print(f"    (not WAL mode — checkpoint not needed)")

        # Quick verification: spot-check a rated track
        row = conn.execute(
            "SELECT COUNT(*) FROM djmdContent WHERE Rating > 0"
        ).fetchone()
        print(f"    Verification: {row[0]:,} tracks with Rating > 0 in main DB")

        conn.close()
        print("  ✅ Database connection closed cleanly")
    except ImportError:
        print("    ⚠️  sqlcipher3 not available — WAL checkpoint skipped")
        print("    If changes don't appear, install: pip3 install sqlcipher3")
    except Exception as e:
        print(f"    ⚠️  WAL checkpoint error: {e}")
        print("    Changes were committed via ORM — they may still be in the WAL file")

    # Clean up any stale WAL/SHM files if they're now empty
    for suffix in ['-wal', '-shm']:
        p = DB_PATH.parent / (DB_PATH.name + suffix)
        if p.exists() and p.stat().st_size == 0:
            p.unlink()
            print(f"    Removed empty {p.name}")

    print("\n  → Reopen Rekordbox — your full collection now has complete metadata.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Full metadata sync to Rekordbox (Rating, Genre, Year, Comment, Color)"
    )
    ap.add_argument("--write", action="store_true",
                    help="Apply changes (default: preview only)")
    args = ap.parse_args()
    main(write=args.write)
