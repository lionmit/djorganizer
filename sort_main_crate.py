#!/usr/bin/env python3
"""
sort_main_crate.py — Auto-sort script for Lionel Mitelpunkt's DJ library
==========================================================================
Classifies every file in your Main Crate into genre-based sub-folders
under DJ_MUSIC/, using filename keyword analysis.

VERSION 13 — v13 keyword batch applied (2026-03)
  Progress trajectory (3,776 tracks total):
    Baseline  → 26.3% INBOX (993 tracks)
    v7+v8     → 22.0% (831 tracks)
    v9        → 20.7% (781 tracks)
    v10       → 19.3% (730 tracks)
    v11       → 18.1% (683 tracks)  ← accent + underscore fixes
    v12       → 16.4% (619 tracks)
    v13       → 12.7% (480 tracks)  ← deep research on all 619 remaining INBOX

  Each version = one full analysis of INBOX + targeted keyword batch:
    • v7/v8: 80+ artists across all genres (993-track INBOX)
    • v9:    electronic / house deep-dive
    • v10:   rock, pop, classics, world expansion
    • v11:   accent fixes (marías, jhené), underscore variants, 50+ artists
    • v12:   60+ artists + song-title keywords + underscore/accent fixes
    • v13:   150+ keywords — deep research on all 619 remaining INBOX tracks

  DJ setup: Pioneer DDJ-FLX4, Rekordbox 7

USAGE:
  python3 sort_main_crate.py --preview    ← shows plan, moves NOTHING
  python3 sort_main_crate.py --execute    ← runs the actual moves

SAFETY:
  - Always run --preview and check the output before --execute
  - Unclassified files go to 00_INBOX/ for your manual review
  - No files are deleted or renamed — only moved
  - Run Rekordbox 7: File → Relocate → Auto Relocate after executing

REKORDBOX 7 WORKFLOW:
  1. Run: python3 sort_main_crate.py --preview
  2. Check the output — verify folder distribution looks right
  3. Run: python3 sort_main_crate.py --execute
  4. Rekordbox 7: File → Library → Relocate → Auto Relocate
     (reconnects moved files to existing cue/loop/grid data)
  5. Manually review 00_INBOX/ and sort remaining files as needed
"""

import os
import re
import sys
import shutil
import unicodedata
import csv
from pathlib import Path
from collections import defaultdict

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION — edit these paths if yours differ
# ─────────────────────────────────────────────────────────────────────────────

MAIN_CRATE    = Path("/Users/Lionmit/Music/Main Crate")
DJ_MUSIC_ROOT = Path("/Users/Lionmit/Music/DJ_MUSIC")

# Folder names inside DJ_MUSIC_ROOT
FOLDERS = {
    "israeli":     "01 Israeli & Hebrew",
    "hiphop":      "02 Hip-Hop & R&B",
    "house":       "03 House & Dance",
    "electronic":  "04 Electronic",
    "pop":         "05 Pop & Commercial",
    "rock":        "06 Rock & Alternative",
    "latin":       "07 Latin",
    "classics":    "08 Classics & Oldies",
    "world":       "09 World & Ecstatic",
    "tools":       "10 Tools & FX",
    "remixes":     "11 Remixes",
    "inbox":       "00_INBOX",
}

# Audio file extensions to process
AUDIO_EXTS = {".mp3", ".flac", ".wav", ".aiff", ".aif", ".m4a", ".ogg", ".wma", ".alac"}

# ─────────────────────────────────────────────────────────────────────────────
# GENRE KEYWORD RULES  (v3 — dramatically expanded + remix fallback)
# Rules are evaluated in order. First match wins.
# Each rule is: (genre_key, [list of keywords]) or (key, None) for special handling
# "remixes" rule is LAST so known-artist remixes still hit their genre first.
# ─────────────────────────────────────────────────────────────────────────────

