#!/usr/bin/env python3
"""Build the bundled artist-to-genre index from the MusicBrainz artist dump.

Run this occasionally, not at install time. It produces the compact file that
ships with DJOrganizer so the tool knows hundreds of thousands of artists with
no internet connection at all.

Why this exists
---------------
Hand-written keyword lists do not scale. On a real 1,736 track library they
left 47 percent unclassified, and the cause was simply not knowing the
artists: that one library held 1,061 distinct names. A curated list of 1,295
artists moved the number by two points. The answer is not another list, it is
real data.

Source and licence
------------------
MusicBrainz JSON data dumps, https://data.metabrainz.org/pub/musicbrainz/data/json-dumps/
The core data, including the artist genre and tag associations used here, is
released under Creative Commons Zero. That is what makes it safe to extract,
compress and redistribute inside an MIT licensed project. Attribution is not
legally required under CC0, and it is included anyway in LICENSE-DATA.md.

MusicBrainz also absorbed roughly six million Discogs, Last.fm and TagTraum
genre tags in 2021, so the DJ-grained vocabulary this tool needs, "deep house",
"uk garage", "baile funk", is already present in these tags. There is no need
to also parse the far larger Discogs release dump.

Usage
-----
    python3 tools/build_artist_index.py /path/to/artist.tar.xz

Writes engine/artist_index.json.gz next to the engine package.
"""
from __future__ import annotations

import gzip
import json
import re
import sys
import tarfile
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.enrich import TAG_TO_GENRE          # noqa: E402
from engine.genres import CORE_GENRES           # noqa: E402

OUT = ROOT / "engine" / "artist_index.json.gz"

# A tag needs at least this many votes to count. Filters out one-person
# opinions and the long tail of joke tags.
MIN_TAG_VOTES = 1

# Names this short collide with ordinary words and were the source of real
# misfiles: "sl", "air", "mya", "tlc".
MIN_NAME_LEN = 4

# Names that are common English words. Even at full length these match inside
# unrelated titles, so they are dropped rather than shipped as traps.
BANNED_NAMES = {
    "love", "life", "time", "rain", "fire", "gold", "home", "hope", "soul",
    "dream", "dreams", "money", "heart", "hearts", "queen", "king", "boys",
    "girls", "water", "sugar", "honey", "smile", "angel", "magic", "sun",
    "moon", "star", "stars", "night", "day", "days", "one", "two", "cream",
    "bread", "yes", "kiss", "prince", "future", "rush", "boston", "chicago",
    "america", "europe", "poison", "journey", "toto", "train", "muse",
    "garbage", "blur", "pulp", "sade", "air", "war", "free", "alive",
    "forever", "paradise", "the beat", "sound", "music", "radio", "disco",
    "house", "techno", "trance", "jazz", "soul music", "pop", "rock",
}


def norm(name: str) -> str:
    name = unicodedata.normalize("NFKC", name or "").strip().lower()
    return " ".join(name.split())


def genre_for_tags(tags) -> str | None:
    """Map MusicBrainz tags onto our folders, weighted by how many people voted.

    An earlier version returned whichever mapping rule matched first, which is
    an ordering artefact and not an opinion about the artist. It made Bjork
    hardstyle and Beyonce deep house, because a single niche tag outranked the
    tag hundreds of people actually agreed on. Votes decide now, and the rule
    order only breaks ties.
    """
    if not tags:
        return None
    scores: dict[str, int] = {}
    order = {tag: i for i, (tag, _) in enumerate(TAG_TO_GENRE)}
    for t in tags:
        name = (t.get("name") or "").lower().strip()
        if not name:
            continue
        votes = t.get("count")
        votes = 1 if votes is None else int(votes)
        if votes < MIN_TAG_VOTES:
            continue
        # Longest matching label wins for this tag, so "deep house" is not
        # read as "house".
        best = None
        for tag, genre in TAG_TO_GENRE:
            if tag in name and (best is None or len(tag) > len(best[0])):
                best = (tag, genre)
        if best:
            scores[best[1]] = scores.get(best[1], 0) + votes
    if not scores:
        return None
    # Highest vote total wins; a tie falls back to the more specific rule.
    return max(scores.items(),
               key=lambda kv: (kv[1], -min(
                   (order[t] for t, g in TAG_TO_GENRE if g == kv[0]),
                   default=999)))[0]


def main(dump_path: str) -> None:
    src = Path(dump_path)
    if not src.exists():
        sys.exit(f"Dump not found: {src}")

    index: dict[str, str] = {}
    stats = Counter()
    genre_counts: Counter = Counter()

    print(f"Reading {src.name} ...")
    with tarfile.open(src, "r:xz") as tar:
        for member in tar:
            # The archive carries a TIMESTAMP and a COPYING file alongside the
            # data. Only the JSONL payload is worth opening, and it is the one
            # large member, so size is the reliable filter.
            if not member.isfile() or member.size < 1_000_000:
                continue
            print(f"  payload: {member.name} ({member.size/1e9:.2f} GB)")
            fh = tar.extractfile(member)
            if fh is None:
                continue
            for raw in fh:
                stats["lines"] += 1
                if stats["lines"] % 250_000 == 0:
                    print(f"  {stats['lines']:>9,} artists read, "
                          f"{len(index):>7,} kept", flush=True)
                try:
                    a = json.loads(raw)
                except Exception:
                    continue
                if not isinstance(a, dict):
                    continue

                tags = (a.get("genres") or []) + (a.get("tags") or [])
                genre = genre_for_tags(tags)
                if not genre or genre not in CORE_GENRES:
                    continue

                for key in {norm(a.get("name", "")), norm(a.get("sort-name", ""))}:
                    if len(key) < MIN_NAME_LEN or key in BANNED_NAMES:
                        continue
                    if not re.search(r"[a-z0-9֐-׿؀-ۿ]", key):
                        continue
                    # First writer wins, and dumps are ordered by MBID, so
                    # prefer keeping an existing entry over churning it.
                    if key not in index:
                        index[key] = genre
                        genre_counts[genre] += 1
                        stats["kept"] += 1

    print(f"\nread   {stats['lines']:,} artist records")
    print(f"kept   {len(index):,} name to genre entries")
    print("\ntop genres in the index:")
    for g, c in genre_counts.most_common(20):
        print(f"  {c:>7,}  {CORE_GENRES[g]['name']}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8", compresslevel=9) as fh:
        json.dump(index, fh, ensure_ascii=False, separators=(",", ":"))
    size_mb = OUT.stat().st_size / 1_048_576
    print(f"\nwrote {OUT.relative_to(ROOT)}  ({size_mb:.1f} MB)")
    if size_mb > 50:
        print("  WARNING: over 50 MB is awkward to ship in a git repo. "
              "Raise MIN_TAG_VOTES to trim the long tail.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1])
