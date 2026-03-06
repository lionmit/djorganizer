#!/usr/bin/env python3
"""
rb_fix_ratings_encoding.py — Fix Rating encoding from XML-style to DB-style.

Problem: Previous writes stored XML-encoded ratings (51/102/153/204/255)
in djmdContent.Rating, but Rekordbox's internal DB expects simple
integers (1/2/3/4/5). That's why genres and colours display but stars don't.

Fix: Convert existing values via ORM setattr (which triggers USN tracking),
then WAL checkpoint.

Run with Rekordbox CLOSED:
    python3 ~/Music/rb_fix_ratings_encoding.py
"""
from pathlib import Path
import shutil

DB_PATH = Path.home() / "Library/Pioneer/rekordbox/master.db"

# XML-style → DB-style mapping
ENCODING_FIX = {51: 1, 102: 2, 153: 3, 204: 4, 255: 5}

print("=" * 60)
print("  REKORDBOX RATING ENCODING FIX")
print("  (51/102/153/204/255 → 1/2/3/4/5)")
print("=" * 60)

# ── Backup ────────────────────────────────────────────────────────────────
backup = DB_PATH.with_suffix(".db.pre_encoding_fix")
shutil.copy2(DB_PATH, backup)
print(f"\n  Backup: {backup}")

# ── Open via pyrekordbox ──────────────────────────────────────────────────
from pyrekordbox import Rekordbox6Database
db = Rekordbox6Database(DB_PATH)
tracks = db.get_content()

# ── Diagnose ──────────────────────────────────────────────────────────────
from collections import Counter
rating_dist = Counter()
for t in tracks:
    r = t.Rating or 0
    rating_dist[r] += 1

print(f"\n  BEFORE FIX — Rating value distribution:")
for val in sorted(rating_dist.keys()):
    count = rating_dist[val]
    note = ""
    if val in ENCODING_FIX:
        note = f"  ← WRONG (should be {ENCODING_FIX[val]})"
    elif 1 <= val <= 5:
        note = "  ✓ correct"
    elif val == 0:
        note = "  (unrated)"
    else:
        note = "  ← unexpected"
    print(f"    Rating={val:<5}  count={count:>6,}{note}")

# ── Fix via ORM setattr (triggers USN tracking) ──────────────────────────
fixed = 0
for track in tracks:
    r = track.Rating or 0
    if r in ENCODING_FIX:
        new_val = ENCODING_FIX[r]
        setattr(track, 'Rating', new_val)
        fixed += 1

print(f"\n  Fixed {fixed:,} tracks (re-encoded Rating via ORM)")

if fixed == 0:
    print("  Nothing to fix!")
    db.close()
else:
    print("  Committing …")
    db.commit()
    db.close()
    print("  ✅ ORM commit complete")

# ── WAL checkpoint + verify ───────────────────────────────────────────────
print("\n  Verifying + WAL checkpoint …")
try:
    from sqlcipher3 import dbapi2 as sqlcipher
    from pyrekordbox.db6.database import deobfuscate, BLOB

    key = deobfuscate(BLOB)
    conn = sqlcipher.connect(str(DB_PATH))
    conn.execute(f'pragma key="{key}"')

    # Rating distribution after fix
    rows = conn.execute(
        "SELECT Rating, COUNT(*) FROM djmdContent GROUP BY Rating ORDER BY Rating"
    ).fetchall()
    print(f"\n  AFTER FIX — Rating value distribution:")
    for val, count in rows:
        note = ""
        if val in ENCODING_FIX:
            note = "  ← STILL WRONG"
        elif val is not None and 1 <= val <= 5:
            note = "  ✓ correct"
        elif val == 0 or val is None:
            note = "  (unrated)"
        print(f"    Rating={str(val):<5}  count={count:>6,}{note}")

    # Sample
    samples = conn.execute(
        "SELECT Title, Rating, rb_local_usn FROM djmdContent "
        "WHERE Rating > 0 AND Rating <= 5 ORDER BY rb_local_usn DESC LIMIT 5"
    ).fetchall()
    print(f"\n  Sample tracks (correct ratings, highest USN):")
    for s in samples:
        print(f"    {(s[0] or '')[:50]:<50} {s[1]}★  USN={s[2]}")

    # WAL checkpoint
    jm = conn.execute("PRAGMA journal_mode").fetchone()
    if jm[0] == "wal":
        result = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        busy, log, cp = result
        print(f"\n  WAL checkpoint: busy={busy}, log={log}, checkpointed={cp}")
        if log == 0:
            print("  ✅ WAL fully merged into main DB")
        else:
            print(f"  ✅ Checkpointed {cp}/{log} pages")

    conn.close()
    print("  ✅ Database closed cleanly")

    # Clean up empty WAL/SHM
    for suffix in ['-wal', '-shm']:
        p = DB_PATH.parent / (DB_PATH.name + suffix)
        if p.exists() and p.stat().st_size == 0:
            p.unlink()
            print(f"  Removed empty {p.name}")

except ImportError:
    print("  ⚠️  sqlcipher3 not available for verification")
except Exception as e:
    print(f"  ⚠️  Verification error: {e}")

print("\n" + "=" * 60)
print("  → Close Rekordbox completely, then reopen it.")
print("  → Check Collection view — stars should now display!")
print("=" * 60)