GENRE_RULES = [

    # ── Tools & FX (check first — these are not music) ───────────────────────
    ("tools", [
        "drum sample", "drum kit", "drum loop", "sample pack",
        " fx_", "_fx_", "fx ", "sound effect", "transition",
        "white noise", "intro tool", "dj tool", "acapella",
        "a cappella", "stab ", "clap ", "kick ",
        "snare ", "hihat", "hi hat", "cymbal",
        "bass loop", "build up", "build-up", "drop tool",
        "scratch ", "crowd cheer", "crowd noise", "air horn",
        "countdown", "vinyl crackle", "record scratch",
        "percussion sample", "instrument loop",
        # Ethnic/world percussion & drum machine sample files
        "dhol ", "dholak", "djembe ", "kenkeni", "krin ",
        "tambora ", "linndrum", "linn drum", "cowbell ",
        "shaker ", "conga ", "bongo ", "clave ", "timbale",
        "guiro", "agogo", "cabasa", "maracas",
        "perc abacaxi", "perc loop", "perc hit",
        "low conga", "hi conga", "lo conga",
        "vox miami",         # Roland TR drum label
        " 7t8", " 727 ", " 808 ", " 909 ", " 707 ",
        " dmx ",             # Oberheim DMX drum machine
        "hihat", "clhat", "closedhat", "openhat", "pedhat",
        "hitom", "midtom", "lotom", "lowtom",
        "rimshot", "rim shot", "tamb loop",
        # ─ Added v7: tools labels from INBOX analysis ─
        "openhh",                 # open hi-hat drum sample label
        "closedhh",               # closed hi-hat drum sample label
        "kryptogram",             # DJ tools/transition label
        "traktorset",             # Traktor DJ set/mix file
        "pfc midburn",            # Midburn festival PFC tool tracks
    ]),

    # ── Israeli & Hebrew ──────────────────────────────────────────────────────
    # Hebrew Unicode (U+0590–U+05FF) detected separately in has_hebrew()
    ("israeli_unicode", None),

    ("israeli", [
        # ─ Verified Israeli artists (from tracklist analysis) ─
        "quarter to africa",
        "made in tlv",
        "darwish",                    # David Abramov, Haifa trance DJ
        "yoel lewis",
        "riff cohen",
        "noga erez",
        "red axes",
        # ─ Mizrahi / mainstream Israeli pop ─
        "eyal golan", "eden ben zaken", "eden ben-zaken",
        "moshe peretz", "kobi peretz", "sarit hadad", "dudu aharon",
        "boaz sharabi", "omer adam", "noa kirel", "bar gofer",
        "lior nini", "avraham tal", "shai gabso", "shiri maimon",
        "keren peles", "harel skaat", "marina maximilian", "ninet tayeb",
        "ziv navon", "ido netanyahu", "ziv yehezkel",
        "idan amedi", "ishay ribo", "omer klein",
        "margalit tzanani", "avi biter", "yigal bashan",
        "zehava ben", "zohar argov", "moshe giat", "arik shadmi",
        "lea shabat", "shoshana damari", "yaffa yarkoni",
        "shlomo artzi", "shalom chanoch", "yehoram gaon", "gali atari",
        "zvika pick", "ofra haza", "arik einstein",
        "izhar cohen", "nurit galron", "gidi gov", "uzi hitman",
        "rami kleinstein", "ilana avital", "orna portath", "yoni rechter",
        "chava alberstein", "naomi shemer",
        "david broza", "shlomi shabat", "shlomi shaban",
        "yehuda poliker", "rita ",
        "ivri lider", "eran tzur",
        "miri aloni", "mosh ben ari", "mosh & tuk",
        "corinne allal", "achinoam nini",
        "ehud banai", "yossi banai", "meir banai", "yuval banai",
        "yaakov shwekey", "mordechai ben david",
        "danny sanderson", "karolina",
        "nikki levy",
        # ─ Israeli rock / indie ─
        "hadag nahash", "hadag",
        "knesiyat hasekhel", "knesiyat",
        "rockfour", "tislam", "minimal compact",
        "asaf avidan", "aviv gefen",
        "static ben el", "static & ben", "static and ben",
        # ─ Israeli hip-hop ─
        "subliminal", "hip hop gal", "hatikva 6", "hatikva6",
        "mook-e", "sagol 59",
        # ─ Israeli electronic / psytrance (also in electronic) ─
        "infected mushroom", "astral projection",
        "vini vici", "captain hook", "ace ventura",
        "skazi", "gms ", "borgore",
        # ─ Genre / language terms ─
        "mizrahi", "mizrachit", "mizrakhi", "mizrachi",
        "yemenite", "sephardi", "sfaradi",
        "israeli", "israelit", "hebrew",
        "pizmon", "shira", "nigun",
        # ─ Common transliterated Hebrew words that appear in titles ─
        "ahava", "ahavah", "ahavat",
        "hayam", "habayit", "haboker", "hatikva",
        "neshama", "neshamot",
        "yerushalayim", "jerusalem", "eretz",
        "shabbat", "shabbos", "chag sameach",
        "mazal tov", "mazel tov",
        "sababa", "achi", "yalla",
        "am yisrael", "yisrael",
        "sashka ",
        # ─ Added v6 ─
        "dana international",
        "eviatar banai",
        "avihu pinhasov",
        "nadav guedj",
        "ravid ",                # Ravid Plotnik / Ravid Kahalani / Ravid Alma
        "laor ",                 # Laor (singer)
        "zohar bar shalom",
        # ─ Added v11: Israeli artists from INBOX analysis ─
        "arutz hakibud",          # Israeli phrase / artist reference
        # ─ Added v12: Israeli artists from INBOX analysis ─
        "hamefakedet",            # HaMefakedet — Israeli TV show theme / viral music
        "ninet ",                 # Ninet Tayeb — Israeli singer (Tfilati, Bo) — trailing space
        "ben el tavori",          # Ben El Tavori — Israeli Mizrahi pop (Shir Meyuchad)
        "zafrir ifrach",          # Zafrir Ifrach — Israeli musician
        # ─ Added v13: Israeli artists from INBOX analysis ─
        "basimlah",               # BaSimlah Aduma — Israeli band
        "dr casper",              # Dr. Casper — Israeli hip-hop/electronic artist
    ]),

    # ── Hip-Hop & R&B ─────────────────────────────────────────────────────────
    ("hiphop", [
        # ─ Added from tracklist analysis ─
        "eminem", "m.i.a.", "macklemore", "ryan lewis",
        "lizzo",
        # ─ Old school / Golden Age ─
        "run dmc", "run-dmc", "ll cool j",
        "public enemy", "nwa ", "n.w.a", "ice cube", "ice-t", "ice t",
        "beastie boys", "beastie",
        "tribe called quest", "a tribe called",
        "wu-tang", "wu tang", "method man", "raekwon", "ghostface",
        "ol dirty bastard", "odb ", "gza ", "rza ", "inspectah",
        "big l", "big pun", "big l ",
        "kool g rap", "kool moe dee",
        "slick rick", "mc lyte",
        # ─ 90s ─
        "nas ", "biggie", "notorious b.i.g", "notorious big",
        "2pac", "tupac", "snoop dogg", "snoop dog",
        "dr dre", "dr. dre", "death row",
        "mc hammer", "vanilla ice",
        "dmx ", "ja rule", "eve ", "ludacris",
        "nelly ", "outkast", "andre 3000", "big boi",
        "jay-z", "jay z",
        # ─ 2000s ─
        "kanye", "kanye west",
        "t.i.", " ti_", "young jeezy", "jeezy",
        "lil jon", "t-pain", "t pain",
        "flo rida", "akon ",
        "ne-yo", "ne yo", "chris brown",
        "soulja boy", "lil wayne", "weezy",
        "rick ross", "gucci mane", "young joc",
        "bow wow", "jermaine dupri", "chingy",
        "petey pablo", "david banner",
        "lupe fiasco", "common ", "mos def", "talib kweli",
        "the game ", "50 cent", "g-unit",
        "lloyd banks", "tony yayo",
        # ─ 2010s ─
        "drake", "nicki minaj", "wiz khalifa",
        "kendrick lamar", "kendrick",
        "j cole", "j. cole", "big k.r.i.t",
        "mac miller", "kid cudi", "cudi",
        "childish gambino", "donald glover",
        "tyler the creator", "tyler, the creator",
        "frank ocean", "the weeknd", "weeknd", "abel tesfaye",
        "meek mill", "big sean", "2 chainz", "2chainz",
        "chance the rapper", "vic mensa",
        "fetty wap", "rae sremmurd", "swae lee",
        "lil uzi", "future ", "young thug",
        "migos", "offset ", "quavo", "takeoff",
        "21 savage", "travis scott",
        "post malone", "logic ",
        "a$ap", "asap rocky", "asap mob",
        "missy elliott", "timbaland",
        "swizz beatz", "pharrell", "n.e.r.d",
        "action bronson", "schoolboy q",
        "vince staples", "earl sweatshirt",
        "joey bada$$", "joey badass",
        # ─ Added v4: missing hip-hop / R&B artists ─
        "heavy d", "heavy d and the boyz", "heavy d & the boyz",
        "will smith ",        # trailing space avoids 'will smiths' or compound names
        "lil dicky",
        "tego calderon", "tego calderón",
        "felt ",              # hip-hop supergroup (Murs + Slug) — trailing space
        "serpentwithfeet",    # art R&B / neo-soul
        "lady wray",          # deep soul / R&B
        "dcappella",          # a cappella hip-hop covers
        # ─ 2020s ─
        "polo g", "pop smoke", "lil baby",
        "dababy", "da baby", "nba youngboy",
        "jack harlow", "rod wave",
        "moneybagg yo", "lil durk", "king von",
        "doja cat", "saweetie", "megan thee stallion",
        "city girls", "young m.a",
        "gunna", "lil tecca", "lil mosey",
        "pooh shiesty", "42 dugg",
        "roddy ricch", "blueface", "shordie shordie",
        "lil nas x",
        # ─ R&B ─
        "usher", "alicia keys", "rihanna",
        "beyonce", "beyoncé",
        "mary j blige", "mary j. blige",
        "r kelly", "trey songz", "august alsina",
        "tank ", "miguel ",
        "jhene aiko", "jhene", "jhené aiko", "jhené", "h.e.r.",  # jhené variants for accented filenames
        "summer walker", "sza ",
        "khalid", "daniel caesar",
        "bryson tiller", "partynextdoor", "pnd ",
        "6lack", "giveon", "brent faiyaz",
        "teyana taylor", "kehlani",
        "tinashe", "elle varner",
        "toni braxton", "brandy ", "monica ",
        "destiny's child", "destinys child",
        "tlc ", "en vogue", "salt-n-pepa", "salt n pepa",
        "erykah badu", "lauryn hill", "d'angelo", "dangelo",
        "jill scott", "india arie",
        "musiq soulchild", "anthony hamilton",
        # ─ UK grime / drill ─
        "stormzy", "skepta", "giggs ",
        "dave ", "slowthai", "headie one",
        "central cee", "digga d", "aitch ",
        "tion wayne", "russ millions",
        "nines", "ghetts", "wretch 32",
        "chip ", "dizzee rascal", "tinchy stryder",
        "tinie tempah", "wiley", "jme ",
        # ─ Added v5: hip-hop/R&B artists from INBOX analysis ─
        "naughty by nature",      # classic hip-hop (OPP, Hip Hop Hooray)
        "fabolous",               # NY rap
        "wyclef jean",            # Fugees member / solo
        "geto boys", "scarface",  # Southern rap / Geto Boys
        "cam'ron", "killa cam",   # Dipset / NY rap
        "biz markie",             # classic hip-hop (Just a Friend)
        "sir mix-a-lot",          # West Coast rap (Baby Got Back)
        "d12 ",                   # Eminem's group — trailing space
        "fat joe",                # NY rap / bronx
        "desiigner",              # trap (Panda)
        "foxy brown",             # NY rap / Roc-A-Fella
        "ginuwine",               # R&B
        "ying yang twins",        # Atlanta crunk
        "pras ",                  # Fugees member — trailing space
        "ptaf ",                  # PTAF / hip-hop — trailing space
        "juvenile ",              # Cash Money / NOLA rap — trailing space
        "silkk the shocker",      # No Limit / Southern rap
        "mystikal",               # NOLA rap
        "big tymers",             # Cash Money duo
        "mack 10",                # West Coast rap
        "twista ",                # Chicago rap — trailing space
        "bone thugs",             # Bone Thugs-n-Harmony
        "do or die",              # Chicago rap
        "spice 1",                # West Coast rap
        "mc ren",                 # NWA / solo
        "above the law",          # West Coast rap
        "king tee",               # West Coast rap
        "compton's most wanted",  # West Coast rap
        "bad meets evil",         # Eminem + Royce da 5'9"
        "royce da 5",             # covers "Royce da 5'9""
        "yelawolf",               # Southern rap/rock
        "rittz ",                 # rap — trailing space
        "jarren benton",          # underground rap
        "hopsin",                 # independent rap
        "futuristic",             # Midwest rap
        "machine gun kelly", "mgk ",  # rap/rock
        "joyner lucas",           # storytelling rap
        "token ",                 # teen rap — trailing space
        "tom macdonald", "tom mcdonald",  # Canadian independent rap
        "lil pump",               # SoundCloud rap
        "smokepurpp",             # SoundCloud rap
        "zillakami",              # NY punk rap
        "city morgue",            # NY punk rap
        "flatbush zombies",       # Brooklyn alt-rap
        "denzel curry",           # Florida alt-rap
        "rico nasty",             # Maryland alt-rap
        "little simz",            # UK female rapper
        "lady leshurr",           # UK female rapper/grime
        "shystie",                # UK female grime
        "lady sovereign",         # UK grime
        # ─ Genre terms ─
        "hip hop", "hip-hop", "hiphop",
        "r&b", "rnb", "rap ",
        "trap ", "gangsta", "boom bap", "freestyle rap",
        "g-funk", "chopped", "slowed", "screwed",
        "cypher", "diss track", "mixtape",
        "grime", "uk drill", "afroswing",
        "afrobeats dj", "melodic rap",
        # ─ Added v6 ─
        "cardi b",
        "mobb deep",              # Queens rap (Shook Ones, Hell on Earth)
        "young money",            # Lil Wayne's label/collective
        "sage the gemini",        # Bay Area hip-hop
        "kent jones",             # hip-hop (Don't Mind)
        "nardo wick",             # Jacksonville drill
        "drapht",                 # Australian hip-hop
        "hilltop hoods",          # Australian hip-hop
        "kota the friend",        # Brooklyn indie rap
        "erica banks",            # Dallas rap
        # ─ Added v7: hip-hop artists from INBOX analysis ─
        "j. cole", "j.cole",      # Fayetteville rapper (No Role Modelz, MIDDLE CHILD)
        "azealia banks",          # NYC rapper/pop — NB: must come before "banks" in pop section
        "stefflon don",           # UK grime/rap-pop (Hurtin' Me)
        "yung gravy",             # Minnesota rap-pop novelty (Mr. Clean, Betty)
        # ─ Added v8: hip-hop/R&B artists from full INBOX analysis ─
        "cali swag district",     # West Coast hip-hop (Teach Me How to Dougie)
        "lil mama",               # NYC hip-hop/pop (Lip Gloss, Shawty Get Loose)
        "dej loaf",               # Detroit hip-hop/R&B (Try Me, Liberated)
        "die antwoord",           # South African hip-hop/rave (I Fink U Freeky, Ugly Boy)
        # ─ Added v10: hip-hop artists from INBOX analysis ─
        "nate dogg",              # West Coast rapper/singer (21 Questions ft. 50 Cent, The Next Episode)
        "alligatoah",             # German hip-hop/rap (Willst Du, Monster)
        # ─ Added v12: hip-hop artists & song titles from INBOX analysis ─
        "gin and juice",          # Snoop Dogg classic (1993) — song title keyword for filename-only tracks
        "jeshi",                  # UK rapper (Universal Credit, 3310)
        "the rza",                # Wu-Tang Clan producer / rapper (Wu-Tang Clan Ain't Nuthing ta F' Wit)
        # ─ Added v13: hip-hop artists & song titles from INBOX analysis ─
        "bodak yellow",           # Cardi B hit — title keyword
        "gravel pit",             # Wu-Tang Clan track — title keyword
        "jump around",            # House of Pain — title keyword
        "nappy roots",            # Southern hip-hop (Po' Folks, Good Day)
        "khia ",                  # US hip-hop/crunk (My Neck My Back) — trailing space
        "dj chose",               # Houston hip-hop producer
        "earthgang",              # Atlanta hip-hop duo (Mirrorland)
        "shnekel",                # Israeli hip-hop artist
        "skero ",                 # Austrian rapper (Kabipp) — trailing space
        "die atzen",              # German party rap duo (Disco Pogo)
        "frauenarzt",             # German rapper
        "manny marc",             # German rapper (Frauenarzt collaborator)
        "sdp ",                   # German hip-hop duo — trailing space
        "opm ",                   # US rap-rock (Heaven Is a Halfpipe) — trailing space
        "rollin'",                # Limp Bizkit / other hip-hop title keyword
    ]),

    # ── Latin ─────────────────────────────────────────────────────────────────
    ("latin", [
        # ─ Added from tracklist analysis ─
        "ivete sangalo",
        # ─ Added v5: Latin artists from INBOX analysis ─
        "rosalía", "rosalia ",    # Spanish flamenco-pop/urban (La Malamente, Con Altura)
        "santana ",               # trailing space — Carlos Santana / Santana band
        "los lobos",              # Chicano rock/Latin rock (La Bamba)
        "becky g",                # Latina pop/reggaeton
        "jowell y randy",         # Puerto Rican reggaeton duo
        "trinidad cardona",       # reggaeton/trap (Dinero)
        "bonde do rolê",          # Brazilian funk/baile funk
        "bonde do role",          # ASCII variant
        "porto seguro",           # Brazilian samba
        "carrapicho",             # Brazilian forró/baile funk (Tic, Tic, Tac)
        "jorge ben", "jorge ben jor",  # Brazilian samba/MPB
        "tim maia",               # Brazilian soul/MPB
        "caetano veloso",         # Brazilian MPB (Tropicália)
        "gilberto gil",           # Brazilian MPB (Tropicália)
        "gal costa",              # Brazilian MPB
        "seu jorge",              # Brazilian samba/MPB
        "mc bin laden",           # Brazilian funk
        "l7nnon",                 # Brazilian hip-hop/trap
        "matuê",                  # Brazilian trap
        "veigh ",                 # Brazilian rap — trailing space
        "xande de pilares",       # Brazilian pagode
        "thiaguinho",             # Brazilian pagode/samba
        "rodriguinho",            # Brazilian pagode
        "nego do borel",          # Brazilian funk
        # ─ Reggaeton ─
        "j balvin", "bad bunny", "daddy yankee", "shakira", "maluma",
        "ozuna", "anuel aa", "karol g", "nicky jam",
        "wisin", "yandel", "don omar",
        "rauw alejandro", "myke towers", "farruko",
        "sech", "jhay cortez", "justin quiles",
        "lunay", "lenny tavarez", "dalex",
        "quevedo", "paulo londra", "bizarrap",
        "duki", "peso pluma", "natanael cano",
        "christian nodal", "ivan cornejo",
        "grupo firme", "banda ms",
        "jhayco", "mora ",
        # ─ Latin pop ─
        "marc anthony", "jennifer lopez", "j.lo",
        "pitbull", "ricky martin", "enrique iglesias", "luis fonsi",
        "alejandro sanz", "juanes", "gloria estefan", "selena",
        "celia cruz", "hector lavoe", "willie colon",
        "olga tanon", "victor manuel", "pablo alboran",
        "alejandro fernandez", "carlos vives",
        "ana gabriel", "lupillo rivera",
        "pedro infante", "vicente fernandez",
        # ─ Brazilian ─
        "anitta", "alok ", "dennis dj",
        "mc kevinho", "mc pedrinho",
        "mc livinho", "mc lan",
        "funk carioca", "funk brasileiro",
        # ─ Global reggaeton / collab ─
        "despacito", "con calma", "danza kuduro",
        "macarena", "bailando", "la gozadera",
        "gasolina", "loca", "papi",
        # ─ Genre terms ─
        "reggaeton", "salsa", "bachata", "cumbia", "merengue",
        "latin pop", "urbano", "perreo", "dembow",
        "samba ", "bossa nova", "forró", "axé",
        "champeta", "vallenato", "mariachi",
        "latin jazz", "latin house",
        "moombahton", "latin trap",
        "corrido", "banda ", "norteño",
        # ─ Added v6 ─
        "carlos gardel",          # Argentine tango legend
        "bomba estéreo", "bomba estereo",   # Colombian electrotropical
        "mercedes sosa",          # Argentine Nueva Canción
        "joan manuel serrat",     # Catalan/Spanish singer-songwriter
        "alvaro soler",           # Spanish-German pop (Sofia, El Mismo Sol)
        "chambao",                # Spanish flamenco chill / chillout
        "los bravos",             # Spanish beat group (Black Is Black, 1966)
        "proyecto uno",           # Dominican merengue-rap
        "naâman", "naaman",       # French reggae artist
        # ─ Added v7: Latin artists from INBOX analysis ─
        "king blvck",             # German-Ghanaian reggaeton/afrobeats
        "rigoberta bandini",      # Spanish pop-rock singer-songwriter
        "nina sky",               # Puerto Rican duo (Move Ya Body)
        "kat deluna", "kat de luna",  # Dominican-American singer (Whine Up)
        "los autenticos decadentes",  # Argentine rock en español / cumbia
        # ─ Added v13: Latin artists from INBOX analysis ─
        "konshens",               # Jamaican dancehall/reggaeton crossover
        "rupee ",                 # Barbadian soca/dancehall (Tempted to Touch) — trailing space
        "lil bitts",              # Latin-electronic crossover
        "sergio mendes",          # Brazilian bossa nova/pop (Mas Que Nada)
        "chingon",                # Mexican rock/Latin (Mexican Spaghetti Western, Machete OST)
        "delfina dib",            # Argentine singer-songwriter
        "ludmilla",               # Brazilian funk/pop singer (Tipo Crazy)
        "berimbau",               # Brazilian instrument / title keyword (Astrud Gilberto)
    ]),

    # ── House & Dance ─────────────────────────────────────────────────────────
    ("house", [
        # ─ Added from tracklist analysis ─
        "maestracci",         # organic house, Corsican/French
        "earth n days",
        "saxity",
        "blackboxx",
        "timeless glow",
        "bakermat",
        "secondcity",
        "block & crown", "block and crown",
        "modjo",              # "Lady (Hear Me Tonight)"
        "madison avenue",     # "Don't Call Me Baby"
        "funkanomics",
        "galantis",
        "shiba san",
        # ─ Big EDM / progressive house ─
        "calvin harris", "david guetta", "tiësto", "tiesto",
        "avicii", "martin garrix", "hardwell", "afrojack",
        "swedish house mafia", "swedish house",
        "eric prydz", "fedde le grand", "nicky romero",
        "armin van buuren", "van buuren",
        "above & beyond", "above and beyond",
        "faithless", "fatboy slim",
        "basement jaxx", "groove armada",
        "bob sinclar", "bob sinclair",
        "dj snake", "dj khaled", "marshmello",
        "kygo ", "robin schulz",
        "alesso", "zedd ",
        "kshmr", "showtek", "bassjackers",
        "ummet ozcan", "w&w ",
        "blasterjaxx", "thomas gold", "chuckie",
        "laidback luke", "r3hab", "tom staar",
        "nervo", "yellow claw",
        "sigma ",
        # ─ Deep / tropical house ─
        "duke dumont", "disclosure",
        "route 94", "mk ",
        "gorgon city", "sam feldt",
        "lost frequencies", "kungs ",
        "ofenbach", "regard ",
        "meduza", "sofi tukker",
        "purple disco machine",
        "claptone", "tensnake",
        "breakbot", "todd terje",
        "bicep ", "jon hopkins",
        "boiler room",
        # ─ UK garage / 2-step ─
        "craig david", "mj cole",
        "so solid crew",
        "artful dodger", "shanks & bigfoot",
        "oxide & neutrino",
        # ─ Added v4: classic/commercial house artists ─
        "crystal waters",     # "Gypsy Woman" — US house classic
        "milk & sugar", "milk and sugar",  # German house duo
        "dr. alban", "dr alban",           # Swedish eurodance/house
        "robin s",            # "Show Me Love" — US house classic
        "erick morillo", "morillo",        # house DJ / "I Like to Move It"
        "hedegaard",          # Danish house/future bass DJ
        "coeo",               # German nu-disco/house duo (Toy Tonic)
        "eva simons",         # Dutch house vocalist
        "saison ",            # London deep house duo (Defected/Toolroom) — trailing space
        "deep matter",        # house producer
        # ─ Classic house ─
        "frankie knuckles", "larry levan",
        "larry heard", "mr fingers", "todd terry",
        "kerri chandler", "dj harvey",
        "marshall jefferson", "junior jack",
        "louie vega", "david morales",
        "frankie going hollywood",
        # ─ Tech house ─
        "hot since 82", "marco carola",
        "jamie jones", "seth troxler",
        "green velvet", "detlef",
        "george fitzgerald", "richy ahmed",
        "hannah wants", "jack back",
        "dirtybird", "justin martin",
        "waFF", "miguel clarimond",
        # ─ Melodic house ─
        "anyma", "massano", "innellea",
        "tale of us", "afterlife",
        "modeplex", "amelie lens",
        # ─ Afro house ─
        "black coffee", "themba ",
        "enoo napa", "culoe de song",
        "christos fourkis",
        # ─ Crossover pop-house ─
        "ellie goulding", "john newman",
        "rudimental", "becky hill",
        "ella henderson", "jess glynne",
        "paloma faith", "charli xcx",
        "bebe rexha", "jasmine thompson",
        # ─ Commercial dance / eurodance ─
        "benny benassi", "scooter",
        "cascada", "alice dj", "alice deejay",
        "darude", "atb ",
        "ian van dahl", "lasgo",
        "djs from mars",
        "bob the builder",
        "vengaboys", "dj bobo",
        "2 unlimited", "haddaway",
        "snap ", "la bouche", "real mccoy",
        "corona ", "livin joy",
        "culture beat", "alexia",
        "technotronic", "twenty 4 seven",
        "lmfao", "redfoo",
        "will i am", "will.i.am",
        "taio cruz",
        # ─ Garage / bass ─
        "skream", "benga ", "joy orbison",
        "bok bok", "alex schulmman",
        # ─ Added v5: house artists from INBOX analysis ─
        "armand van helden",      # US house producer (Flowerz, My My My)
        "fisher ",                # Aussie tech-house DJ (You Little Beauty) — trailing space
        "shapeshifters",          # UK deep/house (Lola's Theme)
        "ultra nate", "ultra naté",  # US house vocalist (Free)
        "yolanda be cool",        # Australian house ("We No Speak Americano")
        "defkline",               # part of "Yolanda Be Cool & DCup"
        "illyus & barrientos", "illyus and barrientos",  # Scottish tech-house duo
        "eli & fur", "eli and fur",  # UK melodic house duo
        "bedouin",                # Palestinian-Australian house duo (Innervisions)
        "stephan bodzin",         # German techno/melodic house
        "ben böhmer", "ben bohmer",  # German melodic house
        "&me ",                   # &ME, German melodic house — trailing space
        "rampa ",                 # Keinemusik DJ — trailing space
        "adam port",              # Keinemusik DJ
        "keinemusik",             # Berlin house label
        "woo york",               # Ukrainian melodic techno duo
        "patrice bäumel", "patrice baumel",  # Dutch melodic techno/house
        "marino canal",           # Spanish house
        "tinlicker",              # Dutch melodic house duo
        "pretty pink",            # German progressive/melodic house
        "dj dep",                 # Israeli house DJ
        "sam paganini",           # Brazilian techno
        "huxley ",                # UK tech-house — trailing space
        "skream",                 # already in list — safety skip
        "eats everything",        # UK bass-house
        "cause & affect", "cause and affect",  # tech-house
        "bontan ",                # UK tech-house — trailing space
        "bicep",                  # already in list — safety skip
        "ejeca ",                 # UK house — trailing space
        "cinthie ",               # Berlin house — trailing space
        "dj steaw",               # house
        "blondish",               # Afro/organic house
        "nicone ",                # German house — trailing space
        "chaim ",                 # Israeli house producer — trailing space
        "dj hell",                # German electro house (International Deejay Gigolo)
        "miss kittin", "miss kittin & the hacker",  # French electro/techno
        "the hacker",             # French electro
        "dan bell",               # minimal techno
        "paul kalkbrenner",       # Berlin techno/house
        "charlotte de witte",     # Belgian techno
        "amelie lens",            # already in list — safety skip
        "peggy gou",              # Korean-German house (It Goes Like)
        "honey dijon",            # Chicago house DJ
        "dj stingray",            # Detroit electro/techno
        "moodymann",              # Detroit deep house
        "theo parrish",           # Detroit deep house
        "kyle hall",              # Detroit house
        # ─ Record labels in filenames ─
        "defected", "toolroom", "spinnin",
        "ministry of sound", "monstercat",
        "cr2 records", "hed kandi",
        "nervous records", "glitterbox",
        "ultra records", "big beat",
        "positiva", "data records",
        "all around the world", "v recordings",
        # ─ Genre terms ─
        "house ", " house_", "deep house", "tech house",
        "progressive house", "electro house",
        "dance floor", "dancefloor", "club mix", "club edit",
        "extended mix", "radio edit", "original mix",
        # underscore variants — Beatport numeric ID filenames use _ not space
        "_extended_mix", "_original_mix", "_club_mix", "_radio_edit",
        "bootleg", "mashup", "mash-up", "mash up",
        "nu disco", "nudisco",
        "afrohouse", "afro house", "tropical house",
        "funky house", "soulful house",
        "jackin house", "tribal house",
        "uk garage", "future bass", "bass house",
        "dj set", "live set", "festival mix",
        "disco ", "funky ",
        # ─ Added v6 ─
        "deee-lite", "deee lite",   # NYC dance/house (Groove Is in the Heart, 1990)
        "stardust ",                # French house duo (Music Sounds Better With You, 1998) — trailing space
        "moloko",                   # Irish trip-hop/dance (Sing It Back, The Time Is Now)
        # ─ Added v10: house artists from INBOX analysis ─
        "lissat",                   # Dutch DJ/producer (Ain't Nobody — lissat_and_voltaxx collab)
        "low steppa",               # UK deep/soulful house producer (You're My Life)
        "low_steppa",               # underscore variant for filenames
        # ─ Added v12: house artists & song titles from INBOX analysis ─
        "freed from desire",        # Gala (1997) — song title keyword; "gala " alone misses this filename
        "rui da silva",             # Portuguese house producer (Touch Me, 2001)
        "david penn",               # Spanish house DJ/producer (You Are Somebody, Funky Drummer)
        "arthur baker",             # NYC electro/dance pioneer (Rockit remix, Planet Rock, Breaker's Revenge)
        "victor simonelli",         # NYC garage/deep house producer (Let There Be House, Bassline)
        "john morales",             # NYC house remixer — M+M Mixes (Ain't Nobody, I Need You Now)
        "dj spen",                  # Baltimore house DJ/producer (Nite Life, Joy)
        "will clarke ",             # UK house/techno producer (Good Lemonade, Our Love) — trailing space
        # ─ Added v13: house artists & song titles from INBOX analysis ─
        "michelle weeks",           # US house vocalist (The Light, Don't Give Up)
        "djane housekat",           # German DJ (My Party, All the Time)
        "housekat",                 # short variant
        "agatino romero",           # German/Italian house DJ
        "bruno martini",            # Brazilian house/dance producer (Hear Me Now)
        "breach ",                  # UK deep house producer (Jack) — trailing space
        "bodybangers",              # German house/dance production team
        "chelina manuhutu",         # Dutch house DJ
        "chris lorenzo",            # UK bass house producer (California Dreamin')
        "croatia squad",            # German house duo (The D Machine)
        "combustibles",             # House/electronic project
        "criminal vibes",           # European house producer
        "dombresky",                # French house/tech producer (Bubblin')
        "funkatron",                # Funky house producer
        "gamper ",                  # Austrian house DJ (Gamper & Dadoni) — trailing space
        "krystal klear",            # Irish house/disco DJ
        "laserkraft",               # German house/electro duo (Laserkraft 3D — Nein Mann)
        "lee foss",                 # US house DJ (Hot Creations label)
        "lil' louis",               # Chicago house pioneer (French Kiss)
        "lil louis",                # variant without apostrophe
        "mobin master",             # Australian house producer
        "me & my toothbrush",       # European house duo
        "michael mind",             # German house producer (Michael Mind Project)
        "mike candys",              # Swiss house DJ (Together Again)
        "nari & milani",            # Italian house DJs
        "cristian marchi",          # Italian house DJ/producer
        "never dull",               # South African house/disco producer
        "picard brothers",          # French disco-house duo
        "san pacho",                # Colombian house/tech house producer
        "toomanylefthands",         # Danish house duo
        "vato gonzalez",            # Dutch house DJ (Badman Riddim)
        "jolyon petch",             # Australian house/dance DJ
        "masteria",                 # House producer
        "babert",                   # French disco-house producer
        "mell hall",                # Australian house/disco producer
        "black loops",              # Spanish house/minimal producer
        "youandewan",               # UK deep house producer
        "fort romeau",              # UK deep house/electronic producer
        "drinks on me",             # House/R&B crossover artist
        "david versace",            # Australian house DJ
        "tenshu",                   # House/bass producer
        "kdyn",                     # House/electronic artist
        "harrison bdp",             # UK house/breakbeat producer
        "ootoro",                   # Electronic/house producer
        "cortese",                  # Italian house project
        "argy ",                    # Greek house/techno DJ — trailing space
        "darius & finlay",          # German house duo (Tropicali)
        "dj sammy",                 # Spanish Eurodance/house DJ (Heaven)
        "french affair",            # German-French house pop (My Heart Goes Boom)
        "martin jensen",            # Danish house/future bass DJ (Solo Dance)
        "remady",                   # Swiss house DJ
        "lothief",                  # House/melodic techno artist
        "sam shure",                # Israeli-German melodic house producer
        "audiosonik",               # European house DJ
        u"d\u00e9but de soir\u00e9e",  # French disco/pop (Nuit de Folie)
        "debut de soiree",          # ASCII variant
        "lika morgan",              # German house/vocal pop (Feel the Same)
        "franky wah",               # UK progressive house DJ
        "john summit",              # US house/tech house producer (Deep End)
        "jean tonique",             # French house/disco producer
        "braga circuit",            # House/electronic project
        "herr krank",               # European house/techno producer
        "delroy edwards",           # US house/dance producer (L.I.E.S. label)
        "stazzia",                  # House/dance vocalist
        "douvelle",                 # House/electronic artist
        "100% pure love",           # Crystal Waters title keyword (1994)
        "the bomb ",                # Bucketheads title keyword (The Bomb) — trailing space
        "the business",             # Tiësto title keyword (The Business, 2020)
        "blackwater",               # Octave One title keyword (Blackwater, 2001)
    ]),

    # ── Electronic / Psytrance / Techno ───────────────────────────────────────
    ("electronic", [
        # ─ Added from tracklist analysis ─
        "arthur russell",     # NYC avant-garde electronic / disco
        "moby ",              # space after 'moby' to avoid false positives
        "sylvan esso",
        "big wild",
        "stromae",
        "la roux",
        "major lazer",
        "mfinity",
        "anna meredith",
        "deichkind",
        "glass animals",
        "polo & pan", "polo and pan",
        "kraftwerk",
        "new order",
        "joy division",       # post-punk/electronic crossover
        # ─ Israeli psytrance ─
        "infected mushroom", "astral projection",
        "gms ", "perfect stranger", "sun project", "loud ",
        "vini vici", "captain hook", "ace ventura",
        "skazi", "talamasca", "x-dream",
        "astrix", "juno reactor", "hallucinogen",
        "simon posford", "shpongle",
        "avalon ", "oforia", "ubar tmar",
        "1200 mics", "riktam",
        "sol tribe", "alien project",
        "psysex",
        # ─ Global psytrance / goa ─
        "parasense", "vibrasphere",
        "cosmosis", "transwave",
        "total eclipse", "psyphenomenon",
        # ─ Trance ─
        "armin van buuren", "paul van dyk",
        "sasha ", "john digweed",
        "markus schulz", "paul oakenfold",
        "ferry corsten", "tiesto",
        "above & beyond",
        "giuseppe ottaviani", "solarstone",
        "factor b", "bryan kearney",
        "aly & fila", "aly and fila",
        "gareth emery", "andrew rayel",
        "dash berlin", "cosmic gate",
        "judge jules", "mike shiver",
        "simon & biggs", "chicane",
        "atb ", "darude",
        "ian van dahl", "alice dj",
        "rank 1", "push ", "svenson",
        "binary finary",
        # ─ Added v4: trance artists from numbered 1.xx tracks ─
        "omnia ",             # trailing space — avoids 'omnia records'
        "ilan bluestone",
        "denis kenzo",
        "kryder",
        "arty ",              # DJ/producer Arty — trailing space
        "genix",
        "super8 & tab", "super8 and tab",
        "rodg ",              # trailing space
        "estiva",
        "david gravell",
        "simon lee & alvin", "simon lee and alvin",
        "alexander popov",
        "drym",
        "luke bond",
        "orjan nilsen", "ørjan nilsen",
        "ana criado",
        "andrew bayer",
        "ashley wallbridge",
        # ─ Added v5: trance artists from INBOX analysis ─
        "christina novelli",      # vocal trance (1.05 track)
        "alexandra badoi",        # trance vocalist (Feel & Alexandra Badoi)
        "frainbreeze",            # progressive/trance producer
        # ─ Added v5: electronic artists from INBOX analysis ─
        "gesaffelstein",          # dark electro/industrial
        "tycho ",                 # trailing space — ambient electronic
        "celldweller",            # electronic rock/industrial
        "mr oizo", "mr. oizo",    # French electro / Filter
        "nghtmre",                # bass/EDM
        "slander ",               # EDM duo
        "1200 micrograms", "1200mcg",  # Goa/psytrance
        "infected mushroom",      # already likely present — safety add
        "skrillex",               # dubstep/EDM
        "rezz ",                  # dark electronic
        "hermitude",              # electronic hip-hop / trip-hop
        # ─ Techno ─
        "carl cox", "ben klock",
        "marcel dettmann", "adam beyer",
        "blawan", "surgeon",
        "speedy j", "len faki",
        "plastikman", "richie hawtin",
        "sven vath", "sven väth",
        "chris liebing", "sam paganini",
        "joseph capriati", "nina kraviz",
        "dax j", "mndsgn",
        "dj stingray",
        # ─ Drum & Bass ─
        "goldie", "ltj bukem",
        "roni size", "bad boy bill",
        "sub focus", "chase & status", "chase and status",
        "andy c", "high contrast",
        "pendulum", "total science", "calibre",
        "danny byrd", "shy fx",
        "congo natty", "dj marky",
        "logistics", "london elektricity",
        "hospital records",
        # ─ Dubstep ─
        "benga ", "digital mystikz",
        "mala ", "coki ",
        "rusko", "caspa",
        "cookie monsta", "doctor p",
        "flux pavilion", "12th planet",
        "excision", "datsik",
        "skrillex", "borgore",
        # ─ International electronic ─
        "daft punk", "aphex twin", "chemical brothers",
        "prodigy", "the prodigy", "underworld",
        "massive attack", "portishead", "tricky ",
        "deadmau5", "diplo ",
        "flume ", "four tet", "four-tet",
        "caribou", "bonobo", "moderat",
        "boards of canada", "autechre",
        "orbital", "future sound of london",
        "crystal method", "lfo ",
        "squarepusher", "amon tobin",
        "plaid",
        "nightmares on wax",
        "odesza", "madeon",
        "porter robinson", "what so not",
        "kaytranada", "shlohmo",
        "nicolas jaar", "machinedrum",
        "gramatik", "bassnectar",
        "pretty lights", "sts9",
        # ─ Added v4: electronic / DJ artists ─
        "theo parrish",       # Detroit deep house / electronic
        "pachanga boys",      # German minimal house (Kompakt)
        "blundetto",          # French beats / world bass
        "joey pecoraro",      # lo-fi beats / electronic
        "moreno pezzolato",   # Italian nu-disco / electronic
        "carbon decay",       # cyberpunk/dubstep/techno producer
        "c2c ",               # French turntablist group — trailing space (avoids 'c2c records' false pos)
        "camelphat",          # UK house/electronic duo
        "the allergies",      # UK hip-hop/breaks duo
        "krono ",             # French electronic producer — trailing space
        # ─ Genre terms ─
        "psytrance", "psy trance", "psy-trance",
        "goa trance", "goa ",
        "progressive psy", "full on", "fullon",
        "techno ", "trance ",
        "dubstep", "drum and bass", "drum & bass", "dnb",
        "ambient ",
        "edm ", "electro ",
        "synth ", "synthwave",
        "melodic techno",
        "breaks ", "breakbeat",
        "neurofunk", "liquid dnb",
        "hardstyle", "hardcore", "gabber",
        "glitch hop", "glitch",
        "idm ", "experimental",
        # ─ Added v7: electronic / DJ producers from INBOX analysis ─
        "perc ",                  # Perc (Ali Wells) — UK techno — trailing space
        "mura masa",              # UK electronic/pop producer (Love$ick, Lovesick)
        "noizu ",                 # Canadian house/techno DJ — trailing space
        "tim berg",               # Avicii's early alias (Seek Bromance)
        "whethan",                # American future bass/pop-electronic producer
        "klingande",              # French tropical/chillout house producer (Jubel)
        "tungevaag",              # Norwegian DJ/producer (Dynamite)
        "mousse t",               # German-Tunisian house/funk producer (Horny)
        "piero pirupa",           # Italian progressive/melodic house DJ
        "osunlade",               # American deep/afro-house producer (Envision)
        "mako ",                  # UK drum & bass duo — trailing space
        "mochakk",                # Brazilian house/electronic producer
        "roosevelt ",             # German indie-electro pop artist — trailing space
        "young franco",           # Australian electronic/pop producer
        "ian carey",              # American house DJ/producer (Keep On Rising)
        "rank1",                  # Dutch uplifting trance duo (Airwave)
        "pleasurekraft",          # German techno duo (Tarantula)
        # ─ Added v8: electronic artists from full INBOX analysis ─
        "martin solveig",         # French house/electro-pop (Hello, Intoxicated, +1)
        "guru josh",              # British trance/house (Infinity 2008, Infinity)
        "alex gaudino",           # Italian house (Destination Calabria)
        "enur ",                  # Danish-US house (Calabria 2007) — trailing space
        "calabria ",              # keyword for Calabria tracks — trailing space
        "laurent wolf",           # French electro-pop (No Stress, Wash My World)
        "alexandra stan",         # Romanian electronic-pop (Mr Saxobeat, Get Back)
        "jax jones",              # UK dance/electronic (You Don't Know Me, Breathe)
        "aronchupa",              # Swedish pop-EDM (I'm an Albatraoz, Little Swing)
        "twocolors",              # German electronic-pop (Lovefool, Nightbound)
        # ─ Added v9: electronic/dance artists from full INBOX analysis ─
        "wamdue project",         # House/big beat (King of my Castle)
        "wamdue ",                # trailing space variant
        "wilkinson ",             # UK drum and bass (Dirty Love, Afterglow) — trailing space
        "troyboi ",               # UK trap/bass (Do You, After Hours) — trailing space
        "rudenko ",               # Dance/electronic (Everybody) — trailing space
        "robin_schulz",           # German house DJ — underscore variant (filenames use underscores)
        "ida corr",               # Danish house vocalist (Let Me Think About It, Free Me)
        # ─ Added v10: electronic artists from INBOX analysis ─
        "alan walker",            # Norwegian DJ/producer (Faded, Alone, Darkside, Space Melody)
        "a-trak",                 # Canadian DJ/turntablist (Parallel Lines, All I Need)
        "zomboy ",                # UK dubstep/bass music producer (Patient Zero) — trailing space
        # ─ Added v11: electronic artists from INBOX analysis ─
        "maribou state",          # UK electronic duo (One Chance, Turnmills, Tongue)
        "fakear",                 # French electronic producer (Golden Sun, Animal)
        "jan blomqvist",          # German melodic techno/house (Empty Floor, Remote)
        "kerala dust",            # UK electronic duo (Swoon, Heartline, Way Out)
        "golden vessel",          # Australian electronic producer (flaws, Lifespan)
        "baynk",                  # New Zealand electronic producer (Someone, Easy)
        "black strobe",           # French electro/rock-dance (I'm a Man, Boogie In Zero Gravity)
        "debruit",                # French electronic producer (Istanbul is Sleepy, From the Horizon)
        "light asylum",           # Brooklyn darkwave/electronic (IPC, Skull Fuct)
        "bellaire",               # Dutch electronic producer (Everything I Know, You There)
        # ─ Added v12: electronic artists from INBOX analysis ─
        "idris dauwd",            # UK-Libyan electronic producer (Gear, Cities, Lifetime)
        "carlita",                # Egyptian-German melodic house/techno DJ (Momo, Opa Opa)
        "riton",                  # UK electronic/house producer (Rinse & Repeat ft. Haile, Brighter Days)
        "salt cathedral",         # Colombian electronic indie duo (Cool, All Day)
        "tony romera",            # French electro/bass-house producer (Superman, Fire)
        "the supermen lovers",    # French electro-house duo (Starlight, My Magic Dream)
        "dan caster",             # German house/techno DJ (Closer, Spirit)
        "tom wax",                # German trance/techno producer (No Rush, Wax On)
        "ahadadream",             # UK bass/electronic producer (Keel Over, Soot)
        "chemical_brothers",      # The Chemical Brothers — underscore variant for filenames
        "jax jones",              # UK electronic/house producer (You Don't Know Me, Instruction)
        "jax_jones",              # underscore variant for filenames
        "poolside ",              # LA electronic/yacht-disco duo (Slow Down, Do You Believe) — trailing space
        "sleepy fish",            # Japanese lo-fi/electronic producer (Solace, Falling)
        "taiki nulight",          # UK DnB/bass-house producer (Spit, Get Low)
        "serial killaz",          # UK drum & bass duo (Warzone, Time Flies)
        "peaches ",               # Canadian electroclash artist (Fuck the Pain Away, Boys Wanna Be Her) — trailing space
        # ─ Added v13: electronic artists from INBOX analysis ─
        "frederic robinson",      # UK liquid DnB / electronic producer
        "yosi horikawa",          # Japanese experimental electronic (Bubbles, Wandering)
        "pilocka krach",          # German experimental electronic
        "etienne jaumet",         # French electronic/synth artist (Night Music)
        "hucci",                  # Australian trap/electronic producer
        "koreless",               # Welsh electronic producer (Sun, 4D)
        "fasme",                  # French electronic/pop artist
        "cirqular",               # Electronic/bass music producer
        "subb theory",            # UK dubstep/electronic producer
        "neuroplasm",             # Electronic/psychedelic bass artist
        "tentendo",               # Electronic/ambient producer
        "stussko",                # Electronic producer
        "deekapz",                # Electronic/bass producer
        "sandhog",                # Electronic artist
        "coro ",                  # Electronic project — trailing space
        "delerium",               # Canadian ambient/electronic (Silence ft. Sarah McLachlan)
        "neil cicierega",         # US mashup/electronic (Mouth Sounds, Mouth Moods)
        "passion fruit ",         # Electronic/dance act — trailing space
        "alexander marcus",       # German electrolore artist (Hawaii Toast Song)
        "clipz",                  # UK drum & bass producer
        "matrix & futurebound",   # UK drum & bass duo (Magnetic Eyes, Fire)
        "outsiders & dickster",   # Psytrance duo
        "tristan & bliss",        # Psytrance artists
        "esg ",                   # NYC post-punk/electronic (UFO, My Love for You) — trailing space
    ]),

    # ── Rock & Alternative ────────────────────────────────────────────────────
    ("rock", [
        # ─ Added from tracklist analysis ─
        "belle and sebastian", "belle & sebastian",
        "the magnetic fields", "magnetic fields",
        "the chills",
        "surf curse",
        "r.e.m.",
        "gang of four",
        "no doubt",
        "morrissey",
        "dinosaur jr", "dinosaur jr.",
        "they might be giants",
        "elliott smith",
        "nine inch nails",
        # ─ Added v4: classic indie / proto-punk / alternative ─
        "velvet underground", "the velvet underground",
        "the stooges", "iggy pop", "iggy & the stooges",
        "pavement ",          # trailing space — avoids 'pavement mix' etc.
        "built to spill",
        "lemonheads", "the lemonheads",
        "indigo girls",
        "cat power",
        "foxygen",
        "the dandy warhols", "dandy warhols",
        "mild high club",
        "japanese breakfast",
        "allah-las",
        "the clean ",         # NZ indie — space avoids 'clean bandit'
        "the sonics",
        "the growlers",
        "powderfinger",
        "liquid liquid",      # NYC dance-punk / no-wave
        "slapp happy",        # avant-garde / krautrock-adjacent
        "ac_dc",              # filenames use underscore instead of slash
        "fuel ",              # 90s grunge/post-grunge band — trailing space
        "the 5.6.7.8", "5.6.7.8",      # Japanese garage surf rock
        "the centurians", "centurians",  # 60s surf/garage
        "the durutti column", "durutti column",  # post-punk / Manchester
        "rmr ",               # country-trap dark pop — trailing space
        # ─ Heavy / metal ─
        "metallica", "slipknot", "korn",
        "system of a down", "soad",
        "rage against the machine", "ratm",
        "linkin park", "limp bizkit",
        "red hot chili peppers", "rhcp",
        "black sabbath", "ozzy", "iron maiden", "judas priest",
        "megadeth", "anthrax", "sepultura",
        "pantera", "slayer", "testament",
        "machine head", "death angel",
        "down ", "corrosion of conformity",
        "soulfly",
        # ─ Classic rock ─
        "led zeppelin", "pink floyd", "deep purple",
        "ac dc", "ac/dc",
        "guns n roses", "guns n' roses",
        "queen ", "aerosmith",
        "the who", "rolling stones",
        "the doors", "doors ",
        "jimi hendrix", "janis joplin",
        "creedence clearwater", "ccr ",
        "styx ", "foreigner", "boston ",
        "bon jovi", "def leppard",
        "motley crue", "motley crüe",
        "whitesnake", "poison ",
        "thin lizzy", "rainbow",
        # ─ 90s / alternative / grunge ─
        "nirvana", "pearl jam", "soundgarden",
        "alice in chains", "audioslave",
        "foo fighters", "weezer",
        "the offspring", "offspring",
        "green day", "blink-182", "blink 182", "sum 41",
        "smashing pumpkins", "silverchair",
        "bush ", "collective soul",
        "matchbox twenty", "matchbox 20",
        "third eye blind", "live ",
        "stone temple pilots", "stp",
        "tool ", "a perfect circle",
        # ─ 2000s rock ─
        "coldplay", "muse ", "radiohead",
        "the killers", "killers",
        "30 seconds to mars", "thirty seconds",
        "fall out boy", "panic at the disco",
        "my chemical romance", "paramore",
        "evanescence", "within temptation",
        "nickelback", "creed ", "staind",
        "puddle of mudd", "trapt",
        "breaking benjamin", "three days grace",
        "seether", "papa roach", "disturbed",
        "hinder", "theory of a deadman",
        "depeche mode", "the cure", "the smiths",
        "u2 ", "oasis ", "blur ", "pulp ",
        # ─ Indie / modern rock ─
        "arctic monkeys", "arctic",
        "arcade fire", "the national",
        "vampire weekend", "the strokes",
        "interpol", "bloc party",
        "kaiser chiefs", "razorlight",
        "the libertines", "jack white",
        "the white stripes", "white stripes",
        "the black keys", "black keys",
        "mumford and sons", "mumford & sons",
        "the xx ",
        "alt-j", "alt j",
        "bastille",
        "elbow ", "snow patrol",
        "biffy clyro", "frank turner",
        # ─ Added v4: Metallica song titles (album-rip files have no artist name) ─
        "enter sandman",
        "for whom the bell tolls",
        "the call of ktulu", "call of ktulu",
        "until it sleeps",
        "eye of the beholder",
        "dirty window",
        "of wolf and man",
        "hero of the day",
        "orion (instrumental)",
        "bad seed",
        # ─ Added v5: rock artists from INBOX analysis ─
        "pixies",                 # alt-rock (Where Is My Mind, Debaser)
        "the police", "police ",  # new wave/rock (Every Breath You Take)
        "deftones",               # alternative metal (My Own Summer)
        "yeah yeah yeahs",        # indie rock (Maps, Heads Will Roll)
        "cage the elephant",      # indie rock (Ain't No Rest for the Wicked)
        "the cranberries", "cranberries",  # Irish alternative (Zombie, Linger)
        "the cardigans", "cardigans",      # Swedish pop-rock (Lovefool)
        "the hives", "hives ",    # Swedish garage punk (Hate to Say I Told You So)
        "goo goo dolls",          # alt-rock (Iris, Slide)
        "avril lavigne",          # pop-punk / rock
        "drowning pool",          # post-grunge / nu-metal (Bodies)
        "godsmack",               # heavy rock / post-grunge
        "everclear",              # alt-rock / post-grunge (Father of Mine)
        "haim ",                  # pop rock trio — trailing space
        "jet ",                   # garage rock (Are You Gonna Be My Girl) — trailing space
        "the vines",              # garage rock / grunge revival
        "the coral",              # indie rock / psychedelia
        "the libertines",         # already in list — safety skip
        "razorlight",             # already in list — safety skip
        "graham coxon",           # Blur member solo
        "supergrass",             # Britpop
        "suede ",                 # Britpop — trailing space
        "elastica",               # Britpop
        "sleeper ",               # Britpop — trailing space
        "echobelly",              # Britpop
        "powder",                 # Britpop / indie
        "the breeders", "breeders",  # alternative rock (Cannonball)
        "throwing muses",         # alternative / post-punk
        "breeders",               # already added above — skip
        "the lemonheads",         # already in list — safety skip
        "guided by voices", "gbv ",  # indie rock / lo-fi
        "big star ",              # power pop — trailing space
        "the replacements",       # proto-alternative
        "husker du", "hüsker dü", # hardcore/post-punk
        "mission of burma",       # post-punk
        "television ",            # proto-punk / post-punk — trailing space
        "wire ",                  # post-punk — trailing space
        "siouxsie",               # Siouxsie and the Banshees
        "bauhaus ",               # post-punk / goth — trailing space
        "the sisters of mercy",   # goth rock
        "christian death",        # death rock / goth
        "type o negative",        # gothic metal / doom
        "my dying bride",         # gothic doom metal
        "anathema",               # gothic metal / atmospheric rock
        "paradise lost",          # gothic metal (already covers Song of Darkness etc.)
        "lacuna coil",            # gothic metal / alternative metal
        "nightwish",              # symphonic metal
        "within temptation",      # already in list — safety skip
        "epica ",                 # symphonic metal — trailing space
        "after forever",          # symphonic metal
        # ─ Genre terms ─
        "rock ", "metal ", "punk ",
        "grunge", "alternative", "indie rock",
        "hard rock", "heavy metal", "nu metal", "nu-metal",
        "post-rock", "prog rock", "progressive rock",
        "classic rock", "glam rock",
        "screamo", "post-hardcore", "metalcore",
        "emo ", "pop punk", "skate punk",
        # ─ Added v6 ─
        "talking heads",          # new wave / art rock (Psycho Killer, Burning Down the House)
        "tom tom club",           # Talking Heads offshoot (Genius of Love)
        "sonic youth",            # noise rock / indie (Teenage Riot, Kool Thing)
        "stereolab",              # post-rock / space rock (French Disko)
        "the stone roses", "stone roses",  # Madchester / indie rock (I Wanna Be Adored)
        "the shins", "shins ",    # indie rock (New Slang, Caring Is Creepy) — trailing space
        "queens of the stone age", "qotsa",  # stoner rock (No One Knows, Go with the Flow)
        "the jam ", "jam ",       # British punk/new wave (Town Called Malice) — trailing space
        "the b-52's", "the b-52s", "b-52s",  # new wave (Rock Lobster, Love Shack)
        "cocteau twins",          # dream pop / shoegaze (Pearly-Dewdrops' Drops)
        "frightened rabbit",      # Scottish indie rock (The Modern Leper)
        "mazzy star",             # dream pop / slowcore (Fade into You)
        "animal collective",      # psychedelic indie (My Girls, Summertime Clothes)
        "at the drive-in", "at the drive in",  # post-hardcore (One Armed Scissor)
        "the fall ",              # post-punk — trailing space (Mark E. Smith / The Fall)
        "pere ubu",               # art punk / avant-garde rock (Final Solution)
        "the undertones",         # punk rock (Teenage Kicks)
        "delta 5",                # post-punk / Leeds punk-funk (Mind Your Own Business)
        "the chameleons",         # post-punk / goth rock (Swamp Thing, Up the Down Escalator)
        "pinback ",               # indie rock duo — trailing space
        # ─ Added v7: rock artists & title keywords from INBOX analysis ─
        "millencolin",            # Swedish melodic punk/skate punk (No Cigar)
        "the la's", "the las ",   # British indie rock (There She Goes) — trailing space variant
        "xtc ",                   # English new wave — trailing space (Senses Working Overtime)
        "the revivalists",        # New Orleans indie rock (Wish I Knew You)
        "q lazzarus",             # American dance/rock (Goodbye Horses)
        "welcome to the jungle",  # Guns N' Roses — title keyword for remixes/covers
        # ─ Added v8: rock/country artists from full INBOX analysis ─
        "lenny kravitz",          # US rock/funk/soul (Are You Gonna Go My Way, Again, Fly Away)
        "republica ",             # 90s British rock-pop (Ready to Go) — also in classics, trailing space
        "luke combs",             # US country-pop (Fast Car, Beautiful Crazy, Hurricane)
        "zach bryan",             # US alt-country/folk (Something In The Orange, Heading South)
        "orville peck",           # Canadian alt-country/folk (Dead of Night, Drive Me Crazy)
        # ─ Added v9: rock artists from full INBOX analysis ─
        "zz top",                 # Texas blues-rock (Sharp Dressed Man, La Grange, Legs)
        "static-x",               # Industrial metal (Push It, Dirthouse)
        "the troggs",             # 60s garage rock (correct spelling; "the trogs" typo already exists)
        "troggs ",                # trailing space variant
        "brother dege",           # Alt-blues/folk-rock (Too Old to Die Young)
        "townes van zandt",       # Texas singer-songwriter (If I Needed You, Pancho and Lefty)
        # ─ Added v10: rock artists & song titles from INBOX analysis ─
        "stone cold crazy",       # Queen song title keyword (04 - Stone Cold Crazy.mp3 ×4 files)
        "mac demarco",            # Canadian indie rock (Chamber of Reflection, Salad Days)
        "mudvayne",               # Nu-metal (Not Falling, Happy?)
        "ministry ",              # Industrial metal (Thieves) — trailing space (house catches "ministry of sound" first)
        "the vaselines",          # Scottish indie-punk (You Think You're a Man)
        "the wedding present",    # UK indie rock (I'm Not Always So Stupid, Kennedy)
        "the feelies",            # US indie rock (Let's Go, Crazy Rhythms)
        "the only ones",          # Late 70s British rock (Another Girl Another Planet)
        "the raincoats",          # Post-punk feminist band (No One's Little Girl)
        "air miami",              # DC indie rock (Bubbling Over — Mark Robinson project)
        "electric eels",          # Ohio proto-punk (Jaguar Ride)
        "westernhagen",           # German rock icon (Es geht mir gut, Freiheit)
        "this mortal coil",       # 4AD collective (Song to the Siren, Blood)
        "a certain ratio",        # Manchester post-punk/funk (Shack Up, Flight)
        "the frights",            # San Diego surf-punk (Crust Bucket)
        "the bats ",              # New Zealand Flying Nun indie rock (Made Up in Blue) — trailing space
        # ─ Added v11: rock artists from INBOX analysis ─
        "josef k",                # Scottish post-punk (It's Kinda Funny, Chance Meeting on a Train)
        "red krayola",            # Texan avant-garde/experimental (Hurricane Fighter Plane) — alt spelling
        "red crayola",            # Texan avant-garde/experimental — original spelling variant
        "ned's atomic dustbin",   # UK alternative rock (Kill Your Television, Grey Cell Green)
        "neds atomic dustbin",    # UK alternative rock — no-apostrophe filename variant
        "dog's eye view",         # Alternative pop-rock (Everything Falls Apart)
        "no age ",                # LA noise-pop duo (Eraser, Teen Earth Magic) — trailing space prevents false positives
        "liliput",                # Swiss post-punk (originally Kleenex, 1978)
        "shudder to think",       # DC post-hardcore (Pebbles, Fear of Living Alone)
        "swirlies",               # Boston indie/shoegaze (Pancake, They Spent Their Wild Youthful Days)
        "marine girls",           # UK early-80s lo-fi indie (A Place in the Sun, Don't Come Back)
        "mark hollis",            # UK art-rock — Talk Talk frontman solo (The Colour of Spring)
        "go-betweens",            # Australian indie rock (Cattle and Cane, Streets of Your Town)
        "go betweens",            # Australian indie rock — no-hyphen filename variant
        "jimmie vaughan",         # Texas blues/rock (Boom Bapa Boom, Six Strings Down)
        "the gourds",             # Austin alt-country/rock (Gin and Juice cover, Promenade)
        # ─ Added v12: rock artists & song titles from INBOX analysis ─
        "alien ant farm",         # Nu-metal/alternative (Smooth Criminal cover, Movies)
        "a_certain_ratio",        # A Certain Ratio — underscore variant for filenames
        "a certain radio",        # Mislabeled filename variant of A Certain Ratio (Yo Yo Gi)
        "buttertones",            # LA garage/psychedelic rock (Creepy Crawl, Weird Out)
        "ghost ",                 # Swedish rock/metal band (Cirice, Square Hammer) — trailing space
        "the gist ",              # Belgian post-punk (This Wasn't Meant to Happen) — trailing space
        "jonathan davis",         # Korn vocalist solo (Basic Needs, What It Is)
        "the lively ones",        # 60s US surf rock (Surfer's Lament, Goofy Foot)
        "the marketts",           # 60s US garage/surf (Out of Limits, Batman Theme)
        "linkin par",             # Truncated Linkin Park filename variant
        "pacific gas & electric", # US blues-rock (Are You Ready, Wade in the Water)
        # ─ Added v13: rock artists from INBOX analysis ─
        "aliotta haynes",         # US folk-rock (Lake Shore Drive, 1971)
        "crosby stills",          # Crosby, Stills, Nash & Young — keyword catches all variants
        "the ex ",                # Dutch post-punk band — trailing space
    ]),

    # ── Pop & Commercial ──────────────────────────────────────────────────────
    ("pop", [
        # ─ Added from tracklist analysis ─
        "prince ",            # trailing space avoids "princess", "the prince of..."
        "kylie minogue",
        # ─ Added v4: missing pop artists ─
        "roxette",            # Swedish pop duo
        "omc ",               # NZ dance-pop "How Bizarre" — trailing space
        "smash mouth",        # "All Star" etc.
        "lany ",              # indie pop trio — trailing space
        "still woozy",
        "surfaces ",          # indie pop/surf — trailing space (avoids 'surfaces_' filenames)
        "electric guest",     # indie pop/funk
        "inna ",              # Romanian dance-pop — trailing space
        "morgan wallen",      # country-pop crossover
        "far east movement",  # "Like a G6" etc.
        "r.i.o.",             # Eurodance act
        "dj antoine",         # Swiss commercial dance
        "eyja ",              # Icelandic indie pop — trailing space
        "her's ",             # indie pop duo — trailing space
        "sports ",            # indie pop band — trailing space
        "feathers ",          # indie pop — trailing space
        "kirk franklin",      # gospel crossover pop
        "dcappella ",         # pop a cappella group — trailing space (already in hiphop as dcappella without space)
        "demi lovato",
        "gwen stefani",
        "p!nk",               # literal "p!nk" in filenames
        "ke$ha",              # literal "ke$ha" in filenames
        "kesha",              # also "kesha" without dollar sign
        "jamiroquai",
        # ─ Mega-stars ─
        "taylor swift", "beyonce", "beyoncé",
        "lady gaga", "katy perry", "rihanna",
        "britney spears", "christina aguilera",
        "michael jackson", "madonna",
        "justin bieber", "ariana grande",
        "selena gomez", "miley cyrus",
        "dua lipa", "billie eilish",
        "harry styles", "one direction",
        "justin timberlake", "timberlake",
        # ─ Ed Sheeran / Sam Smith generation ─
        "ed sheeran", "sam smith", "adele ",
        "lewis capaldi", "niall horan",
        "shawn mendes", "camila cabello",
        "halsey", "lana del rey",
        "lorde", "troye sivan",
        "james arthur", "olly murs",
        "the script", "kodaline",
        "james bay", "tom odell",
        "charlie puth", "meghan trainor",
        "jason derulo", "sia ", "bebe rexha",
        # ─ 90s pop ─
        "nsync", "backstreet boys", "spice girls",
        "nelly furtado", "pink ",
        "fergie ", "black eyed peas",
        "maroon 5", "maroon5", "adam levine",
        "boy bands", "westlife", "blue ",
        "take that", "boyzone",
        "atomic kitten", "girls aloud",
        "sugababes", "liberty x",
        "pussycat dolls", "s club",
        "5ive", "ace of base", "abba ",
        "aqua ", "vengaboys", "a-ha ",
        "rob rob", "savage garden",
        "hanson ", "4 non blondes",
        "alanis morissette", "sheryl crow",
        "natalie imbruglia", "dido ",
        "norah jones", "katie melua",
        # ─ 2000s pop ─
        "kesha ", "katy perry",
        "kelly clarkson",
        "alicia keys",
        "fergie", "black eyed peas",
        "taio cruz", "jason derulo",
        "ne-yo",
        "pixie lott", "leona lewis",
        "n-dubz", "tinchy stryder",
        "chipmunk", "labrinth",
        "cher lloyd", "little mix",
        "one direction",
        "5 seconds of summer", "5sos",
        # ─ Current pop ─
        "olivia rodrigo", "sabrina carpenter",
        "gracie abrams", "conan gray",
        "rex orange county", "clairo",
        "girl in red", "phoebe bridgers",
        "beabadoobee", "powfu",
        "the chainsmokers", "chainsmokers",
        "zara larsson", "tove lo",
        "ellie goulding", "rita ora",
        "jess glynne", "ella henderson",
        "paloma faith", "jessie j",
        "carly rae jepsen", "neon trees",
        "walk the moon", "fun ",
        "owl city", "passion pit",
        "grouplove", "train ",
        "mike posner", "jason mraz",
        "john mayer", "james morrison",
        "james blunt", "daniel bedingfield",
        "daniel powter",
        # ─ Michael Bublé / adult contemporary ─
        "michael buble", "michael bublé",
        "jamie cullum", "diana krall",
        "josh groban", "gavin degraw",
        "john legend", "aloe blacc",
        "robin thicke",
        "sara bareilles", "ingrid michaelson",
        "colbie caillat", "jack johnson",
        "ben harper", "ben folds",
        "mat kearney",
        # ─ Imagine Dragons / modern pop rock ─
        "imagine dragons", "onerepublic", "one republic",
        "switchfoot", "lifehouse",
        "matchbox twenty",
        # ─ Eurodance / eurotrance crossover pop ─
        "haddaway", "snap ",
        "la bouche", "real mccoy", "corona ",
        "culture beat", "two unlimited",
        "mr president", "lou bega",
        "whigfield", "alexia",
        "twenty 4 seven",
        # ─ International pop ─
        "robyn", "loreen", "cornelia jakobs",
        "amy winehouse", "lily allen",
        "florence", "elbow ",
        "paolo nutini", "jake bugg",
        "james morrison", "scouting for girls",
        # ─ Pop genre terms ─
        "pop hit", "chart",
        "bubblegum", "teen pop",
        "electropop", "synthpop", "synth pop",
        "indie pop", "chamber pop",
        "adult contemporary",
        "idol ", "x factor",
        # ─ Added v5: pop artists from INBOX analysis ─
        "gotye ",                 # "Somebody That I Used to Know" — trailing space
        "george michael",         # Wham! / solo pop
        "dnce ",                  # "Cake by the Ocean" — trailing space
        "tones and i", "tones and i",  # "Dance Monkey"
        "years & years", "years and years",  # Olly Alexander's synth-pop project
        "hailee steinfeld",       # pop / acting crossover
        "nico & vinz", "nico and vinz",  # "Am I Wrong"
        "joji ",                  # lo-fi R&B/pop — trailing space
        "jvke ",                  # piano pop — trailing space
        "jawsh 685",              # "Savage Love" co-artist
        "jason derulo",           # already listed — safety skip
        "josh golden",            # indie pop
        "griff ",                 # UK pop — trailing space
        "rina sawayama",          # J-British pop / alt
        "caroline polachek",      # indie pop / experimental pop
        "magdalena bay",          # synth pop duo
        "wet leg",                # indie pop / post-punk
        "beabadoobee",            # already listed — safety skip
        "maisie peters",          # pop songwriter
        "raye ",                  # UK R&B/pop — trailing space
        "emma-louise",            # indie pop
        "dagny ",                 # Norwegian pop — trailing space
        "astrid s",               # Norwegian pop
        "aurora ",                # Norwegian art-pop — trailing space
        "sigrid",                 # Norwegian pop
        "dagny",                  # already added above — skip
        "zara larsson",           # already listed — safety skip
        "tove lo",                # already listed — safety skip
        "icona pop",              # Swedish electropop ("I Love It")
        "robyn",                  # already listed in International pop — skip
        "loreen",                 # already listed — skip
        "annie lennox",           # Eurythmics / solo pop
        "sinead o'connor", "sinead o connor",  # Irish pop/rock
        "dolores o'riordan",      # Cranberries frontwoman solo
        "k.d. lang", "kd lang",   # Canadian pop/country crossover
        "melissa etheridge",      # rock/pop
        "shania twain",           # country-pop crossover
        "faith hill",             # country-pop
        "leann rimes", "leann rimes",  # country-pop
        "jessica simpson",        # pop/country
        "hilary duff",            # teen pop
        "ashley tisdale",         # pop/Disney
        "vanessa hudgens",        # pop/Disney
        "jonas brothers",         # pop/Disney
        "selena gomez",           # already listed — safety skip
        "miley cyrus",            # already listed — safety skip
        # ─ Added v6: pop artists from INBOX analysis ─
        "mariah carey",           # pop/R&B diva (All I Want for Christmas, Hero)
        "janet jackson",          # pop/R&B (Nasty, Together Again, Control)
        "bruno mars",             # pop/R&B/funk (Uptown Funk, Just the Way You Are)
        "empire of the sun",      # Australian electropop (Walking on a Dream)
        "mgmt ",                  # psychedelic pop/new wave — trailing space (Time to Pretend)
        "blood orange",           # Dev Hynes — indie R&B/art-pop (Chamakay)
        "chet faker",             # Australian R&B/electronic (No Diggity cover) — also "nick murphy"
        "nick murphy",            # Chet Faker real name
        "of monsters and men",    # Icelandic indie folk-pop (Little Talks, Mountain Sound)
        "the neighbourhood", "nbhd ",  # California alt-pop/rock (Sweater Weather) — trailing space
        "vance joy",              # Australian indie pop (Riptide)
        "maggie rogers",          # indie pop (Alaska, Light On)
        "hozier",                 # Irish indie/blues-pop (Take Me to Church)
        "jorja smith",            # UK R&B/soul-pop (Blue Lights, Falling or Flying)
        "sigala ",                # UK dance-pop producer — trailing space (Easy Love)
        "stephen sanchez",        # indie pop (Until I Found You)
        "nicky youre",            # indie pop (Sunroof)
        # ─ Added v7: pop artists from INBOX analysis ─
        "lake street dive",       # Boston indie pop/jazz-pop (Bad Self Portraits)
        "todrick hall",           # pop/R&B performer (Nails, Hair, Hips, Heels)
        "weyes blood",            # California art-pop (Andromeda, Movies)
        "kacey musgraves",        # country-pop/psychedelic pop (Rainbow, Slow Burn)
        "solange ",               # R&B/art-pop — trailing space (Cranes in the Sky, Don't Touch My Hair)
        "cautious clay",          # indie R&B/jazz-pop (Cold War)
        "greatest showman",       # 2017 musical film soundtrack keyword
        "banks - ",               # Banks (Jillian Rose Banks) — indie R&B/alt-pop; "banks - " avoids false hits
        "whigfeild",              # misspelling variant of Whigfield in some filenames (Saturday Night)
        "d4vd ",                  # indie pop/alt-R&B — trailing space (Here With Me, Romantic Homicide)
        # ─ Added v8: pop/R&B artists from full INBOX analysis ─
        "ciara ",                 # US R&B/pop — trailing space (Level Up, Goodies, 1, 2 Step)
        "fifth harmony",          # US pop girl group (Work from Home, Worth It)
        "jennifer paige",         # 90s pop (Crush)
        "nine days",              # 90s alt-pop (Absolutely - Story of a Girl)
        "tal bachman",            # 90s pop (She's So High)
        "ylvis",                  # Norwegian comedy/viral pop (The Fox - What Does the Fox Say?)
        "t.a.t.u.", "tatu ",      # Russian pop duo (All The Things She Said) — trailing space on tatu
        "michael kiwanuka",       # British indie-folk/soul (Home Again, Black Man in a White World)
        "mahalia ",               # UK indie R&B (Simmer ft. Burna Boy) — trailing space
        "sault ",                 # UK neo-soul/funk collective (Wildfires) — trailing space
        "devendra banhart",       # Venezuelan-American indie folk (Carmensita, Lover)
        # ─ Added v9: pop artists from full INBOX analysis ─
        "the wanted",             # UK pop boy band (Glad You Came, Chasing The Sun)
        "willow smith",           # US pop (Whip My Hair, Wait a Minute)
        "ruth b.",                # Canadian indie-pop (Lost Boy, Slow Fade)
        "the marias", "the marías",  # Indie dream-pop (I Don't Know You) — second variant for accented á in filenames
        "timeflies",              # Canadian pop duo (Nobody Has To Know, All The Way)
        "the sundays",            # 90s British indie-pop (Wild Horses, Here's Where the Story Ends)
        "rascal flatts",          # US country-pop (Bless the Broken Road, My Wish)
        "the band perry",         # US country-pop (If I Die Young, Done)
        "jesse mccartney",        # US pop (Leavin', Beautiful Soul)
        "lunchmoney lewis",       # US pop (Bills, Whoa)
        "paula cole",             # US pop/folk (Where Have All the Cowboys Gone, I Don't Want to Wait)
        "nicole scherzinger",     # UK pop (Wet, Don't Hold Your Breath, Right There)
        "kelis ",                 # US R&B/pop (Milkshake, Lil Star) — trailing space
        "bran van 3000",          # Canadian alternative pop (Drinking in L.A., Afrodizzia)
        "midlake",                # US indie folk-rock (Roscoe, Young Bride)
        # ─ Added v10: pop artists & song titles from INBOX analysis ─
        "kim petras",             # German pop (Heart to Break, 1,2,3 dayz up feat. SOPHIE)
        "ava max",                # Albanian-American pop (Sweet but Psycho, Slow Dance)
        "andra day",              # US R&B/soul (Rise Up, Woman)
        "shivaree",               # US art-pop (Goodnight Moon)
        "dean and britta",        # US indie pop duo (Friday I'm in Love cover)
        "david gray",             # British folk-pop (Sail Away, Babylon)
        "grouper ",               # US dream-pop/ambient (Heavy Water) — trailing space
        "mapei ",                 # Swedish pop singer (Don't Wait) — trailing space
        "broods ",                # New Zealand electro-pop duo (Bridges) — trailing space
        "petite_meller",          # French indie-pop — underscore variant for filenames
        "petite meller",          # French indie-pop (Barbaric, Baby Love)
        "aj mitchell",            # US pop (Slow Dance ft. Ava Max)
        "24k magic",              # Bruno Mars song title keyword (24K Magic.mp3 has no artist in filename)
        "unrest ",                # DC indie-pop (Isabel) — trailing space
        # ─ Added v11: pop artists from INBOX analysis ─
        "april march",            # US/French yé-yé singer (Chick Habit, Roller Girl)
        "ashnikko",               # UK pop-alternative (Daisy, Stupid)
        "caroline rose",          # US indie pop (Soul No. 5, Do It Without Me)
        "the 6ths",               # Indie pop supergroup (Stephin Merritt/Magnetic Fields project)
        "lewis ofman",            # French pop/electronic (Vamo, Savoir Faire)
        "jp saxe",                # Canadian indie-pop (If the World Was Ending ft. Julia Michaels)
        "noah cyrus",             # US pop (Make Me (Cry), July ft. Leon Bridges)
        "gavin james",            # Irish folk-pop (Nervous, Always)
        "neon jungle",            # UK girl group (Braveheart, Welcome to the Jungle)
        "morly",                  # US indie folk-pop (Until the Day is Done, Atlas Hands)
        "b*witched", "b witched", # Irish pop group (C'est La Vie, Rollercoaster) — two filename variants
        "banes world",            # Australian alternative pop (Bruise, Peach Tree)
        "dennis lloyd",           # Israeli-born English-language pop (Nevermind, Plead) — classified by genre not nationality
        # ─ Added v12: pop artists from INBOX analysis ─
        "b* witched",             # Third filename variant — asterisk + space (B* Witched - Blame It On The Weatherman)
        "idina menzel",           # US Broadway/pop (Let It Go, Defying Gravity)
        "paenda",                 # Austrian singer-songwriter (Limits, Young)
        "sigala",                 # UK pop/dance producer (Easy Love, Give Me Your Love)
        "tessa rose jackson",     # Dutch pop/soul (Do It Now, Waiting)
        "sure sure",              # US indie pop (More Than OK, Roads)
        "the wind and the wave",  # US folk-pop duo (Happiness is Not a Place, Dog Days Are Over cover)
        "thirdstory",             # US R&B trio (Worth It, Foolish)
        "wild child ",            # Austin indie folk-pop (Crazy Bird, Pillow Talk) — trailing space
        # ─ Added v13: pop artists & song titles from INBOX analysis ─
        "i gotta feeling",        # Black Eyed Peas title keyword
        "geri halliwell",         # UK pop (It's Raining Men, Mi Chico Latino)
        "dan balan",              # Moldovan pop (Crazy Loop, Chica Bomb)
        "gilbert montagne",       # French pop singer (On Va S'aimer)
        "kimberose",              # French soul/pop (Chapter One)
        "chesney hawkes",         # UK pop (I Am the One and Only)
        "leslie grace",           # Dominican-American pop/Latin crossover
        "ariana and the rose",    # US pop/electronic artist
        u"m\u00f6we",            # Austrian pop/dance duo (Lovers)
        "mowe ",                  # ASCII variant — trailing space
        "us the duo",             # US pop duo (Missin You Like Crazy, No Matter Where You Are)
    ]),

    # ── Classics & Oldies ─────────────────────────────────────────────────────
    ("classics", [
        # ─ Added from tracklist analysis ─
        "roy orbison",
        # ─ Added v4: missing classics artists ─
        "paul simon",         # solo and S&G
        "parliament",         # P-Funk / George Clinton
        "paul revere",        # Paul Revere & The Raiders — garage/60s rock
        "mamas & the papas", "mamas and the papas", "the mamas",
        "sha-na-na", "sha na na",
        "the hollies", "hollies",
        "john mellencamp", "john cougar",
        "orchestral manoeuvres", "omd ",  # trailing space on omd
        "orange juice",       # Scottish post-punk / new wave 80s
        "johnny cash",
        "cat stevens",
        "grateful dead",
        "the zombies",
        "survivor ",          # "Eye of the Tiger" etc.
        "bobby womack",
        "isaac hayes",
        "big star",
        "earth, wind",        # catches "Earth, Wind & Fire" comma variant
        "lou reed",
        "dire straits",
        "lynyrd skynyrd",
        "whitney houston",
        # ─ Rat Pack / jazz standards ─
        "frank sinatra", "sinatra", "dean martin",
        "sammy davis", "nat king cole", "nat cole",
        "tony bennett", "perry como",
        "bobby darin", "doris day",
        "miles davis", "john coltrane",
        "dave brubeck", "thelonious monk",
        "billie holiday", "louis armstrong",
        "ella fitzgerald", "sarah vaughan",
        "nina simone", "etta james",
        # ─ Blues / soul roots ─
        "muddy waters", "bb king", "b.b. king",
        "john lee hooker", "robert johnson",
        "howlin wolf", "sonny boy williamson",
        "chuck berry", "little richard",
        "buddy holly", "everly brothers",
        "bill haley", "fats domino",
        "jerry lee lewis", "bo diddley",
        "wilson pickett", "solomon burke",
        "al green", "bill withers",
        "otis redding", "sam cooke",
        # ─ Motown / soul ─
        "marvin gaye", "stevie wonder",
        "aretha franklin", "ray charles",
        "james brown", "diana ross",
        "the temptations", "four tops",
        "supremes", "motown",
        "gladys knight", "lionel richie",
        "the commodores", "kool and the gang",
        "earth wind and fire", "earth wind & fire",
        "chic ", "sister sledge",
        "donna summer",
        # ─ Classic pop / rock ─
        "elvis presley", "elvis ",
        "the beatles", "beatles", "rolling stones",
        "bob dylan", "simon & garfunkel",
        "fleetwood mac", "the eagles", "eagles ",
        "creedence clearwater", "ccr ",
        "jimi hendrix", "janis joplin",
        "neil young", "tom petty",
        "bruce springsteen", "springsteen",
        "cher ", "tina turner",
        "bette midler", "celine dion",
        "the beach boys", "beach boys",
        "the byrds", "the who",
        "the kinks", "the animals",
        "dusty springfield", "petula clark",
        "shirley bassey", "tom jones",
        "cliff richard", "lulu ",
        # ─ Disco era ─
        "bee gees", "stayin alive",
        "boney m", "village people",
        "nile rodgers", "abba ",
        "gloria gaynor",
        "jacksons", "jackson 5",
        # ─ 80s pop classics ─
        "a-ha ", "eurythmics",
        "cyndi lauper", "pat benatar",
        "blondie", "heart ",
        "foreigner", "journey ",
        "toto ", "kansas ",
        "supertramp", "elton john",
        "david bowie", "bowie",
        "rod stewart",
        "billy joel",
        "carole king",
        "barbra streisand",
        "engelbert humperdinck",
        # ─ Added v5: classics artists from INBOX analysis ─
        "ben e king", "ben e. king", "ben e  king",  # "Stand by Me" — double-space filename variant
        "donovan ",               # 60s folk/psychedelia (Mellow Yellow) — trailing space
        "the ronettes",           # 60s girl group (Be My Baby)
        "the shirelles",          # 60s girl group (Will You Love Me Tomorrow)
        "katrina & the waves", "katrina and the waves",  # "Walking on Sunshine" — 80s
        "tommy roe",              # 60s bubblegum pop (Dizzy, Sheila)
        "bonnie tyler",           # 80s pop (Total Eclipse of the Heart)
        "irene cara",             # 80s pop (What a Feeling — Flashdance)
        "freda payne",            # 70s soul (Band of Gold)
        "the five stairsteps",    # soul (O-o-h Child)
        "brenda lee",             # rockabilly / 60s pop
        "paul anka",              # teen idol pop 60s (Put Your Head on My Shoulder)
        "frankie valli", "four seasons",  # 60s doo-wop / pop
        "the four seasons",       # full name variant
        "dion and the belmonts", "dion ", # 60s doo-wop — trailing space on dion
        "joey dee",               # 60s Twist era (Peppermint Twist)
        "chubby checker",         # Twist era (The Twist)
        "sam the sham",           # 60s garage rock (Wooly Bully)
        "the trogs", "trogs ",    # 60s garage rock (Wild Thing) — trailing space
        "gary puckett",           # 60s pop
        "lou christie",           # 60s pop (Lightnin' Strikes)
        "bobby vee",              # 60s teen pop (Take Good Care of My Baby)
        "terry stafford",         # 60s pop (Suspicion)
        "gene pitney",            # 60s pop (Town Without Pity)
        "bobby goldsboro",        # 60s/70s pop (Honey)
        "glen campbell",          # country-pop crossover (Rhinestone Cowboy)
        "jim croce",              # 70s singer-songwriter (Bad, Bad Leroy Brown)
        "harry chapin",           # 70s singer-songwriter (Cat's in the Cradle)
        "gilbert o'sullivan",     # 70s pop (Alone Again Naturally)
        "hot chocolate",          # 70s/80s pop (You Sexy Thing)
        "harold melvin",          # Philly soul (If You Don't Know Me by Now)
        "bluenotes",              # Harold Melvin's group
        "blue notes",             # name variant
        "the chi-lites",          # 70s soul (Have You Seen Her)
        "the stylistics",         # Philly soul (You Make Me Feel Brand New)
        "the delfonics",          # Philly soul (La-La)
        "the intruders",          # Philly soul (Cowboys to Girls)
        "the spinners",           # Philly soul (Could It Be I'm Falling in Love)
        "the o'jays",             # Philly soul (Love Train)
        "harold and maude",       # 70s soundtrack
        "boz scaggs",             # 70s soft rock/R&B (Lido Shuffle)
        "gerry rafferty",         # 70s pop-rock (Baker Street)
        "christopher cross",      # 70s/80s soft rock (Sailing)
        "toto ",                  # already in list — trailing space safety add
        "air supply",             # 80s soft rock (All Out of Love)
        "chicago ",               # rock/pop band — trailing space (avoids 'chicago house')
        "10cc ",                  # 70s art-rock/pop — trailing space
        "electric light orchestra", "elo ",  # 70s rock/pop — trailing space on elo
        # ─ Added v6: classics artists from INBOX analysis ─
        "don mclean",             # 70s folk-rock (American Pie, Vincent)
        "dolly parton",           # country-pop classic (Jolene, 9 to 5)
        "kenny rogers",           # country-pop (The Gambler, Islands in the Stream)
        "neil diamond",           # pop/rock classic (Sweet Caroline, Cracklin' Rosie)
        "emmylou harris",         # country/folk classic (Boulder to Birmingham)
        "sly & the family stone", "sly and the family stone",  # funk/soul (Everyday People)
        "sly stone",              # name variant
        "dick dale",              # surf guitar king (Misirlou)
        "bronski beat",           # 80s synth-pop (Smalltown Boy)
        "the pointer sisters", "pointer sisters",  # 80s pop/R&B (I'm So Excited, Jump)
        "belinda carlisle",       # 80s pop (Heaven Is a Place on Earth, Mad About You)
        "tracy chapman",          # 80s/90s folk-pop (Fast Car, Give Me One Reason)
        "seal ",                  # 90s pop/soul — trailing space (Kiss from a Rose, Crazy)
        "des'ree", "desree",      # 90s soul-pop (You Gotta Be, Life)
        "rednex ",                # 90s eurodance — trailing space (Cotton Eye Joe)
        "steppenwolf",            # 60s/70s rock (Born to Be Wild, Magic Carpet Ride)
        "ram jam",                # 70s rock (Black Betty)
        "link wray",              # 50s/60s rock guitar (Rumble)
        "the knack",              # 70s/80s power pop (My Sharona)
        "tommy james",            # 60s/70s pop (Crimson and Clover, Mony Mony)
        "stealers wheel",         # 70s pop-rock (Stuck in the Middle with You)
        "the traveling wilburys", "traveling wilburys",  # supergroup (Handle with Care)
        "righteous brothers",     # 60s blue-eyed soul (You've Lost That Lovin' Feelin')
        "kim wilde",              # 80s pop (Kids in America, You Keep Me Hangin' On)
        "corey hart",             # 80s pop (Sunglasses at Night, Never Surrender)
        "kool & the gang",        # variant without "and" — safety add (Celebration, Get Down on It)
        # ─ Added v7: classics artists from INBOX analysis ─
        "hamilton ",              # Lin-Manuel Miranda musical soundtrack — trailing space
        "john travolta",          # Saturday Night Fever / Grease actor/singer
        "olivia newton-john", "olivia newton john",  # Grease / Physical
        "jefferson airplane",     # 60s psychedelic rock (Somebody to Love, White Rabbit)
        "inner circle",           # Jamaican reggae (Bad Boys, Sweat)
        "kc & the sunshine band", "kc and the sunshine band",  # 70s disco (That's the Way)
        "huey lewis",             # 80s rock/pop (The Power of Love, Hip to Be Square)
        "robbie williams",        # 90s/00s pop (Angels, Feel, Rock DJ)
        "wilson phillips",        # 90s pop harmony trio (Hold On, Release Me)
        "right said fred",        # 90s novelty pop (I'm Too Sexy)
        "reel 2 real",            # 90s dancehall/house (I Like to Move It)
        "barenaked ladies",       # Canadian alt-pop/rock (One Week, If I Had $1000000)
        "wet wet wet",            # 80s/90s Scottish pop (Love Is All Around)
        "bloodhound gang",        # 90s/00s novelty rock (The Bad Touch, Fire Water Burn)
        "chaka khan",             # 70s/80s soul/R&B diva (Ain't Nobody, I Feel for You)
        "minnie riperton",        # 70s soul (Lovin' You)
        "rick astley",            # 80s pop (Never Gonna Give You Up)
        "david hasselhoff",       # 80s/90s pop (Looking for Freedom)
        "ennio morricone",        # film composer classic scores (The Good The Bad The Ugly)
        # ─ Added v8: classics artists from full INBOX analysis ─
        "genesis ",               # British prog/pop (I Can't Dance, Invisible Touch) — trailing space
        "wham ",                  # 80s British pop duo (Wake Me Up, Freedom) — trailing space
        "t. rex", "t.rex",        # British glam rock (Get It On, Bang A Gong, 20th Century Boy)
        "baha men",               # Bahamian junkanoo-pop (Who Let the Dogs Out)
        "ottawan",                # French Caribbean pop (Hands Up, D.I.S.C.O.)
        "kenny loggins",          # US soft rock/pop (Footloose, Danger Zone, I'm Alright)
        "the carpenters", "carpenters ",  # 70s pop duo (Top of the World, Close to You)
        "the archies",            # 60s bubblegum pop (Sugar Sugar)
        "booker t",               # Booker T & the MGs — 60s soul/R&B (Green Onions)
        "buffalo springfield",    # 60s folk-rock (For What It's Worth, Mr. Soul)
        "george baker selection", "george baker ",  # Dutch pop (Little Green Bag)
        "baccara ",               # Spanish disco-pop (Yes Sir I Can Boogie) — trailing space
        "redbone ",               # Native American rock (Come and Get Your Love) — trailing space
        "urge overkill",          # 90s alt-rock (Girl You'll Be a Woman Soon - Pulp Fiction)
        "snap! ", "snap ",        # German Eurodance (Rhythm is a Dancer, I've Got the Power)
        "ricky nelson",           # 50s/60s rockabilly-pop (Lonesome Town, Hello Mary Lou)
        "michael sembello",       # 80s pop (Maniac - Flashdance)
        "yazoo ",                 # 80s British synth-pop duo (Only You, Don't Go) — trailing space
        "starship ",              # 80s rock/pop (Nothing's Gonna Stop Us Now) — trailing space
        "the guess who",          # Canadian classic rock (American Woman, These Eyes)
        "shuggie otis",           # 70s soul/funk (Strawberry Letter 23, Inspiration Information)
        "statler brothers",       # Country/classic (Flowers on the Wall)
        "tag team",               # 90s hip-hop/novelty (Whoomp There It Is)
        "republica ",             # 90s British rock-pop (Ready to Go, Drop Dead Gorgeous) — trailing space
        "wham! ",                 # alternate spelling with exclamation mark
        # ─ Added v9: classics artists from full INBOX analysis ─
        "anita ward",             # Disco (Ring My Bell, 1979)
        "robert palmer",          # 80s rock/pop (Addicted to Love, Simply Irresistible)
        "rupaul ",                # 90s drag pop (Supermodel, Glamazon) — trailing space
        "barbie girl",            # Title keyword for Aqua track (aqua keyword uses trailing space, won't catch this)
        "the human beinz",        # 60s garage (Nobody But Me)
        "human beinz",            # alternate without "the"
        "voulez-vous",            # ABBA title keyword — "abba " trailing-space won't catch "Voulez-Vous ABBA.wav"
        "tim buckley",            # 60s folk-rock (Song to the Siren, Buzzin' Fly)
        "debarge",                # 80s R&B/pop (Rhythm of the Night, I Like It)
        "de barge",               # spacing variant
        "rhythm of the night",    # DeBarge title keyword
        "roy ayers",              # 70s jazz-funk (Everybody Loves the Sunshine, Exotic Dance)
        "the mavericks",          # 90s country-pop (Dance the Night Away, Foolish Heart)
        "berlin ",                # 80s synth-pop band (Take My Breath Away, Metro) — trailing space
        "gala ",                  # 90s eurodance (Freed From Desire, Come Into My Life) — trailing space
        "america ",               # 70s folk-rock band (A Horse with No Name, Ventura Highway) — trailing space
        "joe cocker",             # 60s–90s rock/soul (With a Little Help from My Friends, Up Where We Belong)
        "the monkees",            # 60s pop (I'm a Believer, Last Train to Clarksville)
        "monkees ",               # without "the" — trailing space
        "harry nilsson",          # 70s pop (Coconut, Everybody's Talkin', Without You)
        "jeff buckley",           # 90s folk-rock (Hallelujah, Lover You Should've Come Over)
        "kris kross",             # 90s hip-hop (Jump, Warm It Up) — placed here with era peers
        "fastball ",              # 90s alt-rock (The Way, Out of My Head) — trailing space
        "goldfinger ",            # Ska-punk band (99 Red Balloons, Here in Your Bedroom) — trailing space; not Bond theme
        # ─ Added v10: classics artists from INBOX analysis ─
        "dexys midnight runners", # British new wave/soul (Come On Eileen, Geno)
        "john prine",             # US folk/country singer-songwriter (Fish & Whistle)
        "karen dalton",           # 60s US folk singer (Katie Cruel, Something on Your Mind)
        "dr. buzzard",            # 70s disco (Dr. Buzzard's Original Savannah Band — Sunshowers)
        "brothers johnson",       # 70s funk/soul (Strawberry Letter 23, Stomp)
        "the marvelettes",        # 60s Motown girl group (Please Mr. Postman)
        "quincy jones",           # Jazz/soul legend (Ironside theme, Soul Bossa Nova)
        # ─ Added v11: classics artists from INBOX analysis ─
        "gwen mccrae",            # US soul/R&B (Rockin' Chair, 90% of Me Is You)
        "charlie feathers",       # US rockabilly pioneer (One Hand Loose, I Forgot to Remember to Forget)
        "dee clark",              # US R&B (Raindrops, Hey Little Girl)
        "bruce channel",          # US pop (Hey! Baby — harmonica by Delbert McClinton)
        "joe tex",                # US soul/funk (Ain't Gonna Bump No More, Hold What You've Got)
        "the robins",             # US doo-wop/R&B — precursor to The Coasters (Smokey Joe's Cafe)
        # ─ Added v12: classics artists from INBOX analysis ─
        "black lace",             # UK novelty/pop (Agadoo, 1983; Do the Conga)
        "baccara",                # Spanish pop duo (Yes Sir I Can Boogie, 1977)
        "stockard channing",      # Actress/singer — Grease (Look at Me, I'm Sandra Dee, 1978)
        # ─ Added v13: classics artists from INBOX analysis ─
        "daddy cool",             # Australian disco/pop (Eagle Rock, 1971)
        "carrie lucas",           # US disco/soul (Dance With You, 1979)
        "little nell",            # Australian actress/singer (Rocky Horror — Columbia)
        "time warp",              # Rocky Horror Picture Show — title keyword
        "love hangover",          # Diana Ross title keyword (1976 disco classic)
        "woody thorne",           # UK disco/funk producer
        # ─ Classic genre terms ─
        "classic", "oldies", "golden hit", "evergreen",
        "60s ", "70s ", "80s ",
        "original recording", "remastered",
        "greatest hits", "best of",
        "the definitive", "collection",
        "golden years", "retro ",
        "swing ", "big band", "jazz standard",
    ]),

    # ── World & Ecstatic ──────────────────────────────────────────────────────
    ("world", [
        # ─ Added from tracklist analysis ─
        "bird tribe",         # ecstatic dance, Bay Area
        # ─ Added v4: missing world artists ─
        "omar souleyman",     # Syrian dabke / electronic world
        "eduardo falú", "eduardo falú",   # Argentine folk/guitar
        "la compagnie créole", "la compagnie creole",  # Antillean zouk/world
        "andreas gabalier",   # Austrian folk-pop (Volksrock)
        "akriza",             # ecstatic dance, Northern California
        "banyan",             # ecstatic dance / world fusion
        "prem joshua",        # Indian fusion / ecstatic
        "thornato",           # global bass / ecstatic
        "sara tavares",       # Cape Verdean-Portuguese world music
        # ─ Ecstatic dance / ceremony ─
        "tahum", "tahüm",     # Tyler Winick, world/ambient — NFC fix handles macOS NFD
        "equanimous",
        "mantra", "kirtan",
        "ecstatic dance", "ecstatic",
        "tribal", "shamanic",
        "meditation", "ceremonial",
        "sacred", "devotional",
        "eye of the forest", "east forest",
        "this is flow",
        # ─ Arabic / Middle Eastern ─
        "fairouz", "fayrouz",
        "umm kulthum", "om kalthoum",
        "amr diab", "nancy ajram",
        "elissa", "haifa wehbe",
        "tamer hosny", "arab music",
        "arabic", "arab ", "oud ", "tabla ",
        "turkish", "greek laika",
        # ─ African ─
        "fela kuti", "fela ",
        "youssou n'dour", "salif keita",
        "miriam makeba", "hugh masekela",
        "baaba maal", "ali farka toure",
        "afrobeats", "afropop",
        "amapiano", "gqom",
        "buena vista", "oumou sangare",
        # ─ Indian / Bollywood ─
        "bollywood", "bhangra",
        "ar rahman", "a.r. rahman",
        "dj aqeel", "dj chetas",
        "punjabi mc", "panjabi mc",
        # ─ Reggae / Jamaica ─
        "reggae", "dancehall", "ska ",
        "bob marley", "marley",
        "peter tosh", "bunny wailer",
        "jimmy cliff", "toots",
        "burning spear", "culture ",
        "shabba ranks", "buju banton",
        "beenie man", "sean paul",
        "shaggy", "vybz kartel",
        # ─ Brazilian / Latin world ─
        "bossa nova", "samba ",
        "caetano veloso", "gilberto gil",
        "anitta",
        # ─ Balkan / European folk ─
        "goran bregovic", "shantel",
        "boban markovic", "balkan",
        "celtic", "irish folk",
        "flamenco", "tango ",
        # ─ Added v5: world / global artists from INBOX analysis ─
        "yemen blues",            # Israeli-Yemenite jazz/world fusion
        "ester rada",             # Israeli-Ethiopian soul/world
        "gili yalo",              # Israeli-Ethiopian jazz/world
        "voilaaa",                # French Afro-funk / world bass (Bruno Hovart)
        "batukadeiras",           # Cape Verdean batucadeiras
        "aurelio",                # Garifuna singer-songwriter (Honduras/Belize)
        "fatoumata diawara",      # Malian singer-songwriter
        "habib koite",            # Malian guitarist
        "baaba maal",             # already in list — safety skip
        "amadou & mariam", "amadou and mariam",  # Malian blind duo
        "bombino",                # Tuareg guitar (Niger)
        "tinariwen",              # Tuareg desert blues (Mali)
        "bassekou kouyate",       # Malian ngoni master
        "toumani diabate",        # Malian kora master
        "ballaké sissoko", "ballake sissoko",  # Malian kora
        "rokia traore", "rokia traoré",  # Malian singer
        "salif keita",            # already in list — safety skip
        "ismael lo",              # Senegalese singer (Dibi Dibi Rek)
        "aby ngana diop",         # Senegalese mbalax singer
        "nusrat fateh ali khan",  # Pakistani qawwali legend
        "abida parveen",          # Pakistani Sufi singer
        "ali hassan kuban",       # Sudanese Nubian music
        "nour eddine",            # Moroccan gnawa
        "mahmoud guinia",         # Moroccan gnawa master
        "hamid el kasri",         # Moroccan gnawa
        "deben bhattacharya",     # Indian field recordings / fusion
        "l. shankar",             # Indian violin / world fusion
        "anoushka shankar",       # Indian sitar / fusion
        "ravi shankar",           # Indian sitar classic
        "ali akbar khan",         # Indian sarod
        "sultan khan",            # Indian sarangi
        "zakir hussain",          # Indian tabla (world music)
        "bulgarian voices",       # Bulgarian a cappella / world
        "le mystere des voix",    # Bulgarian voices label release
        "klezmatics",             # klezmer band
        "frank london",           # klezmer / Jewish world music
        "david krakauer",         # klezmer clarinet
        "golem ",                 # NYC klezmer punk — trailing space
        "charango",               # Andean instrument → Andean music
        "los calchakis",          # Andean folk
        "los kjarkas",            # Bolivian folk
        # ─ Added v6: world artists from INBOX analysis ─
        "khaled ",                # Algerian raï legend — trailing space (Didi, Aicha)
        "yasmine hamdan",         # Lebanese art/world pop (Ya Nass)
        "oi va voi",              # British klezmer-influenced world (Refugee)
        "mory kanté", "mory kante",  # Guinean kora/pop (Yeke Yeke)
        "mercan dede",            # Turkish-Canadian Sufi electronica
        "fanfare ciocarlia",      # Romanian Romani brass band (Asfalt Tango)
        # ─ Added v7: world artists from INBOX analysis ─
        "hotei ",                 # Tomoyasu Hotei — Japanese rock guitarist (Battle Without Honor or Humanity) — trailing space
        "meiko kaji",             # Japanese actress/singer (Flower of Carnage, Lady Snowblood OST)
        "magic system",           # Ivorian coupé-décalé group (Premier Gaou)
        "lijadu sisters",         # Nigerian Afrobeat pioneers (Danger)
        "zventa sventana",        # Russian ethno-folk fusion group
        # ─ Added v8: world artists from full INBOX analysis ─
        "dawn penn",              # Jamaican reggae (No No No, You Don't Love Me)
        "aya nakamura",           # French-Malian Afro-pop (Djadja, Pookie, Copines)
        "rodrigo ",               # Argentine folk singer (La Mano de Dios, El Indio) — trailing space
        # ─ Added v9: world artists from full INBOX analysis ─
        "the congos",             # Jamaican roots reggae (Fisherman, Ark of the Covenant)
        "slumdog millionaire",    # Indian film soundtrack keyword (Jai Ho, O... Saya)
        "islandman",              # Turkish/Swedish electronic-world fusion (Sumeru)
        "mahmood ",               # Italian pop with MENA/Maghrebi roots (Soldi) — trailing space
        "shintaro sakamoto",      # Japanese indie-pop (Let's Dance Raw, Wow)
        "rostam ",                # Iranian-American indie (Unfold You, Wood) — trailing space
        # ─ Added v11: world artists from INBOX analysis ─
        "sharmoofers",            # Egyptian indie pop band (Enta Meen, Mabyen Aleik)
        "joao selva",             # French-Brazilian musician (Pitanga, Macumba Virou Cha)
        # ─ Added v12: world artists from INBOX analysis ─
        "wizkid",                 # Nigerian Afrobeats superstar (Essence, Come Closer ft. Drake)
        "playing for change",     # World music project — global musician collaborations (Stand by Me)
        "laya project",           # World music film/album (Va Va Voom, Chale Chalo)
        "the slickers",           # Jamaican reggae (Johnny Too Bad — The Harder They Come OST)
        "quantic",                # UK downtempo/world music producer (Time Is the Enemy, The 5th Exotic)
        "planet drum",            # Mickey Hart (Grateful Dead) world percussion project
        # ─ Added v13: world artists from INBOX analysis ─
        "athena ",                # Greek pop/rock band — trailing space
        "bombo clat",             # World bass / dancehall crossover
        "drumspyder",             # Ecstatic dance / world percussion producer
        "enta omri",              # Arabic song title (Umm Kulthum classic — extra catchall)
        "james asher",            # UK world music / new age percussionist
        # ─ Genre terms ─
        "world music", "global",
        "afro ", "african",
        "qawwali", "sufi",
        "didgeridoo", "native american",
        "deep forest", "enigma ",
        "world beat",
    ]),

    # ── 11 Remixes (LAST rule — catches any remaining unclassified remixes) ──
    # Known artists match their genre above (first-match wins).
    # Only truly unrecognised remixes fall here instead of INBOX.
    ("remixes", [
        " remix", "_remix", "(remix)", "[remix]",
        " rmx ", "_rmx_", "(rmx)", "[rmx]",
        "vip mix", "vip edit",
        "extended remix", "club remix",
        "bootleg remix",
    ]),

]

