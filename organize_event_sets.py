#!/usr/bin/env python3
"""
organize_event_sets.py  —  Classify & add Event Set tracks to rekordbox XML
================================================================================
Scans  DJ_MUSIC/Event Sets/  for audio files, classifies each track using a
comprehensive artist→genre lookup + tag_library.py subgenre engine, then
appends them to rekordbox_tagged.xml with full metadata + per-event playlists.

No files are moved — only the XML is modified (safe for Rekordbox).

USAGE
  python3 organize_event_sets.py              # preview — no changes written
  python3 organize_event_sets.py --write      # append to rekordbox_tagged.xml
  python3 organize_event_sets.py --write --fresh   # rebuild from rekordbox_import.xml

OUTPUT
  rekordbox_tagged.xml updated with:
    ├─ All 1,252 event set tracks tagged (genre, rating, colour, comment)
    └─ PLAYLISTS → Event Sets → [per-event sub-playlists]
"""

import os
import re
import sys
import argparse
import importlib.util
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote, quote
from collections import defaultdict
from datetime import date

# ── Paths ────────────────────────────────────────────────────────────────────
HERE          = Path(__file__).resolve().parent
LIB           = HERE / "tag_library.py"
XML_IMPORT    = HERE / "rekordbox_import.xml"   # source (read-only)
XML_TAGGED    = HERE / "rekordbox_tagged.xml"   # output (append / update)
EVENT_SETS    = HERE / "DJ_MUSIC" / "Event Sets"

MAC_MUSIC     = "/Users/Lionmit/Music/"         # Mac path prefix
AUDIO_EXT     = {".mp3", ".wav", ".flac", ".aiff", ".aif", ".m4a"}
TODAY         = date.today().isoformat()

ENERGY_LABEL  = {1: "LOW", 2: "LOW", 3: "MID", 4: "HIGH", 5: "PEAK"}


# ─────────────────────────────────────────────────────────────────────────────
# ARTIST → GENRE  comprehensive lookup
# Key   : lowercase artist string (or substring)
# Value : genre label that matches a DJ_MUSIC folder prefix
# ─────────────────────────────────────────────────────────────────────────────

# Genre labels must match GENRE_CONFIG rows in tag_library.py
G_ISRAELI  = "Israeli & Hebrew"
G_HIPHOP   = "Hip-Hop & R&B"
G_HOUSE    = "House & Dance"
G_ELEC     = "Electronic"
G_POP      = "Pop & Commercial"
G_ROCK     = "Rock & Alternative"
G_LATIN    = "Latin"
G_CLASSIC  = "Classics & Oldies"
G_WORLD    = "World & Ecstatic"

