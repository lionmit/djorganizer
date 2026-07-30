# engine/classifier.py
"""Genre classification engine. Priority: Tools, Locale, Core genres, Era fallback, INBOX."""
import unicodedata
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from .keywords import GENRE_KEYWORDS as _V19_KEYWORDS
from .keywords_openformat import OPENFORMAT_KEYWORDS as _OPENFORMAT
from .genres import CORE_GENRES, LOCALE_GENRES
from .keywords_openformat import (DISNEY_KEYWORDS, DISNEY_REMIX_SIGNALS,
                                  DISNEY_COVER_SIGNALS)

# An ID3 genre tag is a stronger and cheaper signal than any keyword guess,
# and most downloaded tracks carry one. Mapped explicitly rather than left to
# substring matching, which used to send "Drum & Bass" into the reggae bucket
# because "bass" appeared earlier in the walk.
TAG_GENRE_MAP = {
    "house": "house", "deep house": "deep_melodic_house",
    "melodic house": "deep_melodic_house", "progressive house": "deep_melodic_house",
    "organic house": "deep_melodic_house", "tech house": "techno",
    "techno": "techno", "minimal": "techno", "afro house": "afro_house",
    "afro tech": "afro_house", "disco": "disco_nudisco", "nu disco": "disco_nudisco",
    "nu-disco": "disco_nudisco", "indie dance / nu disco": "disco_nudisco",
    "french house": "disco_nudisco", "trance": "trance", "psytrance": "trance",
    "progressive trance": "trance", "goa": "trance", "electronic": "electronic",
    "electro": "electronic", "electro house": "electronic", "edm": "electronic",
    "dance": "electronic", "dance & edm": "electronic", "big room": "electronic",
    "dubstep": "dubstep", "riddim": "dubstep", "bass": "dubstep",
    "drum & bass": "bass_dnb_garage", "drum and bass": "bass_dnb_garage",
    "dnb": "bass_dnb_garage", "jungle": "bass_dnb_garage",
    "uk garage": "bass_dnb_garage", "ukg": "bass_dnb_garage",
    "garage": "bass_dnb_garage", "breakbeat": "bass_dnb_garage",
    "breaks": "bass_dnb_garage", "hardstyle": "hard_dance",
    "hardcore": "hard_dance", "hard dance": "hard_dance",
    "hip-hop": "hiphop", "hip hop": "hiphop", "hip-hop & rap": "hiphop",
    "rap": "hiphop", "boom bap": "hiphop", "trap": "trap_twerk",
    "twerk": "trap_twerk", "drill": "drill",
    "r&b": "rnb_soul_modern", "rnb": "rnb_soul_modern",
    "r&b & soul": "rnb_soul_modern", "neo soul": "rnb_soul_modern",
    "reggae": "reggae_dancehall", "dancehall": "reggae_dancehall",
    "dub": "reggae_dancehall", "ska": "reggae_dancehall",
    "afrobeats": "afrobeats", "afrobeat": "afrobeats", "amapiano": "amapiano",
    "latin": "latin", "reggaeton": "latin", "salsa": "latin",
    "bachata": "latin", "cumbia": "latin",
    "baile funk": "global_bass", "funk carioca": "global_bass",
    "moombahton": "global_bass", "global bass": "global_bass",
    "balkan": "balkan_gypsy", "gypsy": "balkan_gypsy", "klezmer": "balkan_gypsy",
    "world": "world_ethnic", "ethnic": "world_ethnic", "folk": "world_ethnic",
    "pop": "pop", "indie": "indie_altpop", "indie pop": "indie_altpop",
    "alternative": "indie_altpop", "rock": "rock", "hard rock": "rock",
    "classic rock": "rock", "punk": "rock", "metal": "numetal",
    "nu metal": "numetal", "nu-metal": "numetal",
    "funk": "funk_soul", "soul": "funk_soul", "motown": "oldies_motown",
    "country": "country", "80s": "eighties", "90s": "nineties",
    "2000s": "twothousands", "mashup": "mashup", "bootleg": "mashup",
    "ecstatic": "ecstatic_ceremony", "ecstatic dance": "ecstatic_ceremony",
    "medicine music": "ecstatic_ceremony", "yoga": "chill_downtempo",
    "downtempo": "chill_downtempo", "chillout": "chill_downtempo",
    "chill": "chill_downtempo", "trip hop": "chill_downtempo",
    "ambient": "chill_downtempo", "lounge": "chill_downtempo",
    "jazz": "funk_soul", "blues": "funk_soul",
    "soundtrack": "soundtrack", "score": "soundtrack",
    "disney": "disney", "children": "disney",
}

