# engine/dedupe.py
"""Keep sample libraries out of the crates, and keep one copy of each track.

Three jobs, all of them things a DJ notices immediately and a sorter usually
gets wrong:

1. Sample libraries are not music. A Native Instruments or Splice install can
   hold tens of thousands of one-shots and loops whose filenames look exactly
   like tracks. Sorting them into genre folders buries the real library.

2. The same file often exists in several folders at once, because it was
   downloaded twice or copied to a USB and back. Byte-identical copies should
   collapse to one.

3. The same track often exists at different quality: a 128 kbps YouTube rip
   and a 320 kbps purchase, or an MP3 and a WAV. Those are not byte-identical
   so a hash will not catch them. Keep the best one and set the rest aside.
"""
from __future__ import annotations

import hashlib
import re
from functools import lru_cache
import unicodedata
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Optional

# ---------------------------------------------------------------------------
# 1. Sample libraries and production content
# ---------------------------------------------------------------------------

# Folder names that mean "this whole tree is production content, not a crate".
# Matched against any folder in the path, case-insensitively.
SAMPLE_DIR_MARKERS = {
    "native instruments", "komplete", "kontakt", "maschine", "battery 4",
    "reaktor", "massive", "absynth", "guitar rig",
    "splice", "splice sounds", "loopmasters", "loopcloud", "sample magic",
    "ghosthack", "cymatics", "black octopus", "producerloops",
    "arturia", "serum presets", "sylenth", "spire", "omnisphere",
    "ableton", "user library", "live recordings", "ableton project",
    "logic", "logic pro", "garageband", "audio music apps", "flstudio",
    "fl studio", "reason", "cubase", "studio one", "bitwig", "pro tools",
    "sample pack", "sample packs", "samples", "one shots", "one-shots",
    "oneshots", "drum kits", "drumkits", "loops", "midi", "presets",
    "stems", "acapellas out", "project files", "sound library",
    "apple loops", "jam packs", "impulse responses",
}

# Filename fragments that mean the file itself is production content.
# These matter even when the file already sits in a genre folder: a previous
# sort can bury one-shots among real tracks, and then they look like music.
SAMPLE_FILE_MARKERS = (
    "one shot", "oneshot", "one-shot", "loop_", "_loop", " loop ",
    "bpm_kick", "bpm_snare", "_dry_", "_wet_", "sample pack",
    "vocal chop", "riser ", "downlifter", "uplifter", "impact ",
    "foley ", "texture ", "atmos ", "sub drop", "white noise",
    "preset", ".nki", ".nkm", ".fxp", ".als", ".flp", ".logicx",
    # Unambiguous one-shot naming. These strings do not occur in song titles.
    "closedhh", "openhh", "pedalhh", "clhat", "ophat", "pedhat",
    "rimshot", "hitom", "midtom", "lotom", "lowtom",
)

# Native Instruments and similar product names. Real songs do contain words
# like "Form" and "Rounds" ("Love Surrounds You" was wrongly excluded by an
# earlier version), so these only count as a signal alongside a second one.
_INSTRUMENT_NAMES = ("absynth", "kontakt", "maschine", "reaktor", "monark",
                     "polyplex", "molekular", "replika", "battery", "massive",
                     "prism", "rounds", "razor", "kinetic", "form")

# Percussion words are extremely common in song titles: Tom Petty, Ride It,
# Crash Into Me, Clap Your Hands. Never enough on their own.
_PERCUSSION_WORDS = ("kick", "snare", "hat", "clap", "tom", "rim", "perc",
                     "crash", "ride", "cymbal", "shaker", "cowbell", "clave",
                     "conga", "bongo", "stab", "tamb")

_DRUM_MACHINES = ("707", "727", "808", "909", "606", "linndrum", "dmx")

# One-shot exports almost always end in a bare index: "Kick 707 1.flac",
# "Snap Absynth 2.flac", "ClosedHH Glowstix 2.flac".
_INDEX_SUFFIX = re.compile(r"[ _-]\d{1,3}$")

@lru_cache(maxsize=8)
def _WORD_RE(words: tuple):
    """Whole-word matcher for a tuple of terms."""
    return re.compile(r"(?<![a-z0-9])(?:" + "|".join(re.escape(w) for w in words) + r")(?![a-z0-9])")

# Very short files are almost never playable tracks.
MIN_TRACK_SECONDS = 45
MIN_TRACK_BYTES = 500_000


