#!/usr/bin/env python3
"""Simulate sort_main_crate classifier against a tracklist file and report folder distribution."""
import sys
import importlib.util
import os
import unicodedata
from collections import defaultdict
from pathlib import Path

def load_classifier(script_path):
    spec = importlib.util.spec_from_file_location("sorter", script_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def main():
    if len(sys.argv) < 3:
        print("Usage: simulate.py <sort_script.py> <tracklist.txt>")
        sys.exit(1)

    script_path = sys.argv[1]
    tracklist_path = sys.argv[2]

    # Resolve relative paths from working dir
    if not os.path.isabs(script_path):
        script_path = os.path.join(os.getcwd(), script_path)
    if not os.path.isabs(tracklist_path):
        tracklist_path = os.path.join(os.getcwd(), tracklist_path)

    mod = load_classifier(script_path)

    with open(tracklist_path, "r", encoding="utf-8") as f:
        tracks = [line.strip() for line in f if line.strip()]

    counts = defaultdict(int)
    inbox_files = []
    INBOX_KEY = None  # Will detect the actual inbox folder name

    for track in tracks:
        try:
            result = mod.classify_file(Path(track))
            folder = result[0] if isinstance(result, tuple) else result
        except Exception as e:
            folder = "INBOX"
        counts[folder] += 1
        if folder.upper() == "INBOX":
            inbox_files.append(track)
            if INBOX_KEY is None:
                INBOX_KEY = folder

    if INBOX_KEY is None:
        INBOX_KEY = "INBOX"

    total = len(tracks)
    print(f"\n{'='*60}")
    print(f"SIMULATION RESULTS: {os.path.basename(script_path)}")
    print(f"Total tracks: {total}")
    print(f"{'='*60}")

    # Sort by count descending
    for folder, count in sorted(counts.items(), key=lambda x: -x[1]):
        pct = count / total * 100
        bar = "█" * int(pct / 2)
        tag = " ← INBOX" if folder.upper() == "INBOX" else ""
        print(f"  {folder:<20} {count:>5}  ({pct:5.1f}%)  {bar}{tag}")

    inbox_count = counts.get(INBOX_KEY, 0)
    inbox_pct = inbox_count / total * 100
    target = total * 0.10
    print(f"\n{'='*60}")
    print(f"INBOX: {inbox_count}/{total} = {inbox_pct:.1f}%  (target: <10% = <{int(target)+1})")
    if inbox_pct < 10:
        print("✅ TARGET MET!")
    else:
        print(f"❌ Still {inbox_count - int(target)} tracks over target")
    print(f"{'='*60}\n")

    # Write inbox list
    inbox_out = "/tmp/inbox_v6.txt"
    with open(inbox_out, "w", encoding="utf-8") as f:
        for fn in sorted(inbox_files):
            f.write(fn + "\n")
    print(f"INBOX filenames written to: {inbox_out}")

if __name__ == "__main__":
    main()