# fmt: off
ARTIST_GENRE: dict[str, str] = {
    # ── Israeli & Hebrew ───────────────────────────────────────────────────
    "a-wa": G_ISRAELI, "awa": G_ISRAELI,
    "achinoam nini": G_ISRAELI,
    "arik einstein": G_ISRAELI,
    "ester rada": G_ISRAELI,
    "ethnix": G_ISRAELI, "אתניקס": G_ISRAELI,
    "hadag nahash": G_ISRAELI, "הדג נחש": G_ISRAELI,
    "infected mushroom": G_ELEC,    # Israeli psytrance → Electronic
    "noga erez": G_ISRAELI,
    "subliminal": G_HIPHOP,         # Israeli hip-hop
    "סאבלימינל": G_HIPHOP,
    "svika pick": G_ISRAELI,
    "shye ben tzur": G_WORLD,
    "shlomo artzi": G_ISRAELI,
    "dekel": G_ELEC,                # Israeli psytrance
    "dam": G_HIPHOP,                # Palestinian-Israeli rap
    "eyal golan": G_ISRAELI,
    "eden golan": G_ISRAELI,
    "eden ben zaken": G_ISRAELI,
    "shabak samech": G_ISRAELI,
    "idan raichel": G_ISRAELI,
    "static & ben el": G_ISRAELI,
    "static & adi bity": G_ISRAELI,
    "static": G_ISRAELI,
    "svika": G_ISRAELI,
    "אנה זק": G_ISRAELI,
    "anna zak": G_ISRAELI,
    "טונה": G_ISRAELI, "tuna": G_ISRAELI,
    "רביד פלוטניק": G_ISRAELI,
    "נועה קירל": G_ISRAELI,
    "עומר אדם": G_ISRAELI,
    "ציון גולן": G_ISRAELI,
    "zion golan": G_ISRAELI,
    "שרית חדד": G_ISRAELI,
    "sarit hadad": G_ISRAELI,
    "אריאל זילבר": G_ISRAELI,
    "חנן בן ארי": G_ISRAELI,
    "הדג נחש": G_ISRAELI,
    "נס & סטילה": G_ISRAELI,
    "מועדון הקצב": G_ISRAELI,
    "אביהו פנחסוב": G_ISRAELI,
    "ben snof": G_ISRAELI, "בן סנוף": G_ISRAELI,
    "gabi shoshan": G_ISRAELI,
    "guy haliva": G_ISRAELI,
    "riki gal": G_ISRAELI,
    "idan amedi": G_ISRAELI,
    "nasrin kadri": G_WORLD,         # Israeli world music
    "shulman smith": G_WORLD,
    "freqfield": G_ELEC,
    "captain hook": G_ELEC,
    "vini vici": G_ELEC,
    "סטטיק ובן אל": G_ISRAELI,
    "כפיר צפריר": G_ISRAELI,
    "עדן חסון": G_ISRAELI,
    "עידו בי": G_ISRAELI,
    "עידו שוהם": G_ISRAELI,
    "נתי חסיד": G_ISRAELI,
    "נערות ריינס": G_ISRAELI,
    "אין מוצא": G_ISRAELI,
    "חמסה": G_WORLD, "hamsa": G_WORLD,
    "ג׳ירפות": G_ISRAELI,
    "דודו פארוק": G_ISRAELI,
    "שחר טבוך": G_ISRAELI,
    "שחר סאול": G_ISRAELI,
    "אגם בוחבוט": G_ISRAELI,
    "שאזאמאט": G_ISRAELI,
    "קורין": G_ISRAELI,
    "שאזאמאת": G_ISRAELI,
    "סאבלימינל": G_HIPHOP,
    "לידוי": G_ISRAELI,
    "וייב איש": G_ISRAELI,
    "הדג נחש": G_ISRAELI,
    "היי פייב": G_ISRAELI,
    "משינה": G_ROCK,                 # Israeli rock
    "מרסדס בנד": G_ISRAELI,
    "איגי וקסמן": G_ISRAELI,
    "איזי": G_ISRAELI,
    "אמיר ובן": G_ISRAELI,
    "mergui": G_HIPHOP,
    "אביב גפן": G_ISRAELI,

    # ── Hip-Hop & R&B ──────────────────────────────────────────────────────
    "2pac": G_HIPHOP, "tupac": G_HIPHOP,
    "50 cent": G_HIPHOP,
    "akon": G_HIPHOP,
    "alicia keys": G_HIPHOP,
    "ariana grande": G_POP,
    "arrested development": G_HIPHOP,
    "beyoncé": G_HIPHOP, "beyonce": G_HIPHOP,
    "beyonc": G_HIPHOP,
    "blackstreet": G_HIPHOP,
    "blackbear": G_POP,
    "black eyed peas": G_HIPHOP, "the black eyed peas": G_HIPHOP,
    "bts": G_POP,
    "busta rhymes": G_HIPHOP,
    "cardi b": G_HIPHOP,
    "central cee": G_HIPHOP,
    "chaka khan": G_CLASSIC,
    "chaka demus": G_HIPHOP,
    "chelley": G_HIPHOP,
    "chris brown": G_HIPHOP,
    "ciara": G_HIPHOP,
    "ckay": G_HIPHOP,
    "cypress hill": G_HIPHOP,
    "destiny's child": G_HIPHOP, "destiny-'s child": G_HIPHOP, "destiny´s child": G_HIPHOP,
    "dj jazzy jeff": G_HIPHOP,
    "dj khaled": G_HIPHOP,
    "dr. dre": G_HIPHOP, "dr dre": G_HIPHOP,
    "drake": G_HIPHOP,
    "eminem": G_HIPHOP,
    "eric bellinger": G_HIPHOP,
    "estelle": G_HIPHOP,
    "eve": G_HIPHOP,
    "fat joe": G_HIPHOP,
    "fergie": G_HIPHOP,
    "fetty wap": G_HIPHOP,
    "fifth harmony": G_POP,
    "flo rida": G_HIPHOP,
    "french montana": G_HIPHOP,
    "ja rule": G_HIPHOP,
    "jay-z": G_HIPHOP, "jayz": G_HIPHOP, "saigon, jay-z": G_HIPHOP,
    "juelz santana": G_HIPHOP,
    "justin bieber": G_POP,
    "kanye west": G_HIPHOP,
    "kelis": G_HIPHOP,
    "kendrick lamar": G_HIPHOP,
    "khia": G_HIPHOP,
    "khalid": G_POP,
    "kid laroi": G_POP, "the kid laroi": G_POP,
    "lauryn hill": G_HIPHOP,
    "lil wayne": G_HIPHOP,
    "lizzo": G_POP,
    "lmfao": G_HIPHOP,
    "ludacris": G_HIPHOP,
    "missy elliott": G_HIPHOP, "missy elliot": G_HIPHOP,
    "nelly": G_HIPHOP,
    "nelly furtado": G_POP,
    "notorious b.i.g.": G_HIPHOP, "the notorious b.i.g.": G_HIPHOP,
    "notorious": G_HIPHOP,
    "outkast": G_HIPHOP,
    "p!nk": G_POP, "pink": G_POP,
    "panjabi mc": G_HIPHOP,
    "rihanna": G_HIPHOP,
    "salt-n-pepa": G_HIPHOP, "salt n pepa": G_HIPHOP,
    "sean paul": G_HIPHOP,
    "sean kingston": G_HIPHOP,
    "snoop dogg": G_HIPHOP, "snoop lion": G_HIPHOP,
    "swizz beatz": G_HIPHOP,
    "szا": G_HIPHOP, "sza": G_HIPHOP,
    "taio cruz": G_HIPHOP,
    "terror squad": G_HIPHOP,
    "the game": G_HIPHOP,
    "the weeknd": G_HIPHOP,
    "timbaland": G_HIPHOP,
    "tlc": G_HIPHOP,
    "usher": G_HIPHOP,
    "will.i.am": G_HIPHOP,
    "will smith": G_HIPHOP,
    "wiz khalifa": G_HIPHOP,
    "wyclef jean": G_HIPHOP,
    "young jing": G_HIPHOP,
    "yung gravy": G_HIPHOP,
    "zhané": G_HIPHOP, "zhane": G_HIPHOP,
    "steel banglez": G_HIPHOP,
    "travis scott": G_HIPHOP,
    "childish gambino": G_HIPHOP,

    # ── House & Dance ──────────────────────────────────────────────────────
    "avicii": G_HOUSE,
    "axwell": G_HOUSE, "axwell __ ingrosso": G_HOUSE, "axwell ingrosso": G_HOUSE,
    "benny benassi": G_HOUSE,
    "bob sinclar": G_HOUSE,
    "c2c": G_HOUSE,
    "calvin harris": G_HOUSE,
    "carnage": G_HOUSE,
    "cascada": G_HOUSE,
    "clean bandit": G_HOUSE,
    "corona": G_HOUSE,
    "daft punk": G_HOUSE,
    "darude": G_HOUSE,
    "david guetta": G_HOUSE,
    "disclosure": G_HOUSE,
    "eiffel 65": G_HOUSE, "eiffel65": G_HOUSE,
    "elderbrook": G_HOUSE,
    "empire of the sun": G_HOUSE,
    "fatboy slim": G_HOUSE,
    "flight facilities": G_HOUSE,
    "haddaway": G_HOUSE,
    "la roux": G_HOUSE,
    "laidback luke": G_HOUSE,
    "moby": G_HOUSE,
    "throttle": G_HOUSE,
    "tiesto": G_HOUSE, "tiësto": G_HOUSE,
    "vengaboys": G_HOUSE,
    "snap!": G_HOUSE,
    "bomfunk mc's": G_HOUSE, "bomfunk mcs": G_HOUSE,
    "svet & sasha wise": G_HOUSE,
    "toploader": G_HOUSE,
    "dj noiz": G_HOUSE,
    "dj tony": G_HOUSE,
    "dj tao": G_HOUSE,
    "alex gaudino": G_HOUSE,
    "Alexandra stan": G_HOUSE, "alexandra stan": G_HOUSE,

    # ── Electronic ─────────────────────────────────────────────────────────
    "infected mushroom": G_ELEC,
    "captain hook": G_ELEC,
    "vini vici": G_ELEC,
    "dekel": G_ELEC,
    "the chemical brothers": G_ELEC,
    "the prodigy": G_ELEC, "prodigy": G_ELEC,
    "chase & status": G_ELEC,
    "skrillex": G_ELEC,
    "flume": G_ELEC,
    "four tet": G_ELEC,
    "bonobo": G_ELEC,
    "bicep": G_ELEC,
    "floating points": G_ELEC,
    "monolink": G_ELEC,
    "the blaze": G_ELEC,
    "odesza": G_ELEC,
    "big wild": G_ELEC,
    "san holo": G_ELEC,
    "grimes": G_ELEC,
    "gorillaz": G_ELEC,
    "rüfüs du sol": G_ELEC, "rufus du sol": G_ELEC,
    "slipknot": G_ROCK,             # metal → Rock
    "blackmill": G_ELEC,
    "depeche mode": G_ELEC,
    "empire of the sun": G_HOUSE,
    "empire": G_HOUSE,
    "two door cinema club": G_ROCK,
    "glass animals": G_ELEC,
    "alt-j": G_ELEC, "alt-j ∆": G_ELEC,
    "rezz": G_ELEC,
    "moderat": G_ELEC,
    "christian crisóstomo": G_ELEC, "christian crisostomo": G_ELEC,
    "freqfield": G_ELEC,
    "bro safari": G_ELEC,
    "wuki": G_ELEC,
    "hamdi": G_ELEC,
    "thyponyx": G_ELEC,
    "frontliner": G_ELEC,
    "desert dwellers": G_WORLD,
    "prana": G_ELEC,
    "adam ten & mita gami": G_ELEC,
    "acid arab": G_WORLD,
    "4 strings": G_HOUSE,
    "hyalyte": G_ELEC,

    # ── Pop & Commercial ───────────────────────────────────────────────────
    "abba": G_CLASSIC,              # ABBA → Classics (era fits)
    "adele": G_POP,
    "alanis morissette": G_POP,
    "anna kendrick": G_POP,
    "arctic monkeys": G_ROCK,
    "avril lavigne": G_POP,
    "b*witched": G_POP,
    "backstreet boys": G_POP,
    "billie eilish": G_POP,
    "blackpink": G_POP,
    "britney spears": G_POP,
    "bruno mars": G_POP,
    "charlie xcx": G_POP, "charli xcx": G_POP,
    "coldplay": G_ROCK,
    "counting crows": G_ROCK,
    "demi lovato": G_POP,
    "des'ree": G_POP, "desree": G_POP,
    "dua lipa": G_POP,
    "ed sheeran": G_POP,
    "ellie goulding": G_POP,
    "emmy meli": G_POP,
    "five": G_POP,
    "florence + the machine": G_POP, "florence and the machine": G_POP,
    "florence + the machine": G_POP,
    "gavin degraw": G_POP,
    "geri halliwell": G_POP,
    "gloria gaynor": G_CLASSIC,
    "gorillaz": G_ELEC,
    "gwen stefani": G_POP,
    "hanson": G_POP,
    "justin timberlake": G_POP,
    "katy perry": G_POP,
    "lil' kim": G_HIPHOP,
    "limp bizkit": G_ROCK,
    "lorde": G_POP,
    "madonna": G_POP,
    "maroon 5": G_POP,
    "miley cyrus": G_POP,
    "natasha bedingfield": G_POP,
    "natalie imbruglia": G_POP,
    "no doubt": G_POP,
    "nsync": G_POP, "*nsync": G_POP, "_nsync": G_POP,
    "panic! at the disco": G_POP, "panic at the disco": G_POP,
    "pussycat dolls": G_POP,
    "robbie williams": G_POP,
    "s club 7": G_POP,
    "sam smith": G_POP,
    "shakira": G_LATIN,
    "shania twain": G_POP,
    "sia": G_POP,
    "sigrid": G_POP,
    "smash mouth": G_POP,
    "spice girls": G_POP,
    "spice": G_POP,
    "sugababes": G_POP,
    "taylor swift": G_POP,
    "the chainsmokers": G_POP,
    "the kid laroi": G_POP,
    "the neighbourhood": G_POP, "the neighborhood": G_POP,
    "tones and i": G_POP,
    "twenty one pilots": G_POP,
    "vanilla ice": G_POP,
    "westlife": G_POP,
    "willow": G_POP,
    "zootrax": G_POP,

    # ── Rock & Alternative ─────────────────────────────────────────────────
    "ac/dc": G_ROCK, "ac_dc": G_ROCK,
    "aerosmith": G_ROCK,
    "alice cooper": G_ROCK,
    "blink-182": G_ROCK, "blink182": G_ROCK,
    "blur": G_ROCK,
    "counting crows": G_ROCK,
    "dave matthews band": G_ROCK,
    "david bowie": G_CLASSIC,
    "dire straits": G_CLASSIC,
    "dropkick murphys": G_ROCK,
    "foo fighters": G_ROCK,
    "franz ferdinand": G_ROCK,
    "garbage": G_ROCK,
    "green day": G_ROCK,
    "linkin park": G_ROCK,
    "limp bizkit": G_ROCK,
    "nirvana": G_ROCK,
    "no doubt": G_ROCK,
    "the offspring": G_ROCK,
    "poison": G_ROCK,
    "rage against the machine": G_ROCK,
    "red hot chili peppers": G_ROCK,
    "sheryl crow": G_ROCK,
    "slipknot": G_ROCK,
    "system of a down": G_ROCK, "system of a down": G_ROCK,
    "the beatles": G_CLASSIC,
    "the darkness": G_ROCK,
    "two door cinema club": G_ROCK,
    "the chainsmokers": G_HOUSE,

    # ── Latin ──────────────────────────────────────────────────────────────
    "santana": G_LATIN,
    "shakira": G_LATIN,
    "ricky martin": G_LATIN,
    "pitbull": G_LATIN,
    "wisin & carlos vives": G_LATIN, "wisin": G_LATIN,
    "gente de zona": G_LATIN,
    "damariscrs": G_LATIN,
    "dj tao & ponte perro": G_LATIN,
    "fanfare ciocarlia": G_WORLD,
    "el chima": G_LATIN,
    "ernst bianchi": G_LATIN,
    "santa esmeralda": G_LATIN,

    # ── Classics & Oldies ──────────────────────────────────────────────────
    "abba": G_CLASSIC,
    "aretha franklin": G_CLASSIC,
    "chaka khan": G_CLASSIC,
    "david bowie": G_CLASSIC,
    "diana ross": G_CLASSIC,
    "dire straits": G_CLASSIC,
    "earth, wind & fire": G_CLASSIC, "earth wind and fire": G_CLASSIC,
    "ella fitzgerald": G_CLASSIC,
    "elvis presley": G_CLASSIC,
    "etta james": G_CLASSIC,
    "gloria gaynor": G_CLASSIC,
    "michael jackson": G_CLASSIC,
    "queen": G_CLASSIC,
    "sister sledge": G_CLASSIC,
    "stevie wonder": G_CLASSIC,
    "the beatles": G_CLASSIC,
    "the jackson 5": G_CLASSIC,
    "the marvelettes": G_CLASSIC,
    "the supremes": G_CLASSIC,
    "tom jones": G_CLASSIC,
    "war": G_CLASSIC,
    "yazoo": G_CLASSIC,
    "chaka demus & pliers": G_CLASSIC,

    # ── World & Ecstatic ───────────────────────────────────────────────────
    "om shalom yoga": G_WORLD,
    "beautiful chorus": G_WORLD,
    "rising appalachia": G_WORLD,
    "ayla nereo": G_WORLD,
    "mamuse": G_WORLD,
    "desiree dawson": G_WORLD, "desirée dawson": G_WORLD,
    "east forest": G_WORLD,
    "east forest & ram dass": G_WORLD,
    "sol rising": G_WORLD,
    "trevor hall": G_WORLD,
    "thievery corporation": G_WORLD,
    "el búho": G_WORLD, "el buho": G_WORLD,
    "thornato": G_WORLD,
    "amadou & mariam": G_WORLD,
    "flavien berger": G_WORLD,        # French electro-folk
    "flavien berger & bonnie banane": G_WORLD,
    "facesoul": G_WORLD,
    "batya levine": G_WORLD,
    "desert dwellers": G_WORLD,
    "temple step project": G_WORLD,
    "wildlight": G_WORLD,
    "wildlight & ayla nereo": G_WORLD,
    "birds of chicago": G_WORLD,
    "wailin' jennys": G_WORLD, "wailin jennys": G_WORLD,
    "salt cathedral": G_WORLD,
    "semblanzas del río guapi": G_WORLD, "semblanzas del rio guapi": G_WORLD,
    "tribal seeds": G_WORLD,
    "soja": G_WORLD,
    "soja (feat. collie buddz)": G_WORLD,
    "tribal": G_WORLD,
    "shye ben tzur": G_WORLD,
    "nasrin kadri": G_WORLD,
    "ibrahim maalouf": G_WORLD,
    "acid arab": G_WORLD,
    "blinky bill & nature": G_WORLD, "blinky bill": G_WORLD,
    "bongeziwe mabandla": G_WORLD,
    "fetsum": G_WORLD,
    "govinda": G_WORLD,
    "govinda ": G_WORLD,
    "ya tseen": G_WORLD,
    "awa": G_WORLD,                 # (African Awa ≠ Israeli A-WA)
    "soulely": G_WORLD,
    "troy ramey": G_WORLD,
    "aisha badru": G_WORLD,
    "anees": G_WORLD,
    "christian crisóstomo": G_WORLD,
    "ashh blackwood": G_WORLD,
    "ashh": G_WORLD,
    "desiree dawson": G_WORLD,
    "frank hamilton": G_WORLD,
    "doli & penn": G_WORLD,
    "hana ni": G_WORLD,
    "hana": G_WORLD,
    "ela minus": G_WORLD,
    "rhye": G_WORLD,
    "the advocate": G_WORLD,
    "ahmed spins": G_WORLD,
    "tough art": G_WORLD,
    "colourless colour": G_WORLD,
    "good day": G_WORLD,
    "geminelle": G_WORLD,
    "ella vos": G_WORLD,
    "cory henry": G_WORLD,
    "sara bareilles": G_POP,
    "savanna": G_WORLD,
    "strangers": G_WORLD,
    "stanwood": G_WORLD, "stan wood": G_WORLD,
    "council": G_WORLD,
    "desiree dawson": G_WORLD,
    "judith ravitz": G_WORLD,
    "cracked open": G_WORLD,
    "don day": G_WORLD,
    "will hearn": G_ELEC,
    "slo": G_WORLD,
    "yeahman": G_WORLD,
    "toni jones": G_WORLD,
    "scala & kolacny brothers": G_WORLD,
    "prana": G_ELEC,
    "colourless colour": G_WORLD,
    "shekel": G_WORLD,
    "shekel": G_WORLD,
    "dao feat. adam friedman": G_WORLD, "dao": G_WORLD,
    "arutz hakibud": G_WORLD,
    "alickiko": G_WORLD,
    "gabi shoshan": G_WORLD,
    "Mergui": G_WORLD, "mergui": G_WORLD,
    "zahar": G_WORLD,
    "fruity loops": G_ELEC,
    "ahmad": G_WORLD,
    "om shalom": G_WORLD,
    "om shalom yoga": G_WORLD,
    "binaural": G_WORLD,
    "binaural meditation music mix": G_WORLD,
    "svet": G_HOUSE,
    "sand": G_WORLD,
    "rising": G_WORLD,
    "desiree": G_WORLD,
    "batya": G_WORLD,
    "east": G_WORLD,
    "sol": G_WORLD,
    "hana": G_WORLD,
    "chill out relax": G_WORLD,
    "meditation music": G_WORLD,
    "casino versus japan": G_ELEC,
    "tigerlily": G_HOUSE,
    "barda & populous": G_WORLD,
    "yunghblud": G_ROCK,
    "emmy": G_POP,
    "sara": G_POP,
    "al jawala": G_WORLD, "äl jawala": G_WORLD,
    "al jawala": G_WORLD,
}
# fmt: on

