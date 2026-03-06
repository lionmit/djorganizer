#!/usr/bin/env python3
"""Quick diagnostic: checks djmdColor table and track ColorID/Commnt values."""

import sys, os

try:
    from pyrekordbox import Rekordbox6Database
except ImportError:
    print("ERROR: pyrekordbox not installed.")
    sys.exit(1)

print("Opening Rekordbox database...")
db = Rekordbox6Database()

from sqlalchemy import text

# ── 1. What columns does djmdColor actually have? ────────────────────────────
print("\n=== djmdColor columns ===")
cols = db.session.execute(text("PRAGMA table_info(djmdColor)")).fetchall()
for c in cols:
    print(f"  {c}")

print("\n=== djmdColor rows ===")
rows = db.session.execute(text("SELECT * FROM djmdColor")).fetchall()
if not rows:
    print("  ⚠️  TABLE IS EMPTY — this is the problem!")
else:
    for r in rows:
        print(f"  {r}")

# ── 2. Sample rated tracks ────────────────────────────────────────────────────
print("\n=== Sample rated tracks (25 tracks with rating > 0) ===")
content = db.get_content()
shown = 0
color_none_count = 0
color_set_count  = 0
comment_dj_count = 0
total_rated      = 0

for t in content:
    rating = getattr(t, 'Rating', 0) or 0
    color  = getattr(t, 'ColorID', None)
    commnt = getattr(t, 'Commnt', '') or ''

    if rating > 0:
        total_rated += 1
        if color:  color_set_count  += 1
        else:      color_none_count += 1
        if '|' in commnt: comment_dj_count += 1

        if shown < 25:
            print(f"  {rating}★  ColorID={color!r:38s}  Commnt={commnt[:60]!r}")
            shown += 1

print(f"\n=== Summary ===")
print(f"  Total rated tracks : {total_rated}")
print(f"  Tracks WITH color  : {color_set_count}")
print(f"  Tracks NO color    : {color_none_count}")
print(f"  DJ-format comments : {comment_dj_count}  (contain '|')")

db.close()
print("\nDone.")
