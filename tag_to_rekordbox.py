#!/usr/bin/env python3
"""
tag_to_rekordbox.py  —  Apply tag_library.py classifications to Rekordbox XML
================================================================================
Reads rekordbox_import.xml (exported from Rekordbox), runs every track through
tag_library.classify_track(), and writes rekordbox_tagged.xml ready for import.

FIELDS UPDATED PER TRACK
  Genre    ← subgenre  (e.g. "Uplifting Trance", "Tech House", "Israeli Pop")
  Rating   ← stars × 51  (Rekordbox scale: 51=★  102=★★  153=★★★  …  255=★★★★★)
  Colour   ← tag_library color constant  (0=none … 8=purple; matches Rekordbox exactly)
  Comments ← "Subgenre | ENERGY"  (e.g. "Tech House | HIGH")

USAGE
  python3 tag_to_rekordbox.py                   # preview — shows change summary, writes nothing
  python3 tag_to_rekordbox.py --write            # write rekordbox_tagged.xml  (metadata only)
  python3 tag_to_rekordbox.py --write --playlists  # also rebuild sub-genre playlists in the XML

REKORDBOX WORKFLOW (after --write)
  1. Rekordbox → File → Import → Import rekordbox Library…
  2. Select:  rekordbox_tagged.xml
  3. ✅  Genre, star rating and colour labels are updated on all 3 770 tracks.
     Cue points, loops and beat-grid data are NOT touched.
"""

import os
import sys
import argparse
import importlib.util
import xml.etree.ElementTree as ET
from urllib.parse import unquote
from pathlib import Path
from collections import defaultdict

# ── Paths ────────────────────────────────────────────────────────────────────
HERE    = Path(__file__).resolve().parent
LIB     = HERE / "tag_library.py"
XML_IN  = HERE / "rekordbox_import.xml"
XML_OUT = HERE / "rekordbox_tagged.xml"

# Mac path prefix as stored in the Rekordbox XML
DJ_MUSIC_PREFIX = "/Users/Lionmit/Music/DJ_MUSIC/"

# ── Energy int → human label ─────────────────────────────────────────────────
ENERGY_LABEL = {1: "LOW", 2: "LOW", 3: "MID", 4: "HIGH", 5: "PEAK"}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_tag_library():
    """Import tag_library.py without running its __main__ block."""
    src = LIB.read_text(encoding="utf-8")
    src = src.split("if __name__")[0]
    g = {}
    exec(src, g)            # pylint: disable=exec-used
    return g


def _parse_location(location):
    """
    Decode a Rekordbox Location URL into (filename, folder_name).
    Returns (filename, None) for tracks outside DJ_MUSIC.
    """
    path = unquote(location.replace("file:///", "/"))
    if DJ_MUSIC_PREFIX not in path:
        return Path(path).name, None
    rel    = path[path.index(DJ_MUSIC_PREFIX) + len(DJ_MUSIC_PREFIX):]
    parts  = rel.split("/")
    folder = parts[0] if len(parts) > 1 else ""
    return parts[-1], folder


def _folder_to_genre(folder, genre_config):
    """Match a DJ_MUSIC folder name to a tag_library genre label."""
    fl = folder.lower()
    for row in genre_config:
        prefix = row[0].lower()
        label  = row[1]
        if fl.startswith(prefix):
            return label
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Main processor
# ─────────────────────────────────────────────────────────────────────────────