# ---------------------------------------------------------------------------
# Merged keyword table, v20.
#
# The classifier walks this dict in order and the FIRST match wins, so this
# order IS the priority. Specific and artist-driven genres are checked before
# broad ones, otherwise a wide list like Pop or Electronic swallows tracks
# that belong in a sharper crate.
#
# Rules of thumb baked into the order below:
#   - Function crates that a DJ reaches for by NAME (ecstatic, wedding) go
#     near the top, because that is how they get pulled at a gig.
#   - Genres identified by unmistakable artists (dubstep, nu-metal, drill,
#     balkan) beat genres identified by loose words.
#   - Eras sit below real genres: a 90s house record is house first.
#   - Mashups sit near the bottom on purpose. A mashup of two nu-metal tracks
#     is more useful filed under Nu-Metal than in a single undifferentiated
#     mashup pile. Only tracks whose ONLY signal is "this is a mashup" land
#     in the mashup crate.
#   - Pop and Electronic are last. They are the widest lists and would
#     otherwise win against everything.
# ---------------------------------------------------------------------------
_PRIORITY = [
    # Disney and screen music, resolved by a dedicated rule below
    "disney_remix", "disney_covers", "disney", "soundtrack",
    # function crates, pulled by name at a gig
    "ecstatic_ceremony", "wedding_ceremony",
    # unmistakable artist signatures
    "hard_dance", "dubstep", "drill", "trap_twerk", "global_bass",
    "balkan_gypsy", "amapiano", "afro_house", "afrobeats", "reggae_dancehall",
    "numetal", "trance", "techno", "deep_melodic_house", "disco_nudisco",
    "bass_dnb_garage", "house", "latin",
    # eras, below real genres
    "oldies_motown", "eighties", "nineties", "twothousands",
    # broader but still shaped
    "rnb_soul_modern", "hiphop", "indie_altpop", "rock", "funk_soul",
    "world_ethnic", "chill_downtempo", "country",
    # only when nothing else explained the track
    "mashup", "electronic", "pop",
]

def _build_keyword_table():
    merged = {"tools": _V19_KEYWORDS.get("tools", [])}
    # v19 lists that v20 kept, plus the split of funk_disco_soul
    carried = dict(_V19_KEYWORDS)
    carried["funk_soul"] = carried.pop("funk_disco_soul", [])
    for key in _PRIORITY:
        words = list(_OPENFORMAT.get(key, [])) + list(carried.get(key, []))
        if words:
            merged[key] = words
    # anything defined but not ranked still gets a chance, before INBOX
    for key, words in list(_OPENFORMAT.items()) + list(carried.items()):
        if key not in merged and key != "tools" and words:
            merged[key] = words
    return merged

GENRE_KEYWORDS = {k: [w.lower() for w in v] for k, v in _build_keyword_table().items()}

@dataclass
class ClassificationResult:
    genre: str
    rule: str

