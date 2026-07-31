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
    ("uk garage", "garage"), ("2 step", "garage"),
    ("bassline", "garage"), ("uk funky", "garage"),
    ("drum and bass", "dnb"), ("drum & bass", "dnb"),
    ("jungle", "dnb"), ("liquid funk", "dnb"),
    ("neurofunk", "dnb"), ("garage", "garage"),
    ("dubstep", "dubstep"), ("riddim", "dubstep"), ("brostep", "dubstep"),
    ("hardstyle", "hard_dance"), ("hardcore techno", "hard_dance"),
    ("gabber", "hard_dance"), ("happy hardcore", "hard_dance"),
    ("amapiano", "amapiano"), ("afro house", "afro_house"),
    ("afrobeats", "afrobeats"), ("afrobeat", "afrobeats"),
    ("deep house", "deep_melodic_house"), ("melodic house", "deep_melodic_house"),
    ("progressive house", "deep_melodic_house"), ("organic house", "deep_melodic_house"),
    ("tech house", "techno"), ("techno", "techno"), ("minimal techno", "techno"),
    ("acid house", "house"), ("french house", "nudisco"),
    ("nu-disco", "nudisco"), ("nu disco", "nudisco"),
    ("disco", "disco"), ("italo disco", "disco"),
    ("psytrance", "trance"), ("goa trance", "trance"), ("trance", "trance"),
    ("house", "house"),
    ("trap", "trap"), ("drill", "drill"),
    ("boom bap", "hiphop"), ("hip hop", "hiphop"), ("hip-hop", "hiphop"),
    ("rap", "hiphop"),
    ("neo soul", "rnb"), ("contemporary r&b", "rnb"),
    ("rhythm and blues", "rnb"), ("r&b", "rnb"),
    ("dancehall", "dancehall"), ("reggae", "reggae"),
    ("dub", "reggae"), ("ska", "reggae"),
    ("reggaeton", "latin"), ("salsa", "latin"), ("bachata", "latin"),
    ("cumbia", "latin"), ("latin", "latin"),
    ("funk carioca", "baile_funk"), ("baile funk", "baile_funk"),
    ("moombahton", "moombahton"),
    ("balkan", "balkan"), ("gypsy", "balkan"), ("klezmer", "balkan"),
    # Only nu-metal maps to the nu-metal crate. Plain "metal" was sending
    # every metal band in MusicBrainz there, 30,468 of them.
    ("nu metal", "numetal"), ("nu-metal", "numetal"),
    ("rap metal", "numetal"), ("rapcore", "numetal"),
    ("heavy metal", "rock"), ("death metal", "rock"),
    ("black metal", "rock"), ("thrash metal", "rock"),
    ("metalcore", "rock"), ("metal", "rock"),
    ("punk", "rock"), ("hard rock", "rock"), ("classic rock", "rock"),
    ("alternative rock", "indie_altpop"), ("indie rock", "indie_altpop"),
    ("indie pop", "indie_altpop"), ("indie", "indie_altpop"),
    ("motown", "oldies_motown"), ("rock and roll", "oldies_motown"),
    ("soul", "soul"), ("funk", "funk"), ("jazz", "jazz"),
    ("nu jazz", "chill_downtempo"), ("trip hop", "chill_downtempo"),
    ("downtempo", "chill_downtempo"), ("ambient", "chill_downtempo"),
    ("lounge", "chill_downtempo"), ("chillout", "chill_downtempo"),
    ("country", "country"), ("folk", "world_ethnic"), ("world", "world_ethnic"),
    ("soundtrack", "soundtrack"), ("film score", "soundtrack"),
    ("breakbeat", "dnb"), ("big beat", "electronic"),
    ("electro", "electronic"), ("edm", "electronic"),
    ("electronic", "electronic"), ("dance", "electronic"),
    ("pop", "pop"),
    # Crates created by the v20 split that had no tag rule at all, so every
    # artist tagged with them was dropped from the index entirely.
    ("roots reggae", "reggae"), ("rocksteady", "reggae"), ("lovers rock", "reggae"),
    ("ragga", "dancehall"), ("bashment", "dancehall"),
    ("liquid dnb", "dnb"), ("jump up", "dnb"), ("drumfunk", "dnb"),
    ("speed garage", "garage"), ("2-step", "garage"), ("future garage", "garage"),
    ("twerk", "twerk"), ("jersey club", "twerk"), ("juke", "twerk"),
    ("boom bap", "hiphop"), ("g-funk", "hiphop"), ("gangsta rap", "hiphop"),
    ("motown", "motown"), ("northern soul", "soul"), ("southern soul", "soul"),
    ("nu jazz", "jazz"), ("jazz funk", "jazz"), ("bossa nova", "jazz"),
    ("swing", "jazz"), ("bebop", "jazz"), ("big band", "jazz"),
    ("italo-disco", "disco"), ("boogie", "disco"), ("post-disco", "disco"),
    ("reggaeton", "reggaeton"), ("dembow", "reggaeton"), ("perreo", "reggaeton"),
    ("psytrance", "psytrance"), ("psychedelic trance", "psytrance"),
    ("goa", "psytrance"), ("full on", "psytrance"),
    ("tech house", "tech_house"), ("minimal", "techno"),
    ("hardcore", "hard_dance"), ("gabber", "hard_dance"), ("rawstyle", "hard_dance"),
    ("punk rock", "punk"), ("pop punk", "punk"), ("hardcore punk", "punk"),
    ("post-punk", "punk"), ("ska punk", "punk"),
    ("amapiano", "amapiano"), ("afro house", "afro_house"), ("afro tech", "afro_house"),
    ("balkan brass", "balkan"), ("turbo-folk", "balkan"),
    ("salsa", "latin"), ("bachata", "latin"), ("cumbia", "latin"), ("merengue", "latin"),
    ("drill", "drill"), ("uk drill", "drill"),
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
