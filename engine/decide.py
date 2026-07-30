# engine/decide.py
"""Weigh the evidence instead of trusting whichever rule fired first.

An artist to genre map is a habit, not a fact. Artists release across genres,
they get remixed into other genres, and half a modern tracklist is two artists
from two different worlds on one record. A lookup table that returns one answer
per artist will confidently misfile exactly those tracks.

So nothing votes alone here. Every signal scores, and signals about THIS
recording outrank signals about the people who made it:

  genre tag in the file      decisive, it describes this file
  remix or edit credit       very strong, the remixer defines this version
  BPM                        strong, a physical property of this audio
  words in the title         medium
  the artist                 weak, it is a prior and nothing more

Two rules fall straight out of that ordering and fix the two failures the
question is really about:

  A remixer beats the original artist. "Adele, Set Fire To The Rain (Spicy DnB
  Remix)" is drum and bass. Filing it under Adele's usual genre is wrong.

  BPM breaks a collaboration tie. When "A x B" pairs two genres, 174 says drum
  and bass and 128 says house. The file settles it, not a table.

When the evidence genuinely conflicts and nothing breaks the tie, the result
is returned with low confidence and a readable explanation, so it can be shown
to a human rather than silently filed somewhere plausible and wrong.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .genres import CORE_GENRES, get_bpm_range

# Weights. The gap between a remix credit and an artist prior is deliberately
# large: it is the whole point of the module.
W_TAG_GENRE = 100
W_REMIX_CREDIT = 70
W_BPM_EXACT = 40
W_BPM_NEAR = 15
W_TITLE_KEYWORD = 30
W_FOLDER = 20
W_ARTIST_PRIOR = 18
W_MUSICBRAINZ = 35

CONFIDENT = 60          # at or above this, file it without comment
UNCERTAIN = 30          # below this, show the DJ

# "(Someone's Bootleg)", "[Artist Remix]". Brackets are checked first and the
# LAST one wins, because a remix credit is the final thing added to a filename.
# An earlier greedy version read "Adele - Set Fire To The Rain (Spicy DnB
# Remix)" and returned the song title as the remixer.
_BRACKET_CREDIT = re.compile(
    r"[\(\[]\s*([^()\[\]]{2,40}?)\s*"
    r"(?:remix|bootleg|edit|flip|rework|refix|vip|mix)\s*[\)\]]", re.I)
# Fallback for the unbracketed "- Artist Remix" tail.
_DASH_CREDIT = re.compile(
    r"-\s*([^-\(\)\[\]]{2,40}?)\s*"
    r"(?:remix|bootleg|edit|flip|rework|refix)\s*$", re.I)

# "A x B", "A vs B", "A & B", "A feat. B"
_COLLAB = re.compile(r"\s+(?:x|vs\.?|&|feat\.?|ft\.?|with)\s+", re.I)


@dataclass
class Evidence:
    genre: str
    weight: int
    source: str          # shown to the DJ, so write it in plain language


@dataclass
class Decision:
    genre: str
    confidence: int
    reasons: List[str] = field(default_factory=list)
    contested_by: Optional[str] = None

    @property
    def needs_review(self) -> bool:
        return self.confidence < UNCERTAIN or self.contested_by is not None


def _bpm_fits(genre: str, bpm: Optional[float]) -> int:
    """Score how well a BPM sits inside a genre's working range.

    Half and double time are treated as fitting, because a 174 BPM drum and
    bass track is routinely tagged 87 and a 140 dubstep track as 70.
    """
    if not bpm or bpm <= 0:
        return 0
    rng = get_bpm_range(genre)
    if not rng:
        return 0
    lo, hi = rng
    for candidate in (bpm, bpm * 2, bpm / 2):
        if lo <= candidate <= hi:
            return W_BPM_EXACT
        if lo - 6 <= candidate <= hi + 6:
            return W_BPM_NEAR
    return 0


def remix_credit(text: str) -> Optional[str]:
    """The name inside a remix or edit credit, if there is one."""
    matches = _BRACKET_CREDIT.findall(text or "")
    if matches:
        name = matches[-1]
    else:
        m = _DASH_CREDIT.search(text or "")
        if not m:
            return None
        name = m.group(1)
    name = name.strip(" .-_")
    # "Original Mix" and "Extended Mix" credit nobody.
    if name.lower() in {"original", "extended", "radio", "club", "dirty",
                        "clean", "instrumental", "acapella", "short", "intro"}:
        return None
    return name or None


def split_collaborators(text: str) -> List[str]:
    """Every named party on a track, so a collaboration can be seen as one."""
    parts = [p.strip() for p in _COLLAB.split(text or "") if p.strip()]
    return parts if len(parts) > 1 else []


def decide(evidence: List[Evidence], bpm: Optional[float] = None) -> Decision:
    """Score the evidence and return one genre with a confidence and a why."""
    if not evidence:
        return Decision("inbox", 0, ["Nothing in the file said anything"])

    totals: Dict[str, int] = {}
    reasons: Dict[str, List[str]] = {}
    for e in evidence:
        if e.genre not in CORE_GENRES:
            continue
        totals[e.genre] = totals.get(e.genre, 0) + e.weight
        reasons.setdefault(e.genre, []).append(e.source)

    if not totals:
        return Decision("inbox", 0, ["No candidate matched a real genre"])

    # BPM does not propose a genre on its own, it endorses the ones proposed.
    if bpm:
        for genre in list(totals):
            bonus = _bpm_fits(genre, bpm)
            if bonus:
                totals[genre] += bonus
                reasons[genre].append(f"{int(bpm)} BPM fits {CORE_GENRES[genre]['name']}")

    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    winner, score = ranked[0]
    runner_up, runner_score = (ranked[1] if len(ranked) > 1 else (None, 0))

    # A contest is only real when the loser was close. A landslide is not a tie.
    contested = None
    if runner_up and runner_score >= score * 0.75:
        contested = runner_up

    confidence = min(100, score)
    if contested:
        confidence = int(confidence * 0.6)

    why = reasons[winner][:3]
    if contested:
        why.append(f"Also looked like {CORE_GENRES[contested]['name']}, "
                   f"so this one is worth a glance")
    return Decision(winner, confidence, why, contested)


def build_evidence(*, tag_genre_match: Optional[str] = None,
                   title_match: Optional[Tuple[str, str]] = None,
                   remixer_match: Optional[Tuple[str, str]] = None,
                   artist_matches: Optional[List[Tuple[str, str]]] = None,
                   folder_match: Optional[str] = None,
                   musicbrainz: Optional[str] = None) -> List[Evidence]:
    """Assemble scored evidence from whatever each lookup managed to find.

    Every argument is a genre key, or a (genre, name) pair where the name is
    worth showing the DJ. Anything unknown is simply left out.
    """
    ev: List[Evidence] = []
    if tag_genre_match:
        ev.append(Evidence(tag_genre_match, W_TAG_GENRE, "The file's own genre tag"))
    if remixer_match:
        genre, who = remixer_match
        ev.append(Evidence(genre, W_REMIX_CREDIT, f"Remixed by {who}"))
    if title_match:
        genre, word = title_match
        ev.append(Evidence(genre, W_TITLE_KEYWORD, f"Title says '{word}'"))
    if musicbrainz:
        ev.append(Evidence(musicbrainz, W_MUSICBRAINZ, "MusicBrainz tags"))
    if folder_match:
        ev.append(Evidence(folder_match, W_FOLDER, "The folder it was already in"))
    for genre, who in (artist_matches or []):
        # Each collaborator votes separately and weakly, so two artists from
        # two genres produce a visible contest rather than a silent winner.
        ev.append(Evidence(genre, W_ARTIST_PRIOR, f"{who} usually makes this"))
    return ev
