# engine/tagger.py
"""Tag extractor — derives 12 metadata tags from filename, metadata, and classification."""
import os
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .genres import get_energy_default

# ---------------------------------------------------------------------------
# TrackTags dataclass
# ---------------------------------------------------------------------------

@dataclass
class TrackTags:
    filepath: Path
    title: str
    artist: str
    genre: str
    genre_rule: str
    energy: str          # Low / Mid / High
    clean: str           # Clean / Explicit / Unmarked
    year: Optional[int]
    language: str
    bpm: Optional[float]
    key: Optional[str]
    mix_type: str
    vocal_type: str
    duration: Optional[str]
    date_added: str
    era: Optional[str]


# ---------------------------------------------------------------------------
# Energy detection
# ---------------------------------------------------------------------------

ENERGY_BPM_THRESHOLDS = {
    # Derived from bpm_low/bpm_high in genres.py, so a new genre cannot
    # ship without an energy rule.
    "house":                 {"low": 121, "high": 126},
    "deep_melodic_house":    {"low": 116, "high": 121},
    "tech_house":            {"low": 125, "high": 127},
    "techno":                {"low": 132, "high": 137},
    "afro_house":            {"low": 118, "high": 123},
    "disco":                 {"low": 115, "high": 122},
    "nudisco":               {"low": 116, "high": 121},
    "trance":                {"low": 134, "high": 138},
    "psytrance":             {"low": 143, "high": 148},
    "electronic":            {"low": 133, "high": 144},
    "dubstep":               {"low": 143, "high": 148},
    "dnb":                   {"low": 170, "high": 174},
    "garage":                {"low": 133, "high": 138},
    "hard_dance":            {"low": 156, "high": 172},
    "hiphop":                {"low": 80, "high": 93},
    "trap":                  {"low": 136, "high": 145},
    "twerk":                 {"low": 113, "high": 130},
    "drill":                 {"low": 140, "high": 144},
    "rnb":                   {"low": 73, "high": 90},
    "reggae":                {"low": 70, "high": 83},
    "dancehall":             {"low": 96, "high": 105},
    "afrobeats":             {"low": 100, "high": 107},
    "amapiano":              {"low": 112, "high": 116},
    "reggaeton":             {"low": 92, "high": 97},
    "latin":                 {"low": 103, "high": 120},
    "baile_funk":            {"low": 128, "high": 133},
    "moombahton":            {"low": 108, "high": 113},
    "balkan":                {"low": 126, "high": 148},
    "world_ethnic":          {"low": 96, "high": 118},
    "pop":                   {"low": 110, "high": 123},
    "indie_altpop":          {"low": 110, "high": 123},
    "rock":                  {"low": 113, "high": 130},
    "punk":                  {"low": 156, "high": 178},
    "numetal":               {"low": 110, "high": 135},
    "funk":                  {"low": 103, "high": 114},
    "soul":                  {"low": 83, "high": 100},
    "country":               {"low": 103, "high": 120},
    "motown":                {"low": 110, "high": 123},
    "oldies_motown":         {"low": 106, "high": 128},
    "eighties":              {"low": 110, "high": 123},
    "nineties":              {"low": 120, "high": 133},
    "twothousands":          {"low": 110, "high": 124},
    "mashup":                {"low": 113, "high": 130},
    "ecstatic_ceremony":     {"low": 103, "high": 120},
    "chill_downtempo":       {"low": 83, "high": 100},
    "jazz":                  {"low": 90, "high": 115},
    "wedding_ceremony":      {"low": 73, "high": 90},
    "slow":                  {"low": 70, "high": 83},
    "disney":                {"low": 93, "high": 123},
    "disney_remix":          {"low": 130, "high": 143},
    "disney_covers":         {"low": 80, "high": 105},
    "soundtrack":            {"low": 86, "high": 120},
    "israeli":               {"low": 100, "high": 125},
    "arabic":                {"low": 100, "high": 125},
    "russian":               {"low": 100, "high": 125},
    "kpop":                  {"low": 100, "high": 125},
    "jpop":                  {"low": 100, "high": 125},
    "bollywood":             {"low": 100, "high": 125},
    "turkish":               {"low": 100, "high": 125},
}

HIGH_ENERGY_KEYWORDS = ["festival", "banger", "anthem", "rave", "peak", "drop", "hard"]
LOW_ENERGY_KEYWORDS  = ["chill", "lounge", "ambient", "downtempo", "mellow", "smooth",
                         "relax", "sunset", "sunrise"]
MID_ENERGY_KEYWORDS  = ["remix", "radio", "club"]