def is_sample_library(path: Path, duration_seconds: Optional[float] = None,
                      size_bytes: Optional[int] = None) -> Optional[str]:
    """Return a reason string if this file is production content, else None."""
    parts = [p.lower() for p in path.parts[:-1]]
    for folder in parts:
        cleaned = folder.strip()
        if cleaned in SAMPLE_DIR_MARKERS:
            return f"inside a sample library folder: {folder}"
        for marker in SAMPLE_DIR_MARKERS:
            if marker in cleaned and len(marker) > 6:
                return f"inside a sample library folder: {folder}"

    name = path.name.lower()
    for marker in SAMPLE_FILE_MARKERS:
        if marker in name:
            return f"sample or preset filename: '{marker.strip()}'"

    # Weak signals. Any one of these appears in ordinary song titles, so a
    # file is only treated as production content when at least two agree.
    stem = path.stem.lower()
    weak = []
    # Whole-word only. Substring matching put "Tom Petty" and "Rock Bottom"
    # in the sample pile because "That" contains "hat" and "Bottom" contains
    # "tom". A percussion word only counts when it stands alone.
    if _WORD_RE(_PERCUSSION_WORDS).search(name):
        weak.append("percussion word")
    if _WORD_RE(_INSTRUMENT_NAMES).search(name):
        weak.append("instrument name")
    if _WORD_RE(_DRUM_MACHINES).search(name):
        weak.append("drum machine")
    if _INDEX_SUFFIX.search(stem):
        weak.append("one-shot index")
    if size_bytes is not None and size_bytes < 1_500_000:
        weak.append("very small file")
    if duration_seconds is not None and 0 < duration_seconds < 20:
        weak.append("under 20 seconds")

    if len(weak) >= 2:
        return "sample or one-shot (" + ", ".join(weak[:3]) + ")"

    # Hard limits. Nothing this small or this short is a playable track.
    if size_bytes is not None and size_bytes < MIN_TRACK_BYTES:
        return "file too small to be a track"
    if duration_seconds is not None and 0 < duration_seconds < MIN_TRACK_SECONDS:
        return f"only {int(duration_seconds)} seconds long"
    return None


# ---------------------------------------------------------------------------
# 2 and 3. Duplicates, byte-identical and same-track-different-quality
# ---------------------------------------------------------------------------

# Noise that appears in downloaded filenames and says nothing about the track.
_NOISE = re.compile(
    r"\b("
    r"free\s*(dl|download)|official(\s+(music\s+)?video|\s+audio)?|lyrics?(\s+video)?|"
    r"hd|hq|4k|full\s+hd|audio|video|visualizer|explicit|clean|dirty|"
    r"\d{2,4}\s*kbps|\d{2,3}\s*k\b|remaster(ed)?(\s+\d{4})?|"
    r"copy|copia|duplicate|dup\d*|\(\d+\)|"
    r"youtube|ytmp3|ezmp3|y2mate|savefrom|mp3juices|"
    r"extended(\s+mix)?|radio\s+edit|original\s+mix"
    r")\b", re.I)

_LOSSLESS = {".wav", ".aiff", ".aif", ".flac", ".alac"}

# Quality ranking for containers when no bitrate is known.
_FORMAT_RANK = {".wav": 5, ".aiff": 5, ".aif": 5, ".flac": 4,
                ".m4a": 2, ".mp3": 2, ".ogg": 1, ".wma": 0}


def track_key(filename: str) -> str:
    """Normalise a filename down to the track it represents.

    Strips extension, bracketed junk, download-site noise and punctuation, so
    that "Song (Official Video) [320kbps].mp3" and "Song_1.wav" collapse
    together. Hebrew and other non-Latin letters are preserved.
    """
    stem = Path(filename).stem
    stem = unicodedata.normalize("NFKC", stem).lower()
    stem = re.sub(r"^\d{9,}[_\-\s]+", "", stem)        # Main Crate timestamp prefixes
    stem = re.sub(r"\[.*?\]|\(.*?\)|\{.*?\}", " ", stem)
    stem = _NOISE.sub(" ", stem)
    stem = re.sub(r"[^\w֐-׿]+", "", stem, flags=re.UNICODE)
    return stem


def quality_score(path: Path, bitrate: Optional[int] = None,
                  size_bytes: Optional[int] = None) -> tuple:
    """Higher sorts better. Lossless wins, then bitrate, then file size."""
    ext = path.suffix.lower()
    return (
        1 if ext in _LOSSLESS else 0,
        _FORMAT_RANK.get(ext, 1),
        bitrate or 0,
        size_bytes or 0,
    )


