# engine/genres.py
"""Genre definitions, folder mappings, BPM ranges, energy defaults.

v20 "Open Format" taxonomy.

Design principle: a working open-format DJ (weddings, parties, clubs) should
never have to invent a home for a download. Every folder below exists because
a real track can land in it. Coverage beats tidiness. An extra folder costs
nothing on disk, while a missing one sends good music to INBOX where it dies.

Folders are grouped in playing families and numbered so they sort in that
order both on disk and on a CDJ screen:

  00        tools and effects
  01 to 10  the electronic dance floor
  11 to 17  urban
  18 to 21  latin and global
  22 to 27  pop and band music
  28 to 31  eras, the open-format DJ's real weapon
  32 to 35  function rather than genre: what the track is FOR
  99        inbox, anything unclassified

BPM ranges are the typical working range. The tagger uses them for the energy
system and as a tie-breaker, not as a hard rule.
"""
from typing import Optional, Dict, List, Any, Tuple

CORE_GENRES = {
    # ---------------- the electronic dance floor ----------------
    "house":              {"name": "House",                  "folder_number": "01", "bpm_low": 118, "bpm_high": 128, "energy_default": "Mid"},
    "deep_melodic_house": {"name": "Deep & Melodic House",    "folder_number": "02", "bpm_low": 112, "bpm_high": 124, "energy_default": "Low"},
    "techno":             {"name": "Tech House & Techno",     "folder_number": "03", "bpm_low": 124, "bpm_high": 140, "energy_default": "High"},
    "afro_house":         {"name": "Afro House",              "folder_number": "04", "bpm_low": 115, "bpm_high": 125, "energy_default": "Mid"},
    "disco_nudisco":      {"name": "Disco & Nu-Disco",        "folder_number": "05", "bpm_low": 110, "bpm_high": 125, "energy_default": "Mid"},
    "trance":             {"name": "Trance & Psy",            "folder_number": "06", "bpm_low": 132, "bpm_high": 148, "energy_default": "High"},
    "electronic":         {"name": "Electronic & EDM",        "folder_number": "07", "bpm_low": 125, "bpm_high": 150, "energy_default": "High"},
    "dubstep":            {"name": "Dubstep & Bass",          "folder_number": "08", "bpm_low": 140, "bpm_high": 150, "energy_default": "High"},
    "bass_dnb_garage":    {"name": "Bass DnB & Garage",       "folder_number": "09", "bpm_low": 130, "bpm_high": 175, "energy_default": "High"},
    "hard_dance":         {"name": "Hard Dance",              "folder_number": "10", "bpm_low": 145, "bpm_high": 180, "energy_default": "High"},

    # ---------------- urban ----------------
    "hiphop":             {"name": "Hip-Hop & Rap",           "folder_number": "11", "bpm_low": 70,  "bpm_high": 100, "energy_default": "Mid"},
    "trap_twerk":         {"name": "Trap & Twerk",            "folder_number": "12", "bpm_low": 130, "bpm_high": 150, "energy_default": "High"},
    "drill":              {"name": "Drill",                   "folder_number": "13", "bpm_low": 138, "bpm_high": 145, "energy_default": "Mid"},
    "rnb_soul_modern":    {"name": "RnB & Neo-Soul",          "folder_number": "14", "bpm_low": 60,  "bpm_high": 100, "energy_default": "Low"},
    "reggae_dancehall":   {"name": "Reggae & Dancehall",      "folder_number": "15", "bpm_low": 60,  "bpm_high": 110, "energy_default": "Mid"},
    "afrobeats":          {"name": "Afrobeats",               "folder_number": "16", "bpm_low": 95,  "bpm_high": 110, "energy_default": "Mid"},
    "amapiano":           {"name": "Amapiano",                "folder_number": "17", "bpm_low": 110, "bpm_high": 118, "energy_default": "Mid"},

    # ---------------- latin and global ----------------
    "latin":              {"name": "Latin",                   "folder_number": "18", "bpm_low": 90,  "bpm_high": 130, "energy_default": "Mid"},
    "global_bass":        {"name": "Baile Funk & Global Bass","folder_number": "19", "bpm_low": 100, "bpm_high": 135, "energy_default": "High"},
    "balkan_gypsy":       {"name": "Balkan & Gypsy",          "folder_number": "20", "bpm_low": 110, "bpm_high": 160, "energy_default": "High"},
    "world_ethnic":       {"name": "World & Ethnic",          "folder_number": "21", "bpm_low": 80,  "bpm_high": 130, "energy_default": "Mid"},

    # ---------------- pop and band music ----------------
    "pop":                {"name": "Pop",                     "folder_number": "22", "bpm_low": 100, "bpm_high": 130, "energy_default": "Mid"},
    "indie_altpop":       {"name": "Indie & Alt-Pop",         "folder_number": "23", "bpm_low": 100, "bpm_high": 130, "energy_default": "Mid"},
    "rock":               {"name": "Rock & Alternative",      "folder_number": "24", "bpm_low": 100, "bpm_high": 140, "energy_default": "Mid"},
    "numetal":            {"name": "Nu-Metal & Heavy",        "folder_number": "25", "bpm_low": 90,  "bpm_high": 150, "energy_default": "High"},
    "funk_soul":          {"name": "Funk & Soul",             "folder_number": "26", "bpm_low": 95,  "bpm_high": 120, "energy_default": "Mid"},
    "country":            {"name": "Country",                 "folder_number": "27", "bpm_low": 90,  "bpm_high": 130, "energy_default": "Mid"},

    # ---------------- eras ----------------
    "oldies_motown":      {"name": "Oldies & Motown",         "folder_number": "28", "bpm_low": 90,  "bpm_high": 140, "energy_default": "Mid"},
    "eighties":           {"name": "80s",                     "folder_number": "29", "bpm_low": 100, "bpm_high": 130, "energy_default": "Mid"},
    "nineties":           {"name": "90s",                     "folder_number": "30", "bpm_low": 110, "bpm_high": 140, "energy_default": "Mid"},
    "twothousands":       {"name": "00s",                     "folder_number": "31", "bpm_low": 100, "bpm_high": 132, "energy_default": "Mid"},

    # ---------------- function rather than genre ----------------
    "mashup":             {"name": "Mashups & Bootlegs",      "folder_number": "32", "bpm_low": 100, "bpm_high": 140, "energy_default": "High"},
    "ecstatic_ceremony":  {"name": "Ecstatic & Ceremony",     "folder_number": "33", "bpm_low": 90,  "bpm_high": 130, "energy_default": "Mid"},
    "chill_downtempo":    {"name": "Chill & Downtempo",       "folder_number": "34", "bpm_low": 70,  "bpm_high": 110, "energy_default": "Low"},
    "wedding_ceremony":   {"name": "Wedding & Slow",          "folder_number": "35", "bpm_low": 60,  "bpm_high": 100, "energy_default": "Low"},

    # ---------------- screen and stage ----------------
    # Disney earns three folders of its own rather than one. At a party these
    # are three different tools: the original is nostalgia and singalong, the
    # remix is a floor weapon, the cover is a slow moment or a first dance.
    "disney":             {"name": "Disney Originals",        "folder_number": "36", "bpm_low": 70,  "bpm_high": 140, "energy_default": "Mid"},
    "disney_remix":       {"name": "Disney Remixes",          "folder_number": "37", "bpm_low": 120, "bpm_high": 150, "energy_default": "High"},
    "disney_covers":      {"name": "Disney Covers",           "folder_number": "38", "bpm_low": 60,  "bpm_high": 120, "energy_default": "Low"},
    "soundtrack":         {"name": "Film & TV",               "folder_number": "39", "bpm_low": 60,  "bpm_high": 140, "energy_default": "Mid"},
}