# ── Folder-level genre hints (for tracks that don't match artist lookup) ──────
FOLDER_GENRE_HINTS: dict[str, str] = {
    "קשובות": G_WORLD,          # ecstatic/ceremonial set → World
    "ecstatic set lionel #1": G_WORLD,
    "ecstatic set lionel": G_WORLD,
    "aner & maya": G_POP,       # wedding set → mixed Pop
    "90s - 00's for mmc": G_POP,   # 90s/00s hits → Pop
    "sleazy": G_HIPHOP,         # sleazy → Hip-Hop
    "יומולדת במשביר": G_POP,   # birthday party
    "רווקים ורווקות": G_ISRAELI, # Israeli dating show style
    "פורים 2023- מיינסטרים af": G_POP,
    "jean marc's 50th": G_POP,
    "diskin 50": G_POP,
    "micotown2022": G_ELEC,
    "midburn masada": G_ELEC,
    "shani's 30th": G_POP,
}

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _load_tag_library():
    src = LIB.read_text(encoding="utf-8")
    src = src.split("if __name__")[0]
    g = {}
    exec(src, g)
    return g


def _audio_kind(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".mp3": "MP3 File", ".wav": "WAV File", ".flac": "FLAC File",
        ".aiff": "AIFF File", ".aif": "AIFF File", ".m4a": "M4A File",
    }.get(ext, "Audio File")