# ─────────────────────────────────────────────────────────────────────────────
# YEAR-BASED CLASSICS FALLBACK
# If a filename contains a year from 1900–1989 (in parentheses or brackets),
# and no other rule matched, classify as Classics.
# ─────────────────────────────────────────────────────────────────────────────

_YEAR_RE = re.compile(r'[\(\[\s]1[0-9]{3}[\)\]\s\._-]')

def _has_old_year(name_lower):
    """Return True if filename has a year in the range 1900-1989."""
    for match in _YEAR_RE.finditer(name_lower):
        try:
            year_str = ''.join(c for c in match.group() if c.isdigit())
            if 1900 <= int(year_str) <= 1989:
                return True
        except ValueError:
            pass
    return False

# ─────────────────────────────────────────────────────────────────────────────
# CLASSIFICATION LOGIC
# ─────────────────────────────────────────────────────────────────────────────

def has_hebrew(text):
    """Return True if text contains any Hebrew Unicode characters."""
    for char in text:
        block = unicodedata.name(char, '').lower()
        if 'hebrew' in block:
            return True
        # Direct Unicode range check: Hebrew block U+0590–U+05FF
        cp = ord(char)
        if 0x0590 <= cp <= 0x05FF:
            return True
    return False

def classify_file(filepath):
    """Return (genre_key, matched_rule) for a given file path."""
    name = filepath.name
    # v3 FIX: Normalize to NFC before lowercasing.
    # macOS HFS+ stores filenames in NFD (decomposed Unicode), so accented
    # characters like ü are stored as u + combining diacritic. Python string
    # literals in this file are NFC (composed). Without this fix, keywords like
    # "tahüm" never matched even though the artist was in the keyword list.
    name_lower = unicodedata.normalize('NFC', name).lower()

    # 1. Hebrew characters → Israeli
    if has_hebrew(name):
        return ("israeli", "Hebrew characters detected in filename")

    # 2. Keyword rules
    for genre_key, keywords in GENRE_RULES:
        if keywords is None:
            continue   # handled by has_hebrew above
        for kw in keywords:
            if kw.lower() in name_lower:
                return (genre_key, f"Keyword match: '{kw}'")

    # 3. Old-year fallback → Classics
    if _has_old_year(name_lower):
        return ("classics", "Year 1900–1989 detected in filename")

    # 4. Default: unclassified
    return ("inbox", "No match — needs manual review")

