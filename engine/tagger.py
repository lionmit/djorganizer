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
    "house":            {"low": 122, "high": 128},
    "amapiano":         {"low": 110, "high": 114},
    "afrobeats":        {"low": 98,  "high": 106},
    "reggae_dancehall": {"low": 75,  "high": 100},
    "hiphop":           {"low": 78,  "high": 95},
    "latin":            {"low": 95,  "high": 120},
    "bass_dnb_garage":  {"low": 145, "high": 165},
    "pop":              {"low": 105, "high": 125},
    "funk_disco_soul":  {"low": 112, "high": 122},
    "rock":             {"low": 110, "high": 130},
    "electronic":       {"low": 128, "high": 140},
    "classics":         {"low": 100, "high": 125},
    "country":          {"low": 95,  "high": 120},
    "israeli":          {"low": 100, "high": 125},
    "arabic":           {"low": 95,  "high": 120},
    "russian":          {"low": 105, "high": 128},
    "kpop":             {"low": 105, "high": 125},
    "jpop":             {"low": 105, "high": 125},
    "bollywood":        {"low": 100, "high": 120},
    "turkish":          {"low": 100, "high": 125},
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
             "artist": None, "duration": None}
    try:
        from tinytag import TinyTag
        tag = TinyTag.get(str(filepath))
        return {
            "bpm":      tag.extra.get("bpm") if tag.extra else None,
            "key":      tag.extra.get("key") if tag.extra else None,
            "year":     tag.year,
            "genre":    tag.genre,
            "artist":   tag.artist,
            "duration": _format_duration(tag.duration),
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

    # Parse artist / title from "Artist - Title" convention
    if " - " in stem:
        artist_part, title_part = stem.split(" - ", 1)
    else:
        artist_part = metadata.get("artist") or ""
        title_part  = stem

    # Prefer metadata artist when available
    artist = metadata.get("artist") or artist_part or "Unknown"
    title  = title_part or stem

    # BPM: coerce to float if present
    raw_bpm = metadata.get("bpm")
    bpm: Optional[float] = None
    if raw_bpm is not None:
        try:
            bpm = float(raw_bpm)
        except (ValueError, TypeError):
            bpm = None

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
        key        = metadata.get("key"),
        mix_type   = detect_mix_type(name),
        vocal_type = detect_vocal_type(name),
        duration   = metadata.get("duration"),
        date_added = detect_date_added(filepath),
        era        = detect_era(year),
    )