def _read_bitrate(path: Path) -> Optional[int]:
    """Real bitrate from the file, so "keep the better quality" means it.

    Only called for tracks that already have a same-name rival, so a library
    of thousands is never fully tag-read just to find a handful of duplicates.
    """
    try:
        from tinytag import TinyTag
        tag = TinyTag.get(str(path))
        return int(tag.bitrate) if tag.bitrate else None
    except Exception:
        return None


def file_fingerprint(path: Path, chunk: int = 262_144) -> str:
    """Cheap content fingerprint: size plus the head and tail of the file.

    Full hashing a 70 GB library is minutes of disk churn for no extra
    certainty. Two audio files that share a size, a first 256 KB and a last
    256 KB are the same file in every practical case.
    """
    size = path.stat().st_size
    h = hashlib.blake2b(digest_size=16)
    h.update(str(size).encode())
    with path.open("rb") as f:
        h.update(f.read(chunk))
        if size > chunk * 2:
            f.seek(-chunk, 2)
            h.update(f.read(chunk))
    return h.hexdigest()


class DuplicateGroup(NamedTuple):
    keep: Path
    drop: List[Path]
    reason: str          # "identical" or "quality"
    detail: str


def find_duplicates(files: Iterable[Path],
                    bitrates: Optional[Dict[Path, int]] = None
                    ) -> List[DuplicateGroup]:
    """Group duplicates and pick which copy to keep.

    Two passes. First byte-identical copies, grouped by size then fingerprint,
    so only same-size candidates are ever opened. Then same-track-different-
    quality, grouped by normalised name, keeping the best copy.
    """
    bitrates = bitrates or {}
    files = [f for f in files if f.exists()]
    groups: List[DuplicateGroup] = []
    resolved: set = set()

    by_size: Dict[int, List[Path]] = {}
    for f in files:
        try:
            by_size.setdefault(f.stat().st_size, []).append(f)
        except OSError:
            continue

    # Pass 1: identical content
    for size, candidates in by_size.items():
        if len(candidates) < 2:
            continue
        by_print: Dict[str, List[Path]] = {}
        for f in candidates:
            try:
                by_print.setdefault(file_fingerprint(f), []).append(f)
            except OSError:
                continue
        for prints in by_print.values():
            if len(prints) < 2:
                continue
            prints.sort(key=lambda p: (len(str(p)), str(p)))
            keep, drop = prints[0], prints[1:]
            groups.append(DuplicateGroup(
                keep, drop, "identical",
                f"{len(prints)} byte-identical copies, {size/1_048_576:.1f} MB each"))
            resolved.update(drop)

    # Pass 2: same track, different quality
    by_track: Dict[str, List[Path]] = {}
    for f in files:
        if f in resolved:
            continue
        key = track_key(f.name)
        if len(key) >= 6:                     # too-short keys collide wildly
            by_track.setdefault(key, []).append(f)

    for key, variants in by_track.items():
        if len(variants) < 2:
            continue
        scored = []
        for v in variants:
            try:
                br = bitrates.get(v)
                if br is None:
                    br = _read_bitrate(v)
                scored.append((quality_score(v, br, v.stat().st_size), v))
            except OSError:
                continue
        if len(scored) < 2:
            continue
        scored.sort(key=lambda t: t[0], reverse=True)
        keep = scored[0][1]
        drop = [v for _, v in scored[1:]]
        best, worst = scored[0][0], scored[-1][0]
        detail = f"{len(scored)} versions, keeping {keep.suffix.lstrip('.').upper()}"
        if best[2] and worst[2] and best[2] != worst[2]:
            detail += f" at {best[2]} kbps over {worst[2]} kbps"
        groups.append(DuplicateGroup(keep, drop, "quality", detail))

    return groups


def summarise(groups: Iterable[DuplicateGroup]) -> Dict[str, int]:
    """Counts for the UI: how many files can go, and how much space that frees."""
    identical = quality = freed = 0
    for g in groups:
        for d in g.drop:
            try:
                freed += d.stat().st_size
            except OSError:
                pass
        if g.reason == "identical":
            identical += len(g.drop)
        else:
            quality += len(g.drop)
    return {"identical": identical, "quality": quality,
            "total": identical + quality, "bytes_freed": freed}