LOCALE_GENRES = {
    "israeli":   {"name": "Israeli & Mizrachi",      "detection_method": "hebrew_chars"},
    "arabic":    {"name": "Arabic & Middle Eastern", "detection_method": "arabic_chars"},
    "russian":   {"name": "Russian",                 "detection_method": "cyrillic_chars"},
    "kpop":      {"name": "K-Pop",                   "detection_method": "korean_chars"},
    "jpop":      {"name": "J-Pop",                   "detection_method": "japanese_chars"},
    "bollywood": {"name": "Bollywood & Desi",        "detection_method": "devanagari_chars"},
    "turkish":   {"name": "Turkish",                 "detection_method": "turkish_chars"},
}

SPECIAL_FOLDERS = {
    "tools": {"name": "Tools & FX", "folder_number": "00"},
    "inbox": {"name": "INBOX",      "folder_number": "99"},
}

# v20 split some v19 folders apart. Map the old keys forward so an existing
# djorganizer_config.txt keeps working instead of silently losing genres.
LEGACY_GENRE_ALIASES = {
    "funk_disco_soul": "funk_soul",
    "classics":        "oldies_motown",
    "bass":            "bass_dnb_garage",
    "world":           "world_ethnic",
}

AUDIO_EXTS = {".mp3", ".wav", ".flac", ".aiff", ".aif", ".m4a", ".ogg", ".wma"}

# Formats a CDJ will not play, so a DJ finds out at home and not in the booth.
CDJ_UNSUPPORTED_EXTS = {".ogg", ".wma"}


def resolve_genre_key(genre_key: str) -> str:
    """Map a legacy genre key onto its v20 replacement, or return it unchanged."""
    return LEGACY_GENRE_ALIASES.get(genre_key, genre_key)


def get_folder_name(genre_key: str) -> str:
    """Return numbered folder name, e.g. '01 House'."""
    genre_key = resolve_genre_key(genre_key)
    if genre_key in CORE_GENRES:
        g = CORE_GENRES[genre_key]
        return f"{g['folder_number']} {g['name']}"
    if genre_key in LOCALE_GENRES:
        return LOCALE_GENRES[genre_key]["name"]
    if genre_key in SPECIAL_FOLDERS:
        s = SPECIAL_FOLDERS[genre_key]
        return f"{s['folder_number']} {s['name']}"
    return "99 INBOX"


def get_energy_default(genre_key: str) -> str:
    """Return default energy level for a genre."""
    genre_key = resolve_genre_key(genre_key)
    if genre_key in CORE_GENRES:
        return CORE_GENRES[genre_key]["energy_default"]
    return "Mid"


def get_bpm_range(genre_key: str) -> Optional[Tuple[int, int]]:
    """Return (low, high) typical BPM for a genre, or None if unknown."""
    g = CORE_GENRES.get(resolve_genre_key(genre_key))
    return (g["bpm_low"], g["bpm_high"]) if g else None


def get_all_active_genres(config: Optional[Dict[str, Any]] = None) -> List[str]:
    """Return list of active genre keys based on config settings."""
    if config is None:
        return list(CORE_GENRES.keys()) + list(SPECIAL_FOLDERS.keys())
    enabled = config.get("genres_enabled", "all")
    if enabled == "all":
        genres = list(CORE_GENRES.keys())
    else:
        genres = []
        for g in enabled.split(","):
            key = resolve_genre_key(g.strip())
            if key in CORE_GENRES and key not in genres:
                genres.append(key)
    locale = config.get("locale_genres", "auto")
    if locale != "none":
        genres.extend(LOCALE_GENRES.keys())
    genres.extend(SPECIAL_FOLDERS.keys())
    return genres