def _to_location(path: Path) -> str:
    """Convert an absolute Mac path to a Rekordbox Location URL."""
    rel = str(path).replace("/sessions/busy-funny-noether/mnt/Music/", MAC_MUSIC)
    # URL-encode special characters but keep slashes
    parts = rel.split("/")
    encoded = "/".join(quote(p, safe="") for p in parts)
    return "file:///" + encoded.lstrip("/")


def _extract_artist_title(filename: str):
    """
    Return (artist, title) from 'Artist - Title.ext' pattern.
    Falls back to ("", filename_stem) if no ' - ' separator.
    """
    stem = Path(filename).stem
    if " - " in stem:
        parts = stem.split(" - ", 1)
        return parts[0].strip(), parts[1].strip()
    return "", stem.strip()


def _lookup_genre(artist: str, folder_name: str) -> str:
    """
    Look up genre for an artist string.
    Tries exact match then substring match in ARTIST_GENRE,
    falls back to folder hint, then defaults to INBOX.
    """
    al = artist.lower().strip()

    # Exact match
    if al in ARTIST_GENRE:
        return ARTIST_GENRE[al]

    # Substring match (handles feat., vs., mashup variants)
    for key, genre in ARTIST_GENRE.items():
        if key and key in al:
            return genre

    # Reverse: does artist name contain a known key?
    for key, genre in ARTIST_GENRE.items():
        if key and al and len(key) > 4 and key in al:
            return genre

    # Folder hint
    fl = folder_name.lower().strip()
    for hint_key, genre in FOLDER_GENRE_HINTS.items():
        if hint_key.lower() in fl or fl in hint_key.lower():
            return genre

    return "INBOX"