def process(write, build_playlists):
    # ── Load classifier ──────────────────────────────────────────────────────
    g              = _load_tag_library()
    classify_track = g["classify_track"]
    GENRE_CONFIG   = g["GENRE_CONFIG"]

    # ── Parse XML ────────────────────────────────────────────────────────────
    tree       = ET.parse(XML_IN)
    root       = tree.getroot()
    collection = root.find("COLLECTION")

    # ── Process every track ──────────────────────────────────────────────────
    stats          = defaultdict(int)
    subgenre_tracks = defaultdict(list)   # "GenreLabel::Subgenre" → [TrackID …]
    changes        = []
    skipped        = 0

    for track in collection.findall("TRACK"):
        location           = track.get("Location", "")
        filename, folder   = _parse_location(location)

        if not folder:
            skipped += 1
            continue

        genre_label = _folder_to_genre(folder, GENRE_CONFIG)
        if not genre_label:
            skipped += 1
            continue

        # Classify
        subgenre, stars, color, energy = classify_track(filename, genre_label)

        rating_new   = stars * 51
        colour_new   = str(color)
        energy_label = ENERGY_LABEL.get(energy, "MID")
        comments_new = f"{subgenre} | {energy_label}"
        genre_new    = subgenre

        # Track changes for reporting
        old_genre  = track.get("Genre",   "")
        old_rating = track.get("Rating",  "0")
        old_colour = track.get("Colour",  "0")
        if genre_new != old_genre or colour_new != old_colour or str(rating_new) != old_rating:
            changes.append({
                "file": filename,
                "old":  f"{old_genre} / ★{int(old_rating)//51} / col{old_colour}",
                "new":  f"{genre_new} / ★{stars} / col{color}",
            })

        # Apply
        if write:
            track.set("Genre",    genre_new)
            track.set("Rating",   str(rating_new))
            track.set("Colour",   colour_new)
            track.set("Comments", comments_new)

        stats[genre_label] += 1
        subgenre_tracks[f"{genre_label}::{subgenre}"].append(track.get("TrackID", ""))

    # ── Rebuild subgenre playlists ────────────────────────────────────────────
    genre_sg = None
    if write and build_playlists:
        playlists = root.find("PLAYLISTS")
        root_node = playlists.find("NODE[@Name='ROOT']")

        # Keep "All Tracks" playlist; remove any previously generated genre nodes
        keep = [n for n in list(root_node) if n.get("Name") == "All Tracks"]
        for child in list(root_node):
            root_node.remove(child)
        for n in keep:
            root_node.append(n)

        # Group by top-level genre → subgenre
        genre_sg = defaultdict(dict)
        for key, ids in subgenre_tracks.items():
            gl, sg = key.split("::", 1)
            genre_sg[gl][sg] = ids

        for gl, sgs in sorted(genre_sg.items()):
            genre_node = ET.SubElement(
                root_node, "NODE", Type="0", Name=gl, Count=str(len(sgs))
            )
            for sg, ids in sorted(sgs.items()):
                pl = ET.SubElement(
                    genre_node, "NODE",
                    Type="1", Name=sg, KeyType="0", Entries=str(len(ids))
                )
                for tid in ids:
                    ET.SubElement(pl, "TRACK", Key=str(tid))

        root_node.set("Count", str(len(list(root_node))))

    # ── Write XML ────────────────────────────────────────────────────────────
    if write:
        tree.write(XML_OUT, encoding="unicode", xml_declaration=True)

    # ── Report ───────────────────────────────────────────────────────────────
    total = sum(stats.values())

    print()
    print("=" * 66)
    mode = "PREVIEW (no files changed)" if not write else "WRITE MODE"
    print(f"  tag_to_rekordbox.py  —  {mode}")
    print("=" * 66)
    print(f"  Tracks processed : {total:>5}")
    print(f"  Tracks changed   : {len(changes):>5}")
    print(f"  Tracks skipped   : {skipped:>5}  (outside DJ_MUSIC/)")
    print()
    print("  Genre breakdown:")
    for gl, cnt in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"    {gl:<25} {cnt:>5}")

    if not write:
        print()
        print("  Sample changes (first 12):")
        for c in changes[:12]:
            name = c["file"][:55]
            print(f"    {name}")
            print(f"      {c['old']}  →  {c['new']}")
        if len(changes) > 12:
            print(f"    … and {len(changes) - 12} more")
        print()
        print("  Run with --write to apply.  Add --playlists to rebuild subgenre playlists.")

    else:
        print()
        print(f"  ✅  Written: {XML_OUT.name}")
        if build_playlists and genre_sg is not None:
            sg_total = sum(len(v) for v in genre_sg.values())
            print(f"  ✅  Sub-genre playlists built: {sg_total}")
        print()
        print("  NEXT STEPS IN REKORDBOX:")
        print("    File → Import → Import rekordbox Library…")
        print(f"    Select:  {XML_OUT.name}")
        print("    ✓  Genre, ★ stars and colour labels updated on all tracks.")
        print("    ✓  Cue points, loops and beat-grid data are unchanged.")

    print("=" * 66)
    print()


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Apply tag_library.py classifications to a Rekordbox XML export"
    )
    ap.add_argument(
        "--write", action="store_true",
        help="Write rekordbox_tagged.xml (default: preview only)"
    )
    ap.add_argument(
        "--playlists", action="store_true",
        help="Rebuild sub-genre playlists in the output XML"
    )
    args = ap.parse_args()
    process(write=args.write, build_playlists=args.playlists)