def get_dest_folder(genre_key):
    key = genre_key.replace("israeli_unicode", "israeli")
    folder_name = FOLDERS.get(key, FOLDERS["inbox"])
    return DJ_MUSIC_ROOT / folder_name

# ─────────────────────────────────────────────────────────────────────────────
# PREVIEW & EXECUTE
# ─────────────────────────────────────────────────────────────────────────────

def collect_files():
    """Collect all audio files from MAIN_CRATE (non-recursive, flat folder)."""
    if not MAIN_CRATE.exists():
        print(f"\nERROR: Main Crate folder not found at: {MAIN_CRATE}")
        print("Please check the MAIN_CRATE path at the top of this script.")
        sys.exit(1)

    files = []
    for f in MAIN_CRATE.iterdir():
        if f.is_file() and f.suffix.lower() in AUDIO_EXTS:
            files.append(f)
    return sorted(files, key=lambda x: x.name.lower())

def run_preview(files):
    """Show a plan of all moves without doing anything."""
    counts = defaultdict(int)
    print("\n" + "="*72)
    print("  PREVIEW MODE — No files will be moved")
    print("="*72)
    print(f"\nSource folder:  {MAIN_CRATE}")
    print(f"Destination:    {DJ_MUSIC_ROOT}")
    print(f"Total files:    {len(files)}")
    print()

    plan = []
    for f in files:
        genre_key, rule = classify_file(f)
        dest_folder = get_dest_folder(genre_key)
        genre_name = FOLDERS.get(genre_key, FOLDERS["inbox"])
        plan.append({
            "filename": f.name,
            "genre": genre_name,
            "rule": rule,
            "source": str(f),
            "destination": str(dest_folder / f.name),
        })
        counts[genre_name] += 1

    # Print summary table
    print("CLASSIFICATION SUMMARY:")
    print(f"{'Genre Folder':<35} {'Files':>7}")
    print("-" * 44)
    for genre_name in sorted(counts.keys()):
        print(f"  {genre_name:<33} {counts[genre_name]:>6}")
    print("-" * 44)
    print(f"  {'TOTAL':<33} {sum(counts.values()):>6}")

    # Write detailed CSV
    csv_path = Path.home() / "Desktop" / "sort_main_crate_preview.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=["filename", "genre", "rule", "source", "destination"])
        writer.writeheader()
        writer.writerows(plan)

    print(f"\nDetailed plan saved to: {csv_path}")
    print("Open this CSV in Numbers or Excel to review every individual move.")
    print("\nTo check specific misclassifications, search the CSV for 'No match'")
    print("(those go to 00_INBOX) and for any genre you want to double-check.")
    print()
    print("When ready to proceed: python3 sort_main_crate.py --execute")
    print("="*72)
    return plan