def _max_track_id(collection) -> int:
    ids = [int(t.get("TrackID", 0)) for t in collection.findall("TRACK")]
    return max(ids) if ids else 0


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def process(write: bool):
    # ── Load tagger ──────────────────────────────────────────────────────────
    g              = _load_tag_library()
    classify_track = g["classify_track"]

    # ── Load XML (use tagged if it exists, otherwise import) ─────────────────
    xml_source = XML_TAGGED if XML_TAGGED.exists() else XML_IMPORT
    print(f"\n  Source XML : {xml_source.name}")
    tree       = ET.parse(xml_source)
    root       = tree.getroot()
    collection = root.find("COLLECTION")
    playlists  = root.find("PLAYLISTS")

    # ── Find already-known locations (avoid duplicates) ──────────────────────
    known_locations = set()
    for t in collection.findall("TRACK"):
        loc = t.get("Location", "")
        known_locations.add(loc)

    next_id    = _max_track_id(collection) + 1

    # ── Scan Event Sets ───────────────────────────────────────────────────────
    # event_data: folder_name → list of (genre, track_element)
    event_data: dict[str, list] = {}
    stats      = defaultdict(int)
    unmatched  = []
    skipped    = 0
    added      = 0

    for event_folder in sorted(EVENT_SETS.iterdir()):
        if not event_folder.is_dir():
            continue
        folder_name = event_folder.name
        event_tracks = []

        audio_files = sorted(
            f for f in event_folder.rglob("*")
            if f.is_file() and f.suffix.lower() in AUDIO_EXT
        )

        for fpath in audio_files:
            location = _to_location(fpath)

            if location in known_locations:
                skipped += 1
                continue

            artist, title = _extract_artist_title(fpath.name)
            genre_label   = _lookup_genre(artist, folder_name)
            subgenre, stars, color, energy = classify_track(fpath.name, genre_label)

            if genre_label == "INBOX":
                unmatched.append(f"{folder_name}/{fpath.name}")

            kind         = _audio_kind(fpath)
            rating       = stars * 51
            energy_lbl   = ENERGY_LABEL.get(energy, "MID")
            # Use specific subgenre if known; fall back to broad genre label
            genre_display = subgenre if subgenre and subgenre != "Unknown" else genre_label
            comment      = f"{genre_display} | {energy_lbl}"

            track_elem = ET.Element("TRACK",
                TrackID    = str(next_id),
                Name       = title,
                Artist     = artist,
                Genre      = genre_display,
                Album      = f"Event: {folder_name}",
                Grouping   = "Event Sets",
                Kind       = kind,
                TotalTime  = "0",
                DiscNumber = "0",
                TrackNumber= "0",
                Year       = "",
                Bpm        = "0.00",
                DateAdded  = TODAY,
                BitRate    = "0",
                SampleRate = "44100",
                Comments   = comment,
                Rating     = str(rating),
                Location   = location,
                Remixer    = "",
                Tonality   = "",
                Label      = "",
                Mix        = "",
                Colour     = str(color),
            )

            known_locations.add(location)
            event_tracks.append((str(next_id), genre_label, track_elem))
            next_id += 1
            added   += 1
            stats[genre_label] += 1

        if event_tracks:
            event_data[folder_name] = event_tracks

    # ── Apply to XML ──────────────────────────────────────────────────────────
    if write:
        # Append new TRACK elements to COLLECTION
        for folder_name, tracks in event_data.items():
            for (tid, gl, elem) in tracks:
                collection.append(elem)

        # Update COLLECTION Count attribute
        total_tracks = len(collection.findall("TRACK"))
        collection.set("Entries", str(total_tracks))

        # Build / update "Event Sets" playlist folder
        root_node = playlists.find("NODE[@Name='ROOT']")
        if root_node is None:
            root_node = ET.SubElement(playlists, "NODE",
                                      Type="0", Name="ROOT", Count="0")

        # Remove any existing "Event Sets" folder to rebuild cleanly
        for existing in list(root_node):
            if existing.get("Name") == "Event Sets":
                root_node.remove(existing)

        event_sets_node = ET.SubElement(root_node, "NODE",
                                        Type="0", Name="Event Sets",
                                        Count=str(len(event_data)))
        for folder_name, tracks in sorted(event_data.items()):
            pl = ET.SubElement(event_sets_node, "NODE",
                               Type="1", Name=folder_name,
                               KeyType="0", Entries=str(len(tracks)))
            for (tid, gl, _elem) in tracks:
                ET.SubElement(pl, "TRACK", Key=tid)

        root_node.set("Count", str(len(list(root_node))))

        tree.write(XML_TAGGED, encoding="unicode", xml_declaration=True)

    # ── Report ────────────────────────────────────────────────────────────────
    print()
    print("=" * 70)
    mode = "PREVIEW (no files changed)" if not write else "WRITE MODE ✅"
    print(f"  organize_event_sets.py  —  {mode}")
    print("=" * 70)
    print(f"  Event folders   : {len(event_data)}")
    print(f"  Tracks added    : {added}")
    print(f"  Tracks skipped  : {skipped}  (already in XML)")
    print()
    print("  Genre distribution:")
    for gl, cnt in sorted(stats.items(), key=lambda x: -x[1]):
        bar = "█" * (cnt // 10)
        print(f"    {gl:<28} {cnt:>4}  {bar}")

    if unmatched:
        print()
        print(f"  ⚠️  Unmatched → INBOX ({len(unmatched)} tracks):")
        for u in unmatched[:20]:
            print(f"    {u}")
        if len(unmatched) > 20:
            print(f"    … and {len(unmatched) - 20} more")

    if write:
        print()
        print(f"  Written → {XML_TAGGED.name}")
        print(f"  Total tracks in XML now: {total_tracks}")
        print()
        print("  NEXT STEPS IN REKORDBOX:")
        print("    Preferences → Advanced → rekordbox xml → set file path")
        print("    OR  File → Import → Import rekordbox Library…")
        print(f"    Select: {XML_TAGGED.name}")
    else:
        print()
        print("  Run with --write to apply changes.")

    print("=" * 70)
    print()


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Classify & add Event Set tracks to rekordbox_tagged.xml"
    )
    ap.add_argument(
        "--write", action="store_true",
        help="Write to rekordbox_tagged.xml (default: preview only)"
    )
    args = ap.parse_args()
    process(write=args.write)