def detect_energy(filename: str, bpm: Optional[float], genre: str) -> str:
    """Determine energy level. Priority: BPM → filename keywords → genre default."""
    name_lower = filename.lower()

    # 1. BPM-based (genre-relative)
    if bpm is not None:
        thresholds = ENERGY_BPM_THRESHOLDS.get(genre)
        if thresholds:
            if bpm >= thresholds["high"]:
                return "High"
            if bpm <= thresholds["low"]:
                return "Low"
            return "Mid"

    # 2. Filename keywords — check high/low first, mid last
    for kw in HIGH_ENERGY_KEYWORDS:
        if kw in name_lower:
            return "High"
    for kw in LOW_ENERGY_KEYWORDS:
        if kw in name_lower:
            return "Low"
    for kw in MID_ENERGY_KEYWORDS:
        if kw in name_lower:
            return "Mid"

    # 3. Genre default
    return get_energy_default(genre)


# ---------------------------------------------------------------------------
# Clean / explicit detection
# ---------------------------------------------------------------------------

CLEAN_KEYWORDS    = ["clean", "cln", "radio edit", "radio version", "safe"]
EXPLICIT_KEYWORDS = ["explicit", "dirty", "uncensored"]


def detect_clean(filename: str) -> str:
    """Detect whether a track is Clean, Explicit, or Unmarked."""
    name_lower = filename.lower()
    for kw in EXPLICIT_KEYWORDS:
        if kw in name_lower:
            return "Explicit"
    for kw in CLEAN_KEYWORDS:
        if kw in name_lower:
            return "Clean"
    return "Unmarked"


# ---------------------------------------------------------------------------
# Year detection
# ---------------------------------------------------------------------------

def detect_year(filename: str, metadata_year) -> Optional[int]:
    """Extract release year. Filename 4-digit year wins, then metadata_year."""
    match = re.search(r'\b(19\d{2}|20\d{2})\b', filename)
    if match:
        return int(match.group(1))
    if metadata_year is not None:
        try:
            return int(str(metadata_year).strip())
        except (ValueError, TypeError):
            pass
    return None


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

_LOCALE_TO_LANGUAGE = {
    "israeli":   "Hebrew",
    "arabic":    "Arabic",
    "russian":   "Russian",
    "kpop":      "Korean",
    "jpop":      "Japanese",
    "bollywood": "Hindi",
    "turkish":   "Turkish",
}


def _script_of_char(char: str) -> Optional[str]:
    """Return script key for a single letter character, or None."""
    try:
        name = unicodedata.name(char, '')
    except ValueError:
        return None
    if 'HEBREW' in name:
        return "israeli"
    if 'ARABIC' in name:
        return "arabic"
    if 'CYRILLIC' in name:
        return "russian"
    if 'HANGUL' in name or 'KOREAN' in name:
        return "kpop"
    if 'KATAKANA' in name or 'HIRAGANA' in name:
        return "jpop"
    if 'DEVANAGARI' in name:
        return "bollywood"
    if char in 'ğşıİĞŞ':
        return "turkish"
    return None


def detect_language(filename: str) -> str:
    """Detect language from Unicode characters in the filename."""
    for char in filename:
        cat = unicodedata.category(char)
        if cat.startswith('L'):
            script = _script_of_char(char)
            if script:
                return _LOCALE_TO_LANGUAGE[script]
    return "English"


# ---------------------------------------------------------------------------
# Mix type detection
# ---------------------------------------------------------------------------

# Order matters — more specific patterns first
_MIX_TYPE_PATTERNS = [
    ("Acapella",  r'\bacapell[ao]\b'),
    ("Mashup",    r'\bmashup\b'),
    ("Bootleg",   r'\bbootleg\b'),
    ("Dub",       r'\bdub\s*(mix|version)?\b'),
    ("Radio",     r'\bradio\s*(edit|version|mix)\b'),
    ("Extended",  r'\bextended\s*(mix|version)?\b'),
    ("Edit",      r'\bedit\b'),
    ("Remix",     r'\bremix\b'),
    ("Original",  r'\boriginal\s*(mix|version)?\b'),
]


def detect_mix_type(filename: str) -> str:
    """Detect mix type from filename. Defaults to 'Original'."""
    name_lower = filename.lower()
    for mix_type, pattern in _MIX_TYPE_PATTERNS:
        if re.search(pattern, name_lower):
            return mix_type
    return "Original"


# ---------------------------------------------------------------------------
# Vocal type detection
# ---------------------------------------------------------------------------

def detect_vocal_type(filename: str) -> str:
    """Detect vocal type from filename. Defaults to 'Vocal'."""
    name_lower = filename.lower()
    if re.search(r'\binstrumental\b', name_lower):
        return "Instrumental"
    if re.search(r'\bacapell[ao]\b', name_lower):
        return "Acapella"
    return "Vocal"


# ---------------------------------------------------------------------------
# Era detection
# ---------------------------------------------------------------------------

def detect_era(year: Optional[int]) -> Optional[str]:
    """Map a year to its decade era string."""
    if year is None:
        return None
    if year >= 2020:
        return "2020s"
    if year >= 2010:
        return "2010s"
    if year >= 2000:
        return "2000s"
    if year >= 1990:
        return "90s"
    if year >= 1980:
        return "80s"
    if year >= 1970:
        return "70s"
    if year >= 1960:
        return "60s"
    return "Pre-60s"


