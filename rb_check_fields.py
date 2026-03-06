#!/usr/bin/env python3
"""Quick diagnostic: check what's in the DB for Comments, Colors, Genres, Ratings."""
from pathlib import Path
from collections import Counter

DB_PATH = Path.home() / "Library/Pioneer/rekordbox/master.db"

from pyrekordbox import Rekordbox6Database

db = Rekordbox6Database(DB_PATH)
tracks = db.get_content()

total = len(tracks)
print(f"Total tracks in DB: {total:,}\n")

# Rating
rating_dist = Counter()
for t in tracks:
    r = t.Rating or 0
    rating_dist[r] += 1
print("RATING distribution:")
for val in sorted(rating_dist.keys()):
    print(f"  {val}★ = {rating_dist[val]:,}")

# Comment
has_comment = sum(1 for t in tracks if (getattr(t, 'Commnt', '') or '').strip())
print(f"\nCOMMENT: {has_comment:,} / {total:,} tracks have comments")
print("Sample comments:")
count = 0
for t in tracks:
    c = (getattr(t, 'Commnt', '') or '').strip()
    if c:
        print(f"  {(t.Title or '')[:35]:<35}  → {c[:80]}")
        count += 1
        if count >= 15:
            break

# ColorID
has_color = sum(1 for t in tracks if (getattr(t, 'ColorID', None) or None) is not None)
print(f"\nCOLOR: {has_color:,} / {total:,} tracks have a ColorID")
color_dist = Counter()
for t in tracks:
    cid = getattr(t, 'ColorID', None)
    if cid:
        color_dist[cid] += 1
print("ColorID distribution:")
for cid, cnt in color_dist.most_common():
    print(f"  ColorID={cid}  count={cnt:,}")

# GenreID
has_genre = sum(1 for t in tracks if (getattr(t, 'GenreID', None) or None) is not None)
print(f"\nGENRE: {has_genre:,} / {total:,} tracks have a GenreID")

# Year
has_year = sum(1 for t in tracks if (getattr(t, 'ReleaseYear', 0) or 0) > 0)
print(f"\nYEAR: {has_year:,} / {total:,} tracks have a year")

db.close()
print("\nDone.")
