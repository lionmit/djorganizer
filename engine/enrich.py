# engine/enrich.py
"""Ask a real music database when the filename and tags do not say enough.

Keyword lists are written by people who have never heard the user's music. On
a real library they left 66 percent of tracks in INBOX, and most of those were
simply current artists nobody had listed. No amount of hand-tuning fixes that,
because the next user downloads different music again.

MusicBrainz answers it properly: it is free, needs no API key, and returns
community tags per artist. "Sammy Virji" comes back as uk garage, garage, uk
funky, old school bassline, which is exactly the crate that artist belongs in.

Three design choices that matter:

* Ask about the ARTIST, not the track. A library of 1,736 tracks held only
  1,061 distinct artists, and one answer covers everything they made, forever.
* Cache every answer to disk. The cost is paid once per artist, ever, and the
  cache survives every future scan and every new download by that artist.
* Stay optional. The tool must keep working with no internet at all, so this
  never runs unless the DJ asks for it, and any failure is silent.

MusicBrainz asks for one request per second and a real User-Agent. Both are
honoured here. Abusing it would get the whole tool blocked for everyone.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Callable

CACHE_FILE = "djorganizer_artist_cache.json"
USER_AGENT = "DJOrganizer/20 (https://github.com/lionmit/djorganizer)"
MB_URL = "https://musicbrainz.org/ws/2/artist/"
RATE_LIMIT_SECONDS = 1.1
TIMEOUT = 8

# MusicBrainz tag text, lowercased, mapped onto our folders. Ordered most
# specific first: an artist tagged both "drum and bass" and "electronic"
# belongs in the DnB crate, not the general one.
TAG_TO_GENRE = [
    ("uk garage", "bass_dnb_garage"), ("2 step", "bass_dnb_garage"),
    ("bassline", "bass_dnb_garage"), ("uk funky", "bass_dnb_garage"),
    ("drum and bass", "bass_dnb_garage"), ("drum & bass", "bass_dnb_garage"),
    ("jungle", "bass_dnb_garage"), ("liquid funk", "bass_dnb_garage"),
    ("neurofunk", "bass_dnb_garage"), ("garage", "bass_dnb_garage"),
    ("dubstep", "dubstep"), ("riddim", "dubstep"), ("brostep", "dubstep"),
    ("hardstyle", "hard_dance"), ("hardcore techno", "hard_dance"),
    ("gabber", "hard_dance"), ("happy hardcore", "hard_dance"),
    ("amapiano", "amapiano"), ("afro house", "afro_house"),
    ("afrobeats", "afrobeats"), ("afrobeat", "afrobeats"),
    ("deep house", "deep_melodic_house"), ("melodic house", "deep_melodic_house"),
    ("progressive house", "deep_melodic_house"), ("organic house", "deep_melodic_house"),
    ("tech house", "techno"), ("techno", "techno"), ("minimal techno", "techno"),
    ("acid house", "house"), ("french house", "disco_nudisco"),
    ("nu-disco", "disco_nudisco"), ("nu disco", "disco_nudisco"),
    ("disco", "disco_nudisco"), ("italo disco", "disco_nudisco"),
    ("psytrance", "trance"), ("goa trance", "trance"), ("trance", "trance"),
    ("house", "house"),
    ("trap", "trap_twerk"), ("drill", "drill"),
    ("boom bap", "hiphop"), ("hip hop", "hiphop"), ("hip-hop", "hiphop"),
    ("rap", "hiphop"),
    ("neo soul", "rnb_soul_modern"), ("contemporary r&b", "rnb_soul_modern"),
    ("rhythm and blues", "rnb_soul_modern"), ("r&b", "rnb_soul_modern"),
    ("dancehall", "reggae_dancehall"), ("reggae", "reggae_dancehall"),
    ("dub", "reggae_dancehall"), ("ska", "reggae_dancehall"),
    ("reggaeton", "latin"), ("salsa", "latin"), ("bachata", "latin"),
    ("cumbia", "latin"), ("latin", "latin"),
    ("funk carioca", "global_bass"), ("baile funk", "global_bass"),
    ("moombahton", "global_bass"),
    ("balkan", "balkan_gypsy"), ("gypsy", "balkan_gypsy"), ("klezmer", "balkan_gypsy"),
    ("nu metal", "numetal"), ("metal", "numetal"),
    ("punk", "rock"), ("hard rock", "rock"), ("classic rock", "rock"),
    ("alternative rock", "indie_altpop"), ("indie rock", "indie_altpop"),
    ("indie pop", "indie_altpop"), ("indie", "indie_altpop"),
    ("motown", "oldies_motown"), ("rock and roll", "oldies_motown"),
    ("soul", "funk_soul"), ("funk", "funk_soul"), ("jazz", "funk_soul"),
    ("nu jazz", "chill_downtempo"), ("trip hop", "chill_downtempo"),
    ("downtempo", "chill_downtempo"), ("ambient", "chill_downtempo"),
    ("lounge", "chill_downtempo"), ("chillout", "chill_downtempo"),
    ("country", "country"), ("folk", "world_ethnic"), ("world", "world_ethnic"),
    ("soundtrack", "soundtrack"), ("film score", "soundtrack"),
    ("breakbeat", "bass_dnb_garage"), ("big beat", "electronic"),
    ("electro", "electronic"), ("edm", "electronic"),
    ("electronic", "electronic"), ("dance", "electronic"),
    ("pop", "pop"),
]


def _norm(name: str) -> str:
    return " ".join((name or "").strip().lower().split())


def load_cache(folder: Path) -> Dict[str, Optional[str]]:
    try:
        return json.loads((Path(folder) / CACHE_FILE).read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_cache(folder: Path, cache: Dict[str, Optional[str]]) -> None:
    try:
        (Path(folder) / CACHE_FILE).write_text(
            json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError:
        pass


def genre_from_tags(tags: List[str]) -> Optional[str]:
    """First matching rule wins, and the rules run specific to general."""
    joined = " | ".join(t.lower() for t in tags)
    for tag, genre in TAG_TO_GENRE:
        if tag in joined:
            return genre
    return None


def lookup_artist(name: str) -> Optional[str]:
    """One MusicBrainz call. Returns a genre key, or None. Never raises."""
    q = urllib.parse.urlencode({"query": f'artist:"{name}"', "fmt": "json", "limit": 1})
    req = urllib.request.Request(f"{MB_URL}?{q}", headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception:
        return None
    artists = data.get("artists") or []
    if not artists:
        return None
    top = artists[0]
    # A weak name match is worse than no answer, it files music wrongly.
    if int(top.get("score", 0)) < 90:
        return None
    tags = [t.get("name", "") for t in (top.get("tags") or [])]
    return genre_from_tags(tags) if tags else None


def enrich_tracks(tracks: List[dict], folder: Path,
                  progress: Optional[Callable[[int, int, str], None]] = None,
                  stop_flag: Optional[Callable[[], bool]] = None) -> Dict[str, int]:
    """Resolve INBOX tracks by asking about their artists. Cache-first.

    Returns counts. Safe to interrupt: everything learned so far is written to
    the cache as it goes, so a cancelled run is never wasted work.
    """
    cache = load_cache(folder)
    unresolved = [t for t in tracks if t.get("genre") in ("inbox", "", None)]
    artists: List[str] = []
    seen = set()
    for t in unresolved:
        a = _norm(t.get("artist", ""))
        if a and a not in seen and a not in ("unknown", "various artists", "va"):
            seen.add(a)
            artists.append(a)

    to_query = [a for a in artists if a not in cache]
    total = len(to_query)
    for i, artist in enumerate(to_query):
        if stop_flag and stop_flag():
            break
        cache[artist] = lookup_artist(artist)
        if progress:
            progress(i + 1, total, artist)
        if (i + 1) % 25 == 0:
            save_cache(folder, cache)
        time.sleep(RATE_LIMIT_SECONDS)
    save_cache(folder, cache)

    fixed = 0
    for t in unresolved:
        g = cache.get(_norm(t.get("artist", "")))
        if g:
            t["genre"] = g
            t["genre_rule"] = "MusicBrainz artist tags"
            fixed += 1
    return {"artists_queried": len(to_query), "tracks_resolved": fixed,
            "artists_known": len(cache)}
