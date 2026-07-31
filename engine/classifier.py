# engine/classifier.py
"""Genre classification engine. Priority: Tools, Locale, Core genres, Era fallback, INBOX."""
import unicodedata
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
from .keywords import GENRE_KEYWORDS as _V19_KEYWORDS
from .keywords_openformat import OPENFORMAT_KEYWORDS as _OPENFORMAT
from .genres import CORE_GENRES, LOCALE_GENRES, resolve_genre_key
from .artists import lookup as artist_lookup, bulk_lookup as artist_bulk
from .decide import (Evidence, decide, remix_credit, split_collaborators,
                     W_REMIX_CREDIT, W_TITLE_KEYWORD, W_ARTIST_PRIOR,
                     W_ARTIST_KNOWN)
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
    # Disney and screen, resolved by a dedicated rule below
    "disney_remix", "disney_covers", "disney", "soundtrack",
    # function crates a DJ pulls by name
    "ecstatic_ceremony", "wedding_ceremony", "slow",
    # sharpest artist signatures first
    "hardstyle", "hard_dance", "psytrance", "dubstep", "drill", "twerk",
    "trap", "garage", "dnb", "moombahton", "baile_funk", "balkan",
    "amapiano", "dancehall", "reggae", "afro_house", "afrobeats",
    "reggaeton", "numetal", "punk", "techno", "tech_house", "trance",
    "nudisco", "disco", "deep_melodic_house", "house", "latin",
    # eras and roots below real genres
    "motown", "oldies_motown", "eighties", "nineties", "twothousands",
    # broader but still shaped
    "rnb", "soul", "hiphop", "indie_altpop", "rock", "funk", "jazz",
    "world_ethnic", "chill_downtempo", "country",
    # only when nothing else explained the track
    "mashup", "electronic", "pop",
]

def _build_keyword_table():
    merged = {"tools": _V19_KEYWORDS.get("tools", [])}
    # Route every legacy key through the alias map so a v19 name like
    # "bass_dnb_garage" can never reach the user after v20 split it into
    # Drum & Bass and UK Garage. Without this the classifier returns a key
    # the folder map and the UI label map have never heard of.
    carried = {}
    for key, words in _V19_KEYWORDS.items():
        if key == "tools":
            continue
        carried.setdefault(resolve_genre_key(key), []).extend(words)
    # Same forward-mapping for the v20 lists, which still carry a few of the
    # pre-split names so the file stays readable.
    openformat = {}
    for key, words in _OPENFORMAT.items():
        openformat.setdefault(resolve_genre_key(key), []).extend(words)

    for key in _PRIORITY:
        key = resolve_genre_key(key)
        words = list(openformat.get(key, [])) + list(carried.get(key, []))
        if words and key not in merged:
            merged[key] = words
    # anything defined but not ranked still gets a chance, before INBOX
    for key, words in list(openformat.items()) + list(carried.items()):
        if key not in merged and key != "tools" and words and key in CORE_GENRES:
            merged[key] = words
    return merged

GENRE_KEYWORDS = {k: [w.lower() for w in v] for k, v in _build_keyword_table().items()}

@dataclass
class ClassificationResult:
    genre: str
    rule: str
    confidence: int = 100        # how sure, 0 to 100
    needs_review: bool = False   # show this one to the DJ rather than bury it

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

def _first_keyword(text: str):
    """The first genre whose keyword appears, walked in priority order."""
    for genre_key, keywords in GENRE_KEYWORDS.items():
        if genre_key == "tools":
            continue
        for kw in keywords:
            if kw in text:
                return genre_key, kw
    return None


# Credits that name nobody. They used to vote, and "Unknown" was confidently
# filing tracks into World.
_NOT_AN_ARTIST = {
    "unknown", "unknown artist", "various", "various artists", "va",
    "traditional", "n/a", "none", "no artist", "untitled", "compilation",
    "soundtrack", "original soundtrack", "ost", "my mix", "mix", "dj mix",
}


