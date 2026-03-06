#!/usr/bin/env python3
"""
Diagnostic: check Rekordbox DB journal mode, WAL state, and verify writes.
Run with Rekordbox CLOSED:  python3 ~/Music/rb_diagnostic.py
"""
from pathlib import Path
import os

DB_PATH = Path.home() / "Library/Pioneer/rekordbox/master.db"

print("=" * 60)
print("  REKORDBOX DATABASE DIAGNOSTIC")
print("=" * 60)

# 1. Check for WAL/SHM files
print("\n1. FILE CHECK")
for suffix in ['', '-wal', '-shm', '-journal']:
    p = DB_PATH.parent / (DB_PATH.name + suffix)
    if p.exists():
        sz = p.stat().st_size
        print(f"   {p.name:<25} {sz:>12,} bytes")
    else:
        print(f"   {p.name:<25} NOT FOUND")

# 2. Open via pyrekordbox and check data
print("\n2. PYREKORDBOX ORM CHECK")
from pyrekordbox import Rekordbox6Database
db = Rekordbox6Database(DB_PATH)

from sqlalchemy import text
result = db.session.execute(text("PRAGMA journal_mode")).fetchone()
print(f"   Journal mode: {result[0]}")

tracks = db.get_content()
rated   = [t for t in tracks if t.Rating and t.Rating > 0]
genre_d = [t for t in tracks if t.GenreID and t.GenreID > 0]
comm_d  = [t for t in tracks if getattr(t, 'Commnt', None)]
color_d = [t for t in tracks if t.ColorID]

print(f"   Total tracks:    {len(tracks):,}")
print(f"   With Rating>0:   {len(rated):,}")
print(f"   With GenreID>0:  {len(genre_d):,}")
print(f"   With Comment:    {len(comm_d):,}")
print(f"   With ColorID:    {len(color_d):,}")

print("\n   Sample rated tracks (ORM):")
for t in rated[:3]:
    print(f"     {t.Title[:45]:<45} R={t.Rating} G={t.GenreID} Col={t.ColorID}")

db.close()

# 3. Raw sqlcipher3 check
print("\n3. RAW SQLCIPHER3 CHECK")
try:
    from sqlcipher3 import dbapi2 as sqlite3
    from pyrekordbox.db6.database import deobfuscate, BLOB
    key = deobfuscate(BLOB)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(f'pragma key="{key}"')

    jm = conn.execute("PRAGMA journal_mode").fetchone()
    print(f"   Journal mode (raw): {jm[0]}")

    # Check cipher
    for pragma in ['cipher_version', 'cipher_provider', 'cipher_page_size', 'kdf_iter']:
        try:
            r = conn.execute(f"PRAGMA {pragma}").fetchone()
            print(f"   {pragma}: {r[0] if r else 'N/A'}")
        except:
            pass

    # Count rated tracks via raw SQL
    row = conn.execute("SELECT COUNT(*) FROM djmdContent WHERE Rating > 0").fetchone()
    print(f"\n   Rated tracks (raw SQL): {row[0]:,}")

    row2 = conn.execute("SELECT COUNT(*) FROM djmdContent WHERE GenreID > 0").fetchone()
    print(f"   With GenreID (raw SQL): {row2[0]:,}")

    row3 = conn.execute("SELECT COUNT(*) FROM djmdContent WHERE Commnt IS NOT NULL AND Commnt != ''").fetchone()
    print(f"   With Comment (raw SQL): {row3[0]:,}")

    # Sample
    print("\n   Sample rated tracks (raw SQL):")
    rows = conn.execute(
        "SELECT Title, Rating, GenreID, Commnt, ColorID, rb_local_usn "
        "FROM djmdContent WHERE Rating > 0 LIMIT 3"
    ).fetchall()
    for r in rows:
        print(f"     {(r[0] or '')[:45]:<45} R={r[1]} G={r[2]} Col={r[4]} USN={r[5]}")

    # Check rb_local_usn distribution
    usn_zero = conn.execute(
        "SELECT COUNT(*) FROM djmdContent WHERE Rating > 0 AND (rb_local_usn IS NULL OR rb_local_usn = 0)"
    ).fetchone()
    usn_set = conn.execute(
        "SELECT COUNT(*) FROM djmdContent WHERE Rating > 0 AND rb_local_usn > 0"
    ).fetchone()
    print(f"\n   Rated tracks with USN=0/NULL: {usn_zero[0]:,}")
    print(f"   Rated tracks with USN>0:      {usn_set[0]:,}")

    # WAL checkpoint attempt
    if jm[0] == "wal":
        print("\n4. WAL CHECKPOINT")
        result = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
        busy, log_pages, checkpointed = result
        print(f"   busy={busy}, log_pages={log_pages}, checkpointed={checkpointed}")
        if log_pages == 0:
            print("   ✅ WAL is clean — all data is in main DB file")
        else:
            print(f"   Checkpointed {checkpointed}/{log_pages} WAL pages into main DB")

    # Check agentRegistry table
    print("\n5. AGENT REGISTRY CHECK")
    try:
        reg = conn.execute(
            "SELECT registry_id, id_1, int_1 FROM agentRegistry ORDER BY int_1 DESC LIMIT 5"
        ).fetchall()
        print("   Latest agentRegistry entries:")
        for r in reg:
            print(f"     registry_id={r[0]}, id_1={r[1]}, int_1(usn)={r[2]}")
    except Exception as e:
        print(f"   agentRegistry: {e}")

    conn.close()

except ImportError:
    print("   sqlcipher3 not installed — run: pip3 install sqlcipher3")
except Exception as e:
    print(f"   Error: {e}")

print("\n" + "=" * 60)
print("  DIAGNOSTIC COMPLETE")
print("=" * 60)