def detect_locale(text: str) -> Optional[str]:
    """Detect locale genre from Unicode characters in text."""
    for char in text:
        cat = unicodedata.category(char)
        if cat.startswith('L'):  # Letter characters only
            try:
                name = unicodedata.name(char, '')
            except ValueError:
                continue
            # Hebrew
            if 'HEBREW' in name:
                return "israeli"
            # Arabic
            if 'ARABIC' in name:
                return "arabic"
            # Cyrillic
            if 'CYRILLIC' in name:
                return "russian"
            # Korean (Hangul)
            if 'HANGUL' in name or 'KOREAN' in name:
                return "kpop"
            # Japanese (Katakana, Hiragana, CJK with Japanese context)
            if 'KATAKANA' in name or 'HIRAGANA' in name:
                return "jpop"
            # Devanagari (Hindi)
            if 'DEVANAGARI' in name:
                return "bollywood"
            # Turkish-specific characters
            if char in 'ğşıİĞŞ':
                return "turkish"
    return None

def _has_old_year(name_lower: str) -> bool:
    """Check if filename contains a pre-2000 year (matches 1900-1999 pattern)."""
    import re
    match = re.search(r'\b(19\d{2})\b', name_lower)
    return match is not None

def classify_file(filepath: Path, artist: str = "", title: str = "",
                  album: str = "", tag_genre: str = "") -> ClassificationResult:
    """Classify a single file.

    Matching runs against the filename AND the tag fields. Filenames are often
    stripped of everything useful by download sites: a real library scanned in
    testing had 1,149 tracks named things like "Ahh (320kbps)" that landed in
    INBOX, while every one of them carried a correct artist tag. Reading only
    the filename threw away the strongest signal in the file.
    """
    name = filepath.name
    parts = [name] + [p for p in (artist, title, album, tag_genre) if p]
    haystack = " | ".join(parts)
    name_lower = unicodedata.normalize('NFC', haystack).lower()

    # 1. Tools & FX — filename only. Matching tool words against tag text
    #    misfires badly, because "Kick" and "Clap" are ordinary title words.
    fname_lower = unicodedata.normalize('NFC', name).lower()
    for kw in GENRE_KEYWORDS.get("tools", []):
        if kw in fname_lower:
            return ClassificationResult("tools", f"Tool/FX keyword: '{kw}'")

    # 2. Locale detection — character-based, on tags too, since Hebrew and
    #    Arabic tracks are frequently saved under transliterated filenames.
    locale = detect_locale(haystack)
    if locale:
        return ClassificationResult(locale, f"Locale detected: {locale} characters")

    # 2b. Disney and screen music, split three ways. A Disney remix is a floor
    #     weapon, a Disney cover is a slow moment, and the original is a
    #     singalong. Resolved here so the generic "remix" lists cannot claim it.
    if any(d in name_lower for d in DISNEY_KEYWORDS):
        if any(r in name_lower for r in DISNEY_COVER_SIGNALS):
            return ClassificationResult("disney_covers", "Disney title with a cover signal")
        if any(r in name_lower for r in DISNEY_REMIX_SIGNALS):
            return ClassificationResult("disney_remix", "Disney title with a remix signal")
        return ClassificationResult("disney", "Disney title")

    # 2c. The file's own genre tag, when it maps cleanly. Cheaper and far more
    #     reliable than guessing from words in a filename.
    if tag_genre:
        tg = tag_genre.strip().lower()
        if tg in TAG_GENRE_MAP:
            return ClassificationResult(TAG_GENRE_MAP[tg], f"Genre tag: '{tag_genre}'")
        for label, bucket in TAG_GENRE_MAP.items():
            if len(label) > 4 and label in tg:
                return ClassificationResult(bucket, f"Genre tag contains '{label}'")

    # 3. Core genre keywords — first match wins
    for genre_key, keywords in GENRE_KEYWORDS.items():
        if genre_key == "tools":
            continue  # already checked
        for kw in keywords:
            if kw in name_lower:
                return ClassificationResult(genre_key, f"Keyword: '{kw}'")

    # 4. Classics fallback — year pre-2000, only when no genre keywords matched
    if _has_old_year(name_lower):
        return ClassificationResult("oldies_motown", "Year pre-2000 in filename")

    # 5. INBOX — unclassified
    return ClassificationResult("inbox", "No match — manual review needed")