def run_execute(files):
    """Move all files to their classified destination folders."""
    print("\n" + "="*72)
    print("  EXECUTE MODE — Moving files now")
    print("="*72)
    print(f"\nSource: {MAIN_CRATE}")
    print(f"Destination root: {DJ_MUSIC_ROOT}")
    print()

    # Verify DJ_MUSIC_ROOT exists
    if not DJ_MUSIC_ROOT.exists():
        print(f"ERROR: DJ_MUSIC root folder not found: {DJ_MUSIC_ROOT}")
        print("Please create the DJ_MUSIC folder structure first (see Section 2 of your plan).")
        sys.exit(1)

    # Create destination folders if they don't exist
    for key, folder_name in FOLDERS.items():
        dest = DJ_MUSIC_ROOT / folder_name
        dest.mkdir(parents=True, exist_ok=True)

    moved = 0
    skipped = 0
    errors = []
    log_lines = []

    for i, f in enumerate(files, 1):
        genre_key, rule = classify_file(f)
        dest_folder = get_dest_folder(genre_key)
        dest_path = dest_folder / f.name

        # Progress indicator
        if i % 100 == 0 or i == len(files):
            print(f"  Progress: {i}/{len(files)} files processed...")

        # Handle duplicate filenames at destination
        if dest_path.exists():
            stem = dest_path.stem
            suffix = dest_path.suffix
            counter = 1
            while dest_path.exists():
                dest_path = dest_folder / f"{stem}_dup{counter}{suffix}"
                counter += 1
            print(f"  DUPLICATE: {f.name} → renamed to {dest_path.name}")

        try:
            shutil.move(str(f), str(dest_path))
            moved += 1
            log_lines.append(f"MOVED: {f.name} → {dest_folder.name}/{dest_path.name}  [{rule}]")
        except Exception as e:
            skipped += 1
            errors.append(f"ERROR: {f.name} — {e}")
            log_lines.append(f"ERROR: {f.name} — {e}")

    # Write log
    log_path = Path.home() / "Desktop" / "sort_main_crate_log.txt"
    with open(log_path, "w", encoding="utf-8") as lf:
        lf.write(f"sort_main_crate.py — Execution Log\n")
        lf.write(f"Source: {MAIN_CRATE}\n")
        lf.write(f"Destination: {DJ_MUSIC_ROOT}\n")
        lf.write(f"Total moved: {moved} | Errors: {len(errors)}\n")
        lf.write("=" * 72 + "\n\n")
        for line in log_lines:
            lf.write(line + "\n")

    print()
    print("="*72)
    print(f"  DONE")
    print(f"  Files moved:   {moved}")
    print(f"  Errors:        {len(errors)}")
    print(f"  Log saved to:  {log_path}")
    print("="*72)

    if errors:
        print("\nERRORS (files that could not be moved):")
        for err in errors:
            print(f"  {err}")

    print()
    print("NEXT STEP: Open Rekordbox → File → Display All Missing Files →")
    print("           File → Relocate → Auto Relocate")
    print()

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("--preview", "--execute"):
        print(__doc__)
        print("\nUSAGE:")
        print("  python3 sort_main_crate.py --preview    ← see the plan, no moves")
        print("  python3 sort_main_crate.py --execute    ← run the actual moves")
        sys.exit(0)

    print(f"\nsort_main_crate.py v3 — DJ Library Auto-Sort for Lionel Mitelpunkt")
    print(f"Scanning: {MAIN_CRATE} ...")

    files = collect_files()
    print(f"Found {len(files)} audio files.")

    if sys.argv[1] == "--preview":
        run_preview(files)
    elif sys.argv[1] == "--execute":
        # Safety check: require preview to have been run first
        csv_path = Path.home() / "Desktop" / "sort_main_crate_preview.csv"
        if not csv_path.exists():
            print("\nWARNING: Preview CSV not found on Desktop.")
            print("It is strongly recommended to run --preview first and review the plan.")
            confirm = input("Type 'yes' to proceed anyway: ").strip().lower()
            if confirm != "yes":
                print("Aborted. Run --preview first.")
                sys.exit(0)
        run_execute(files)

if __name__ == "__main__":
    main()
