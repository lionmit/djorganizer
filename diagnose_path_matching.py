#!/usr/bin/env python3
"""
diagnose_path_matching.py
Compares paths between rekordbox_tagged.xml and Rekordbox database to find
why some tracks are not matching, then fixes fix_rekordbox_ratings.py.

Run in Terminal (Rekordbox CLOSED):
    python3 ~/Music/diagnose_path_matching.py
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote

XML_PATH = Path.home() / "Music/rekordbox_tagged.xml"
DB_PATH  = Path.home() / "Library/Pioneer/rekordbox/master.db"

def normalise(path: str) -> str:
    """Strip any file:// or file://localhost prefix and url-decode."""
    p = path
    if p.startswith("file://localhost"):
        p = p[len("file://localhost"):]
    elif p.startswith("file://"):
        p = p[len("file://"):]
    return unquote(p)

def main():
    try:
        from pyrekordbox.db6 import Rekordbox6Database
    except ImportError:
        print("ERROR: pyrekordbox not installed.  Run: pip3 install pyrekordbox")
        sys.exit(1)

    # ── load XML paths ────────────────────────────────────────────────────────
    print(f"Reading {XML_PATH} …")
    tree = ET.parse(XML_PATH)
    root = tree.getroot()
    col  = root.find("COLLECTION")

    xml_raw_paths  = {}   # raw Location → rating
    xml_norm_paths = {}   # normalised path → rating

    for t in col.findall("TRACK"):
        loc = t.get("Location", "")
        if not loc:
            continue
        rb_rating = int(t.get("Rating", "0"))
        xml_raw_paths[loc] = rb_rating
        xml_norm_paths[normalise(loc)] = rb_rating

    print(f"  {len(xml_raw_paths):,} tracks in XML")

    # Show sample of raw XML paths
    print("\n── Sample XML Location values (first 5) ──")
    for i, p in enumerate(list(xml_raw_paths.keys())[:5]):
        print(f"  [{i}] {p}")

    # ── load DB paths ─────────────────────────────────────────────────────────
    print(f"\nOpening Rekordbox database …")
    db = Rekordbox6Database(DB_PATH)
    db_paths = {}
    for track in db.get_content():
        fp = track.FolderPath or ""
        db_paths[fp] = track
    db.close()

    print(f"  {len(db_paths):,} tracks in DB")

    # Show sample of raw DB FolderPath values
    print("\n── Sample DB FolderPath values (first 5) ──")
    for i, p in enumerate(list(db_paths.keys())[:5]):
        print(f"  [{i}] {p}")

    # ── exact match (current script behaviour) ────────────────────────────────
    exact_matches = set(xml_norm_paths.keys()) & set(db_paths.keys())
    print(f"\n── Exact normalised matches: {len(exact_matches):,} ──")

    # ── XML paths that don't match any DB path ────────────────────────────────
    xml_only = set(xml_norm_paths.keys()) - set(db_paths.keys())
    print(f"\n── XML paths with NO DB match ({len(xml_only):,} tracks) ──")
    print("   (showing first 10)")
    for p in list(xml_only)[:10]:
        print(f"  XML : {p}")
        # Try to find a close DB path
        basename = Path(p).name
        close = [dp for dp in db_paths if Path(dp).name == basename]
        if close:
            print(f"  DB  : {close[0]}   ← POSSIBLE MATCH")
        else:
            print(f"  DB  : (no DB track with this filename found)")

    # ── DB paths that don't match any XML path ────────────────────────────────
    db_only = set(db_paths.keys()) - set(xml_norm_paths.keys())
    print(f"\n── DB paths with NO XML match ({len(db_only):,} tracks) ──")
    print("   (showing first 10)")
    for p in list(db_only)[:10]:
        print(f"  DB  : {p}")

    # ── summary ───────────────────────────────────────────────────────────────
    print("\n══ SUMMARY ══════════════════════════════════")
    print(f"  XML tracks          : {len(xml_norm_paths):,}")
    print(f"  DB tracks           : {len(db_paths):,}")
    print(f"  Exact matches       : {len(exact_matches):,}")
    print(f"  XML-only (no DB)    : {len(xml_only):,}  ← these tracks got no stars")
    print(f"  DB-only (no XML)    : {len(db_only):,}  ← these were never in our XML")

    # ── check if stripping /localhost fixes more ──────────────────────────────
    # Sometimes XML has file://localhost/path, DB has /path
    # Our normalise() already handles this. Let's double-check raw xml matches:
    raw_xml_stripped = {normalise(k): v for k, v in xml_raw_paths.items()}
    extra_via_norm = set(raw_xml_stripped.keys()) & set(db_paths.keys())
    if len(extra_via_norm) != len(exact_matches):
        print(f"\n  NOTE: After normalise(), matches change: "
              f"{len(exact_matches):,} → {len(extra_via_norm):,}")
    else:
        print(f"\n  Normalisation already applied — no extra matches from stripping localhost.")

if __name__ == "__main__":
    main()