def _genre_for_text(text: str):
    """Best genre for a bare name, used for remixers and each collaborator.

    The curated artist table is asked first: it holds full names, so it beats
    a keyword scan that might catch a common word inside the same string.
    """
    if not text or text.strip().lower() in _NOT_AN_ARTIST:
        return None
    known = artist_lookup(text)          # hand-checked, wins
    if known:
        return known
    known = artist_bulk(text)            # bundled MusicBrainz index
    if known:
        return known
    hit = _first_keyword(unicodedata.normalize('NFC', text).lower())
    return hit[0] if hit else None


def _looks_like_a_tool(filepath: Path, duration_seconds=None, size_bytes=None) -> bool:
    """A tool keyword only counts on a file that is actually short or tiny."""
    try:
        if size_bytes is None:
            size_bytes = filepath.stat().st_size
    except OSError:
        size_bytes = None
    if duration_seconds is not None:
        return duration_seconds < 100
    if size_bytes is not None:
        return size_bytes < 2_500_000        # roughly 100 seconds at 192 kbps
    return False


def classify_file(filepath: Path, artist: str = "", title: str = "",
                  album: str = "", tag_genre: str = "",
                  duration_seconds=None, size_bytes=None,
                  bpm=None) -> ClassificationResult:
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

    # 1. Tools & FX. A keyword alone is not enough evidence: "Kick Back" and
    #    "Scratch My Back" are real records that were being filed as one-shots.
    #    The file must also LOOK like a tool, meaning short or tiny, which is
    #    what engine.dedupe already knows how to decide.
    fname_lower = unicodedata.normalize('NFC', name).lower()
    for kw in GENRE_KEYWORDS.get("tools", []):
        if kw in fname_lower:
            if _looks_like_a_tool(filepath, duration_seconds, size_bytes):
                return ClassificationResult("tools", f"Tool/FX keyword: '{kw}'")
            break   # keyword matched but it is a real track, keep classifying

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

    # 3. Everything else is EVIDENCE, not a verdict. Collect what each source
    #    thinks and let engine.decide weigh it, so a remix credit outranks the
    #    original artist and BPM can break a collaboration tie. First-match-wins
    #    misfiled exactly those tracks.
    evidence = []

    #    3a. The remixer defines THIS version of the record.
    who = remix_credit(name) or remix_credit(title)
    if who:
        g = _genre_for_text(who)
        if g:
            evidence.append(Evidence(g, W_REMIX_CREDIT, f"Remixed by {who}"))

    #    3b. Words in the title and filename.
    hit = _first_keyword(name_lower)
    if hit:
        g, kw = hit
        evidence.append(Evidence(g, W_TITLE_KEYWORD, f"Matched '{kw}'"))

    #    3c. Each named party votes separately and weakly, so two artists from
    #        two genres produce a visible contest rather than a silent winner.
    for party in (split_collaborators(artist) or ([artist] if artist else [])):
        if not party or party.strip().lower() in _NOT_AN_ARTIST:
            continue
        known = artist_lookup(party) or artist_bulk(party)
        if known:
            # A named artist found in a real database is solid evidence.
            evidence.append(Evidence(known, W_ARTIST_KNOWN,
                                     f"{party.strip()} is known for this"))
            continue
        g = _genre_for_text(party)
        if g:
            evidence.append(Evidence(g, W_ARTIST_PRIOR,
                                     f"{party.strip()} matched a keyword"))

    if evidence:
        d = decide(evidence, bpm=bpm)
        if d.genre != "inbox":
            return ClassificationResult(
                d.genre, "; ".join(d.reasons),
                confidence=d.confidence, needs_review=d.needs_review)

    # 4. Era fallback — a pre-2000 year, only when nothing else spoke
    if _has_old_year(name_lower):
        return ClassificationResult("oldies_motown", "Year pre-2000 in filename",
                                    confidence=25, needs_review=True)

    # 5. INBOX — unclassified
    return ClassificationResult("inbox", "No match — manual review needed")
