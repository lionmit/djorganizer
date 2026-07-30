# engine/learn.py
"""Make the sorter improve on its own, for a library nobody hand-tuned it for.

Keyword lists do not scale. Every DJ downloads different music, and the people
who wrote the lists have never heard of half of it. A test scan of one real
library left 66 percent of tracks in INBOX, and most of them were simply
current artists no list knew about.

Two mechanisms here, both offline, both requiring nothing from the user:

1. Artist propagation. If nine tracks by an artist classify as Bass DnB and
   three land in INBOX, the three are almost certainly Bass DnB too. The
   library answers the question about itself.

2. Learned overrides. When a DJ corrects a track by hand, remember the artist,
   so every future download by that artist is right the first time. This is
   the only part that needs a human, and it costs one click that the DJ was
   going to make anyway.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

LEARNED_FILE = "djorganizer_learned.json"

# An artist needs this many classified tracks before their majority genre is
# trusted, and that majority must be at least this dominant.
MIN_EVIDENCE = 2
MIN_SHARE = 0.6

_UNRESOLVED = {"inbox", "", None}


def _norm_artist(name: str) -> str:
    return " ".join((name or "").strip().lower().split())


# ---------------------------------------------------------------------------
# 1. Artist propagation, no user input at all
# ---------------------------------------------------------------------------

def propagate_by_artist(tracks: List[dict]) -> Tuple[List[dict], Dict[str, int]]:
    """Fill in INBOX tracks from what the rest of the same artist already says.

    `tracks` are dicts with at least "artist" and "genre". Modified in place
    and returned, along with a count of what each artist resolved.
    """
    votes: Dict[str, Counter] = defaultdict(Counter)
    for t in tracks:
        g = t.get("genre")
        if g not in _UNRESOLVED:
            a = _norm_artist(t.get("artist", ""))
            if a and a not in ("unknown", "various artists", "va"):
                votes[a][g] += 1

    resolved: Dict[str, int] = Counter()
    for t in tracks:
        if t.get("genre") not in _UNRESOLVED:
            continue
        a = _norm_artist(t.get("artist", ""))
        counter = votes.get(a)
        if not counter:
            continue
        total = sum(counter.values())
        genre, hits = counter.most_common(1)[0]
        if total >= MIN_EVIDENCE and hits / total >= MIN_SHARE:
            t["genre"] = genre
            t["genre_rule"] = f"Same artist: {hits} of {total} tracks are {genre}"
            resolved[genre] += 1
    return tracks, dict(resolved)


# ---------------------------------------------------------------------------
# 2. Learned overrides, from the DJ's own corrections
# ---------------------------------------------------------------------------

def load_learned(folder: Path) -> Dict[str, str]:
    path = Path(folder) / LEARNED_FILE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {k: v for k, v in data.get("artists", {}).items() if isinstance(v, str)}
    except Exception:
        return {}


def save_learned(folder: Path, artists: Dict[str, str]) -> None:
    path = Path(folder) / LEARNED_FILE
    try:
        path.write_text(json.dumps(
            {"version": 1, "artists": artists}, ensure_ascii=False, indent=1),
            encoding="utf-8")
    except OSError:
        pass


def remember_correction(folder: Path, artist: str, genre: str) -> None:
    """A DJ moved a track by hand. Never ask them about this artist again."""
    a = _norm_artist(artist)
    if not a or genre in _UNRESOLVED:
        return
    learned = load_learned(folder)
    learned[a] = genre
    save_learned(folder, learned)


def apply_learned(tracks: List[dict], learned: Dict[str, str]) -> int:
    """Apply remembered artist decisions. Returns how many tracks it fixed."""
    if not learned:
        return 0
    n = 0
    for t in tracks:
        if t.get("genre") not in _UNRESOLVED:
            continue
        g = learned.get(_norm_artist(t.get("artist", "")))
        if g:
            t["genre"] = g
            t["genre_rule"] = "You classified this artist before"
            n += 1
    return n


def learn_from_scan(tracks: List[dict], folder: Path) -> None:
    """Record every confident artist to genre link this scan established.

    Runs after propagation, so a library that was 60 percent classified teaches
    the tool about its own artists for every scan that follows.
    """
    votes: Dict[str, Counter] = defaultdict(Counter)
    for t in tracks:
        g = t.get("genre")
        if g not in _UNRESOLVED:
            a = _norm_artist(t.get("artist", ""))
            if a and a not in ("unknown", "various artists", "va"):
                votes[a][g] += 1
    learned = load_learned(folder)
    for artist, counter in votes.items():
        total = sum(counter.values())
        genre, hits = counter.most_common(1)[0]
        if total >= MIN_EVIDENCE and hits / total >= MIN_SHARE:
            learned.setdefault(artist, genre)
    save_learned(folder, learned)
