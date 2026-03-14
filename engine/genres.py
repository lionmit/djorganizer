# engine/genres.py
"""Genre definitions, folder mappings, BPM ranges, energy defaults."""
from typing import Optional, Dict, List, Any

CORE_GENRES = {
    "house":           {"name": "House",              "folder_number": "01", "bpm_low": 120, "bpm_high": 130, "energy_default": "Mid"},
    "amapiano":        {"name": "Amapiano",           "folder_number": "02", "bpm_low": 112, "bpm_high": 115, "energy_default": "Mid"},
    "afrobeats":       {"name": "Afrobeats",          "folder_number": "03", "bpm_low": 95,  "bpm_high": 110, "energy_default": "Mid"},
    "reggae_dancehall":{"name": "Reggae & Dancehall", "folder_number": "04", "bpm_low": 60,  "bpm_high": 110, "energy_default": "Mid"},
    "hiphop":          {"name": "Hip-Hop & R&B",      "folder_number": "05", "bpm_low": 70,  "bpm_high": 100, "energy_default": "Mid"},
    "latin":           {"name": "Latin",              "folder_number": "06", "bpm_low": 90,  "bpm_high": 130, "energy_default": "Mid"},
    "bass_dnb_garage": {"name": "Bass DnB & Garage",  "folder_number": "07", "bpm_low": 130, "bpm_high": 175, "energy_default": "High"},
    "pop":             {"name": "Pop",                "folder_number": "08", "bpm_low": 100, "bpm_high": 130, "energy_default": "Mid"},
    "funk_disco_soul": {"name": "Funk Disco Soul",    "folder_number": "09", "bpm_low": 110, "bpm_high": 125, "energy_default": "Mid"},
    "rock":            {"name": "Rock & Alternative",  "folder_number": "10", "bpm_low": 100, "bpm_high": 140, "energy_default": "Mid"},
    "electronic":      {"name": "Electronic",         "folder_number": "11", "bpm_low": 125, "bpm_high": 150, "energy_default": "High"},
    "classics":        {"name": "Classics",           "folder_number": "12", "bpm_low": 80,  "bpm_high": 140, "energy_default": "Mid"},
    "country":         {"name": "Country",            "folder_number": "13", "bpm_low": 90,  "bpm_high": 130, "energy_default": "Mid"},
}

LOCALE_GENRES = {
    "israeli":   {"name": "Israeli & Mizrachi",     "detection_method": "hebrew_chars"},
    "arabic":    {"name": "Arabic & Middle Eastern", "detection_method": "arabic_chars"},
    "russian":   {"name": "Russian",                "detection_method": "cyrillic_chars"},
    "kpop":      {"name": "K-Pop",                  "detection_method": "korean_chars"},
    "jpop":      {"name": "J-Pop",                  "detection_method": "japanese_chars"},
    "bollywood": {"name": "Bollywood & Desi",       "detection_method": "devanagari_chars"},
    "turkish":   {"name": "Turkish",                "detection_method": "turkish_chars"},
}

SPECIAL_FOLDERS = {
    "tools": {"name": "Tools & FX", "folder_number": "00"},
    "inbox": {"name": "INBOX",      "folder_number": "99"},
}

AUDIO_EXTS = {".mp3", ".wav", ".flac", ".aiff", ".aif", ".m4a", ".ogg", ".wma"}

def get_folder_name(genre_key: str) -> str:
    """Return numbered folder name, e.g. '01 House'."""
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
    if genre_key in CORE_GENRES:
        return CORE_GENRES[genre_key]["energy_default"]
    return "Mid"

def get_all_active_genres(config: Optional[Dict[str, Any]] = None) -> List[str]:
    """Return list of active genre keys based on config settings."""
    if config is None:
        return list(CORE_GENRES.keys()) + list(SPECIAL_FOLDERS.keys())
    enabled = config.get("genres_enabled", "all")
    if enabled == "all":
        genres = list(CORE_GENRES.keys())
    else:
        genres = [g.strip() for g in enabled.split(",") if g.strip() in CORE_GENRES]
    locale = config.get("locale_genres", "auto")
    if locale != "none":
        genres.extend(LOCALE_GENRES.keys())
    genres.extend(SPECIAL_FOLDERS.keys())
    return genres
