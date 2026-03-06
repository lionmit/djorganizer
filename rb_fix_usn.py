#!/usr/bin/env python3
"""
rb_fix_usn.py — Repair Rekordbox USN tracking for all metadata rows.

Problem: Earlier writes set correct Rating/Genre/Comment/Color values via raw SQL,
which bypassed pyrekordbox's RekordboxAgentRegistry.  Those rows have stale
rb_local_usn values (0 or NULL), so Rekordbox ignores the data even though
it's physically in the database.

Fix: "Touch" every track that has metadata by re-setting one attribute via ORM
setattr, which triggers RekordboxAgentRegistry.on_update() and assigns a fresh
rb_local_usn during commit().  Then force a WAL checkpoint so the changes are
in the main DB file.

Run with Rekordbox CLOSED:
    python3 ~/Music/rb_fix_usn.py
"""
from pathlib import Path
import shutil

DB_PATH = Path.home() / "Library/Pioneer/rekordbox/master.db"

print("=" * 60)
print("  REKORDBOX USN REPAIR")
print("=" * 60)

# ── Backup ───────────────────────────────────────────────────────────────
backup = DB_PATH.with_suffix(".db.pre_usn_fix")
shutil.copy2(DB_PATH, backup)
print(f"\n  Backup: {backup}")

# ── Open via pyrekordbox ─────────────────────────────────────────────────
from pyrekordbox import Rekordbox6Database
db = Rekordbox6Database(DB_PATH)
tracks = db.get_content()

# ── Diagnose current USN state ───────────────────────────────────────────
from sqlalchemy import text

usn_check = db.session.execute(text(
    "SELECT "
    "  COUNT(*) AS total, "
    "  SUM(CASE WHEN Rating > 0 THEN 1 ELSE 0 END) AS rated, "
    "  SUM(CASE WHEN Rating > 0 AND (rb_local_usn IS NULL OR rb_local_usn = 0) THEN 1 ELSE 0 END) AS rated_bad_usn, "
    "  SUM(CASE WHEN Rating > 0 AND rb_local_usn > 0 THEN 1 ELSE 0 END) AS rated_good_usn "
    "FROM djmdContent"
)).fetchone()

total, rated, bad_usn, good_usn = usn_check
print(f"\n  BEFORE REPAIR:")
print(f"    Total tracks:          {total:,}")
print(f"    With Rating > 0:       {rated:,}")
print(f"    → USN missing/zero:    {bad_usn:,}  ← these are invisible to Rekordbox")
print(f"    → USN valid:           {good_usn:,}")

if bad_usn == 0:
    print("\n  All USN values look correct. Trying a full touch anyway…")

# ── Touch every track that has metadata ──────────────────────────────────
# Setting an attribute to its current value still triggers
# RekordboxAgentRegistry.on_update() via the __setattr__ override,
# which adds the row to __update_sequence__.
# During commit(), autoincrement_local_update_count() assigns fresh
# rb_local_usn values to every touched row.

touched = 0
for track in tracks:
    has_metadata = (
        (track.Rating is not None and track.Rating > 0)
        or (track.GenreID is not None and track.GenreID > 0)
        or (getattr(track, 'Commnt', None))
        or (track.ColorID is not None)
    )
    if has_metadata:
        # Touch Rating — triggers USN tracking even if value is unchanged
        current_rating = track.Rating if track.Rating else 0
        setattr(track, 'Rating', current_rating)
        touched += 1

print(f"\n  Touched {touched:,} tracks (forced USN re-assignment)")
print("  Committing …")

db.commit()
db.close()
print("  ✅ ORM commit complete")

# ── Verify USN state after fix ───────────────────────────────────────────
print("\n  Verifying USN after fix …")
try:
    from sqlcipher3 import dbapi2 as sqlcipher
    from pyrekordbox.db6.database import deobfuscate, BLOB

    key = deobfuscate(BLOB)
    conn = sqlcipher.connect(str(DB_PATH))
    conn.execute(f'pragma key="{key}"')

    # Check USN state
    row = conn.execute(
        "SELECT "
        "  SUM(CASE WHEN Rating > 0 AND (rb_local_usn IS NULL OR rb_local_usn = 0) THEN 1 ELSE 0 END), "
        "  SUM(CASE WHEN Rating > 0 AND rb_local_usn > 0 THEN 1 ELSE 0 END) "
        "FROM djmdContent"
    ).fetchone()
    print(f"  AFTER REPAIR:")
    print(f"    Rated tracks with USN missing: {row[0]:,}")
    print(f"    Rated tracks with USN valid:   {row[1]:,}")

    # Sample a few
    samples = conn.execute(
        "SELECT Title, Rating, rb_local_usn FROM djmdContent "
        "WHERE Rating > 0 ORDER BY rb_local_usn DESC LIMIT 5"
    ).fetchall()
    print(f"\n  Sample tracks (highest USN):")
    for s in samples:
        stars = {0:0, 51:1, 102:2, 153:3, 204:4, 255:5}.get(s[1], '?')
        print(f"    {(s[0] or '')[:50]:<50} {stars}★  USN={s[2]}")

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

    # Check agentRegistry
    reg = conn.execute(
        "SELECT int_1 FROM agentRegistry ORDER BY int_1 DESC LIMIT 1"
    ).fetchone()
    if reg:
        print(f"  agentRegistry max USN: {reg[0]}")

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
print("  → Check Collection view for stars, genres, and colors.")
print("=" * 60)