# ---------------------------------------------------------------------------
# Date added
# ---------------------------------------------------------------------------

def detect_date_added(filepath: Path) -> str:
    """Return ISO date string (YYYY-MM-DD) from file modification time."""
    try:
        mtime = os.path.getmtime(filepath)
        return datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
    except (OSError, ValueError):
        return datetime.now().strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Metadata reader
# ---------------------------------------------------------------------------

def read_metadata(filepath: Path) -> dict:
    """Read audio metadata via tinytag. Returns dict with None values on failure."""
    empty = {"bpm": None, "key": None, "year": None, "genre": None,
             "artist": None, "title": None, "album": None, "duration": None,
             "duration_seconds": None}
    try:
        from tinytag import TinyTag
        tag = TinyTag.get(str(filepath))
        return {
            "bpm":      tag.extra.get("bpm") if tag.extra else None,
            "key":      tag.extra.get("key") if tag.extra else None,
            "year":     tag.year,
            "genre":    tag.genre,
            "artist":   tag.artist,
            "title":    tag.title,
            "album":    tag.album,
            "duration": _format_duration(tag.duration),
            "duration_seconds": tag.duration,
        }
    except Exception:
        return empty


def _format_duration(seconds: Optional[float]) -> Optional[str]:
    """Convert seconds to MM:SS string."""
    if seconds is None:
        return None
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def tag_file(filepath: Path, classification_result, metadata: Optional[dict] = None) -> TrackTags:
    """Derive all 12 tags for a single track.

    Args:
        filepath:              Path to the audio file.
        classification_result: ClassificationResult(genre, rule) from classifier.
        metadata:              Optional pre-loaded metadata dict (used in tests to
                               avoid reading stub files). If None, read_metadata() is called.
    """
    if metadata is None:
        metadata = read_metadata(filepath)

    name = filepath.name
    stem = filepath.stem

    # Parse artist / title from "Artist - Title" convention.
    # YouTube rips use en/em dashes ("Artist – Title"), so split on those too.
    artist_part = ""
    title_part = ""
    for sep in (" - ", " – ", " — "):
        if sep in stem:
            artist_part, title_part = stem.split(sep, 1)
            break
    if not title_part:
        artist_part = metadata.get("artist") or ""
        title_part  = stem

    # Prefer metadata when available; the tag title beats a filename guess,
    # EXCEPT when the tag is a generic rip artifact ("Track 07", "01",
    # "Untitled") — then the filename is the better source.
    tag_title = metadata.get("title") or ""
    if re.fullmatch(r"(?i)\s*(?:track\s*)?\d{1,3}\s*|\s*untitled\s*", tag_title):
        tag_title = ""
    artist = metadata.get("artist") or artist_part or "Unknown"
    title  = tag_title or title_part or stem

    # BPM: coerce to float if present
    raw_bpm = metadata.get("bpm")
    bpm: Optional[float] = None
    if raw_bpm is not None:
        try:
            bpm = float(raw_bpm)
        except (ValueError, TypeError):
            bpm = None

    # Filename fallbacks: DJ pools write "102 Bpm" and Camelot keys like "(6A)"
    # into the name. YouTube rips have no ID3 at all, so the name is all we get.
    # Kept deliberately strict — a bare trailing number is only trusted after a
    # pool marker (INTRO/OUTRO/CLEAN/DIRTY), otherwise "Anthem 99" gets a fake BPM.
    if bpm is None:
        m = (re.search(r"(?:^|[\s\-_(\[])(\d{2,3})\s*bpm\b", name, re.IGNORECASE)
             or re.search(r"[(\[](9\d|1[0-7]\d)[)\]]", stem)
             or re.search(r"(?i)(?:intro|outro|clean|dirty)\s*-?\s*(9\d|1[0-7]\d)\s*$", stem))
        if m:
            candidate = float(m.group(1))
            if 60 <= candidate <= 200:
                bpm = candidate

    key = metadata.get("key")
    if not key:
        km = re.search(r"[(\[](1[0-2]|[1-9])([AB])[)\]]", stem)
        if km:
            key = km.group(1) + km.group(2)

    year = detect_year(name, metadata.get("year"))

    return TrackTags(
        filepath   = filepath,
        title      = title,
        artist     = artist,
        genre      = classification_result.genre,
        genre_rule = classification_result.rule,
        energy     = detect_energy(name, bpm, classification_result.genre),
        clean      = detect_clean(name),
        year       = year,
        language   = detect_language(name),
        bpm        = bpm,
        key        = key,
        mix_type   = detect_mix_type(name),
        vocal_type = detect_vocal_type(name),
        duration   = metadata.get("duration"),
        date_added = detect_date_added(filepath),
        era        = detect_era(year),
    )
