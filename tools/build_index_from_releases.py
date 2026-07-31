#!/usr/bin/env python3
"""Extend the bundled artist index using release-level genre tags.

Why a second pass exists
------------------------
Artist-level tags in MusicBrainz are sparse for anyone who arrived recently.
Sammy Virji, Hamdi and most of the 2020s bass scene have no genre on their
artist entity at all, which is exactly the music a working DJ is downloading
right now. Their RELEASES are tagged, though, because tagging happens where
people actually listen.

So this walks the release-group dump, credits every artist named on a release
with that release's genre votes, and takes each artist's strongest genre. The
artist-level index still wins wherever it has an opinion: this only fills the
silence.

Usage
-----
    python3 tools/build_index_from_releases.py /path/to/release-group.tar.xz
"""
from __future__ import annotations

import gzip
import json
import re
import sys
import tarfile
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.enrich import TAG_TO_GENRE          # noqa: E402
from engine.genres import CORE_GENRES           # noqa: E402

OUT = ROOT / "engine" / "artist_index.json.gz"
_BY_LENGTH = sorted(TAG_TO_GENRE, key=lambda kv: -len(kv[0]))

MIN_NAME_LEN = 4
# An artist needs this much release-level evidence before it counts. Release
# tags are noisier than artist tags, so the bar is higher than one vote.
MIN_TOTAL_VOTES = 2
MIN_SHARE = 0.5

BANNED = {
    "various artists", "various", "unknown", "unknown artist", "traditional",
    "soundtrack", "original soundtrack", "cast", "anonymous", "no artist",
    "love", "life", "time", "rain", "fire", "gold", "home", "hope",
    "queen", "king", "water", "sugar", "honey", "angel", "magic",
    "sun", "moon", "star", "night", "one", "two", "cream", "bread",
    "yes", "kiss", "prince", "future", "rush", "boston", "chicago",
    "america", "europe", "poison", "journey", "toto", "train", "muse",
    "garbage", "blur", "pulp", "sade", "air", "war", "free",
}


def fold(name: str) -> str:
    n = unicodedata.normalize("NFKD", str(name or "").strip().lower())
    n = "".join(c for c in n if not unicodedata.combining(c))
    return " ".join(n.split())


def genre_votes(entry) -> dict:
    """Genre votes carried by one release group."""
    out = {}
    for t in (entry.get("genres") or []) + (entry.get("tags") or []):
        name = (t.get("name") or "").lower().strip()
        if not name:
            continue
        votes = t.get("count")
        votes = 1 if votes is None else int(votes)
        if votes < 1:
            continue
        for tag, genre in _BY_LENGTH:
            if tag in name:
                out[genre] = out.get(genre, 0) + votes
                break
    return out


def main(dump: str) -> None:
    src = Path(dump)
    if not src.exists():
        sys.exit(f"Dump not found: {src}")

    tally: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    lines = 0
    with tarfile.open(src, "r:xz") as tar:
        for member in tar:
            if not member.isfile() or member.size < 1_000_000:
                continue
            print(f"reading {member.name} ({member.size/1e9:.1f} GB)", flush=True)
            fh = tar.extractfile(member)
            if fh is None:
                continue
            for raw in fh:
                lines += 1
                if lines % 500_000 == 0:
                    print(f"  {lines:>10,} releases, {len(tally):>8,} artists seen",
                          flush=True)
                if b'"genres":[' not in raw and b'"tags":[' not in raw:
                    continue
                try:
                    d = json.loads(raw)
                except Exception:
                    continue
                if not isinstance(d, dict):
                    continue
                votes = genre_votes(d)
                if not votes:
                    continue
                for credit in (d.get("artist-credit") or []):
                    a = credit.get("artist") or {}
                    key = fold(a.get("name") or credit.get("name") or "")
                    if len(key) < MIN_NAME_LEN or key in BANNED:
                        continue
                    if not re.search(r"[a-z0-9֐-׿؀-ۿ]", key):
                        continue
                    for g, v in votes.items():
                        tally[key][g] += v

    print(f"\nread {lines:,} release groups, {len(tally):,} artists with any vote")

    existing = {}
    if OUT.exists():
        with gzip.open(OUT, "rt", encoding="utf-8") as fh:
            existing = json.load(fh)
    print(f"existing artist-level index: {len(existing):,}")

    added = 0
    for artist, votes in tally.items():
        if artist in existing:
            continue                       # artist-level opinion always wins
        total = sum(votes.values())
        genre, hits = max(votes.items(), key=lambda kv: kv[1])
        if total < MIN_TOTAL_VOTES or hits / total < MIN_SHARE:
            continue
        if genre not in CORE_GENRES:
            continue
        existing[artist] = genre
        added += 1

    print(f"added from releases: {added:,}")
    print(f"index now: {len(existing):,}")
    with gzip.open(OUT, "wt", encoding="utf-8", compresslevel=9) as fh:
        json.dump(existing, fh, ensure_ascii=False, separators=(",", ":"))
    print(f"wrote {OUT.relative_to(ROOT)}  ({OUT.stat().st_size/1_048_576:.1f} MB)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1])
