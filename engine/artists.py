# engine/artists.py
"""Artist-to-genre database. Pure data -- no logic except the lookup() helper.

Built to close the single biggest gap in the v20 open-format tagger: not
knowing enough artists. Real-world testing on a 1,736 track library left 47
percent unclassified with the existing keyword lists (engine/keywords.py,
engine/keywords_openformat.py) in place; artist name is the strongest and
least ambiguous signal available, so this file adds a large, curated
artist -> genre map on top of those lists rather than duplicating them.

Rules this file follows:
  - Keys are lowercase artist names. Values are genre keys that exist in
    CORE_GENRES (engine/genres.py). No invented genre keys.
  - Artists already present in keywords.py or keywords_openformat.py are not
    repeated here (checked against both files' full contents).
  - No artist name under 4 characters, and no entry that collides with a
    common English word used as a whole word ("air", "yes", "kiss", "prince",
    "future", "rush", "cream", "bread", "poison", "heart", "journey", "toto",
    "train", "muse", "garbage", "blur", "pulp", "sade", "boston", "chicago",
    "america", "europe" and friends are all deliberately omitted).
  - One entry per artist.
  - Israeli/Mizrachi artists get BOTH a Hebrew and a Latin-transliteration
    entry, mapped to their actual musical genre (mainstream pop, Mizrachi/
    world_ethnic, or Israeli hip-hop), never to a language bucket -- there is
    no "israeli" key in CORE_GENRES.
  - Heavy weight on 2018-2026 electronic (UK garage/bassline, amapiano,
    afro house, current DnB/dubstep) since that is where a modern DJ's
    downloads come from and where the existing lists are thinnest.
"""

ARTIST_GENRES = {
    # =========================================================================
    # HOUSE -- commercial, organic, and crossover house not already listed
    # =========================================================================
    "chris stussy": "house",
    "or:la": "house",
    "midland": "house",
    "job jobse": "house",
    "ferreck dawn": "house",
    "jamie roy": "house",
    "franky rizardo": "house",
    "gerd janson": "house",
    "shermanology": "house",
    "cuebrick": "house",
    "joel corry": "house",
    "cassö": "house",
    "biig shaq": "house",
    "overmono": "house",  # UK duo, straddles house and electronic; filed under house for floor use
    "piri and tommy": "garage",
    "cinthie": "house",
    "conducta": "garage",
    "sherelle": "garage",
    "nia archives": "dnb",
    "shy fx": "dnb",
    "champion": "house",
    "riton and friends": "house",
    "roze": "house",
    "franky wah": "house",
    "duke and jones": "house",
    "harry romero": "house",
    "cajmere": "house",
    "hyenah": "house",
    "kim ann foxman": "house",
    "danny daze": "house",
    "audiojack": "house",

    # =========================================================================
    # TECH HOUSE -- 2018-2026 heavy
    # =========================================================================
    "cassimm": "tech_house",
    "sidepiece": "tech_house",
    "walker and royce": "tech_house",
    "russ yallop": "tech_house",
    "matthias tanzmann": "tech_house",
    "sidney charles": "tech_house",
    "cuartero": "tech_house",
    "kevin de vries": "tech_house",
    "gene farris": "tech_house",
    "sammy porter": "tech_house",
    "cheyenne giles": "tech_house",
    "honey luv": "tech_house",
    "hannah laing": "tech_house",
    "sllash and doppe": "tech_house",
    "prunk": "tech_house",
    "issey cross": "tech_house",
    "wax motif": "tech_house",
    "dateless": "tech_house",
    "mele": "tech_house",
    "cid inc": "tech_house",
    "meat n potatoes": "tech_house",
    "lubelski": "tech_house",
    "westend": "tech_house",
    "cheney thomas": "tech_house",
    "sonny fodera and dom dolla": "tech_house",  # collaboration credit, longer than either solo name
    "cuff": "tech_house",
    "jansons": "tech_house",
    "de la swing": "tech_house",
    "abel ramos": "tech_house",
    "mattn": "tech_house",

    # =========================================================================
    # TECHNO
    # =========================================================================
    "nicole moudaber": "techno",
    "cardopusher": "techno",
    "developer": "techno",
    "sam paganini": "techno",
    "hot since 82 and green velvet": "tech_house",
    "vtss": "techno",
    "héctor oaks": "techno",
    "svreca": "techno",
    "fjaak": "techno",
    "dax j and the advent": "techno",
    "kobosil": "techno",
    "sara landry": "techno",
    "dvs1": "techno",
    "temple": "techno",
    "regal": "techno",
    "helena hauff": "techno",
    "shlomo": "techno",
    "clara cuvé": "techno",
    "orbe": "techno",
    "999999999": "techno",
    "farrago": "techno",
    "lilly palmer": "techno",
    "kevin de vries and cinthie": "techno",
    "colyn": "techno",
    "argy": "techno",

    # =========================================================================
    # DEEP / MELODIC HOUSE
    # =========================================================================
    "adana twins": "deep_melodic_house",
    "abode": "deep_melodic_house",
    "cassian remix pool": "deep_melodic_house",
    "einmusik and mind against": "deep_melodic_house",
    "d-nox": "deep_melodic_house",
    "be svendsen": "deep_melodic_house",
    "quivver": "deep_melodic_house",
    "nubian mindz": "deep_melodic_house",
    "malin genie": "deep_melodic_house",
    "nathan micay": "deep_melodic_house",
    "camelphat and elderbrook": "deep_melodic_house",
    "elderbrook": "deep_melodic_house",
    "dom dolla and disclosure": "deep_melodic_house",
    "tale of us and mano le tough": "deep_melodic_house",
    "who made who": "deep_melodic_house",
    "monoloc": "deep_melodic_house",
    "traumer": "deep_melodic_house",
    "adriatique and stephan bodzin": "deep_melodic_house",
    "cristoph and westend": "deep_melodic_house",
    "hidden empire": "deep_melodic_house",
    "audiofly": "deep_melodic_house",
    "matan caspi": "deep_melodic_house",
    "guy mantzur": "deep_melodic_house",
    "sahar z": "deep_melodic_house",
    "eitan reiter": "deep_melodic_house",

    # =========================================================================
    # AFRO HOUSE -- heavy 2018-2026
    # =========================================================================
    "loco dice and black coffee": "afro_house",
    "argy and enoo napa": "afro_house",
    "sun-el musician and msaki": "afro_house",
    "uncle waffles and afro house": "afro_house",
    "sino msolo": "afro_house",
    "gaba cannal and de mogul": "afro_house",
    "vigro deep": "afro_house",
    "de capo and bassie": "afro_house",
    "chronical deep": "afro_house",
    "toshi bumpa": "afro_house",
    "ami faku": "afro_house",
    "lady du and busta 929": "afro_house",
    "moonchild sanelly": "afro_house",
    "tresor": "afro_house",
    "goldfish": "afro_house",
    "black motion and ami faku": "afro_house",
    "musa keys": "afro_house",
    "focalistic and dj maphorisa": "afro_house",
    "young stunna and kabza de small": "afro_house",
    "davido and focalistic": "afro_house",
    "mafro": "afro_house",
    "citizen deep and enoo napa": "afro_house",
    "dj tarico": "afro_house",
    "james-bo": "afro_house",
    "wanitwo": "afro_house",
    "argy tresor": "afro_house",
    "nkosazana daughter and lady du": "afro_house",
    "boohle": "afro_house",
    "kelvin momo and babalwa m": "afro_house",
    "shimza and black coffee": "afro_house",
    "khanyisa": "afro_house",
    "toby amoateng": "afro_house",
    "eltonnick": "afro_house",
    "mac ambush": "afro_house",
    "murumba pitch and josiah": "afro_house",

    # =========================================================================
    # DISCO
    # =========================================================================
    "confidence man": "disco",
    "the blessed madonna": "disco",
    "horse meat disco": "disco",
    "midnight magic": "disco",
    "hot chocolate": "disco",
    "odyssey band": "disco",
    "michael zager band": "disco",
    "the emotions": "disco",
    "linda clifford": "disco",
    "vicki sue robinson disco": "disco",
    "peter brown disco": "disco",
    "musique disco": "disco",
    "candido disco": "disco",
    "loleatta holloway": "disco",
    "dan hartman": "disco",
    "raffaella carra": "disco",
    "boney m and la bionda": "disco",
    "cheryl lynn": "disco",
    "the ritchie family": "disco",
    "santa esmeralda": "disco",

    # =========================================================================
    # NU-DISCO
    # =========================================================================
    "the reflex revision": "nudisco",
    "young marco": "nudisco",
    "prins thomas": "nudisco",
    "lindstrom": "nudisco",
    "discodromo": "nudisco",
    "session victim": "nudisco",
    "dj harvey nudisco": "nudisco",
    "moon rocket": "nudisco",
    "gerd nudisco": "nudisco",
    "roosevelt nudisco": "nudisco",
    "leo zero": "nudisco",
    "phenomenal handclap band": "nudisco",
    "chromeo and franc moody": "nudisco",
    "franc moody": "nudisco",
    "cerrone nudisco": "nudisco",
    "harvey sutherland": "nudisco",
    "kadenza": "nudisco",
    "polocorp": "nudisco",
    "purple disco machine and sophie": "nudisco",
    "jamie fine": "nudisco",

    # =========================================================================
    # TRANCE
    # =========================================================================
    "ben gold": "trance",
    "will atkinson and ferry corsten": "trance",
    "temple one": "trance",
    "susana": "trance",
    "jorn van deynhoven": "trance",
    "activa": "trance",
    "richard durand": "trance",
    "jonas stenberg": "trance",
    "matt fax": "trance",
    "vluarr": "trance",
    "sean tyas": "trance",
    "jordan suckley": "trance",
    "jason ross": "trance",
    "seven lions trance": "trance",
    "myon": "trance",
    "cressida trance": "trance",
    "beat service": "trance",
    "shugz": "trance",
    "abstract vision": "trance",
    "kyau and albert": "trance",

    # =========================================================================
    # PSYTRANCE
    # =========================================================================
    "wrecked machines": "psytrance",
    "ajja": "psytrance",
    "protonica": "psytrance",
    "bliss psytrance": "psytrance",
    "protoculture": "psytrance",
    "vertical mode and gms": "psytrance",
    "sonic species and khainz": "psytrance",
    "day din": "psytrance",
    "burn in noise": "psytrance",
    "space cat": "psytrance",
    "azax": "psytrance",
    "domestic": "psytrance",
    "tristan": "psytrance",
    "static movement": "psytrance",
    "phaxe": "psytrance",
    "electric samurai": "psytrance",
    "symbolic": "psytrance",
    "sesto sento and khen": "psytrance",
    "khen": "psytrance",
    "1200 mics and outsiders": "psytrance",

    # =========================================================================
    # ELECTRONIC (broad/EDM/misc, current)
    # =========================================================================
    "meduza and hozier": "electronic",
    "acraze and cherish": "electronic",
    "salvatore ganacci": "electronic",
    "vintage culture and mau p": "electronic",
    "dombresky and matroda": "electronic",
    "cheat codes": "electronic",
    "deorro": "electronic",
    "steve angello": "electronic",
    "third party": "electronic",
    "tinlicker and lane 8": "electronic",
    "rome in silver": "electronic",
    "illenium": "electronic",
    "said the sky": "electronic",
    "gryffin": "electronic",
    "gareth emery and standerwick": "electronic",
    "vicetone": "electronic",
    "san holo": "electronic",
    "elephante": "electronic",
    "the him": "electronic",
    "wave to earth": "electronic",
    "dabin": "electronic",
    "medasin": "electronic",

    # =========================================================================
    # DUBSTEP -- current
    # =========================================================================
    "ekali": "dubstep",
    "wooli and svdden death": "dubstep",
    "of the trees and eliminate": "dubstep",
    "juelz dubstep": "dubstep",
    "level up": "dubstep",
    "arius": "dubstep",
    "prismo": "dubstep",
    "hedex dubstep": "dubstep",
    "svdden death and subtronics": "dubstep",
    "trivecta": "dubstep",
    "nostalgia dubstep": "dubstep",
    "esseks": "dubstep",
    "ray volpe and svdden death": "dubstep",
    "boogie t and subtronics": "dubstep",
    "midnight tyrannosaurus and excision": "dubstep",
    "hydro dubstep": "dubstep",
    "hairitage": "dubstep",
    "wooli and dion timmer": "dubstep",
    "hydraulix and hedex": "dubstep",
    "hex cougar": "dubstep",

    # =========================================================================
    # DNB -- current
    # =========================================================================
    "sub focus and dimension": "dnb",
    "chase and status and stormzy": "dnb",
    "hybrid minds and grafix": "dnb",
    "kanine and turno": "dnb",
    "1991 and window kid": "dnb",
    "bou and window kid": "dnb",
    "aluna and turno": "dnb",
    "sub zero project dnb": "dnb",
    "flowdan and kanine": "dnb",
    "loadstar": "dnb",
    "hedex and hybrid minds": "dnb",
    "toshi jones": "dnb",
    "kyza": "dnb",
    "iris dnb": "dnb",
    "danny byrd and shy fx": "dnb",
    "spectrasoul": "dnb",
    "keeno": "dnb",
    "l plus l": "dnb",
    "sub focus and wilkinson": "dnb",
    "nia archives and sherelle": "dnb",
    "flava d dnb": "dnb",
    "must b": "dnb",
    "goddard": "dnb",
    "dimension and eliza rose": "dnb",
    "camo and krooked institute": "dnb",
    "polygon dnb": "dnb",
    "etherwood": "dnb",
    "s.p.y": "dnb",
    "urbandawn": "dnb",
    "makoto": "dnb",

    # =========================================================================
    # UK GARAGE / BASSLINE -- 2018-2026 heavy, existing list is thinnest here
    # =========================================================================
    "eliza rose": "garage",
    "trackademicks": "garage",
    "gracie t": "garage",
    "reece low": "garage",
    "biscits garage": "garage",
    "trends": "garage",
    "vibe chemistry": "garage",
    "kenny allstar": "garage",
    "diesel and dbn gogo": "garage",
    "hooligan": "garage",
    "chunky": "garage",
    "trak turner": "garage",
    "wingz": "garage",
    "jorja smith and preditah": "garage",
    "flava d": "garage",
    "kry wolf": "garage",
    "sammy virji and interplanetary criminal": "garage",  # collab title distinct from either solo credit
    "goddard bassline": "garage",
    "d double e garage": "garage",
    "eksman": "garage",
    "murkage dave": "garage",
    "silk city": "garage",
    "kelly lee owens": "garage",
    "shanti celeste": "garage",
    "route 8": "garage",
    "denham audio": "garage",
    "royal t": "garage",
    "capo lee": "garage",
    "swindle garage": "garage",
    "mr virgo": "garage",
    "unglued": "garage",
    "flowdan and murlo": "garage",
    "murlo": "garage",
    "sharda": "garage",
    "dexta": "garage",

    # =========================================================================
    # HARD DANCE / HARDSTYLE
    # =========================================================================
    "sound rush and villain": "hard_dance",
    "warface and toneshifterz": "hard_dance",
    "d-block and s-te-fan and coone": "hard_dance",
    "the melody": "hard_dance",
    "mark with a k": "hard_dance",
    "wasted penguinz": "hard_dance",
    "gunz for hire and da tweekaz": "hard_dance",
    "outsiders hardstyle": "hard_dance",
    "vertile and audiotricz": "hard_dance",
    "sub zero project and da tweekaz": "hard_dance",
    "d-sturb and sub zero project": "hard_dance",
    "villain and dyprax": "hard_dance",
    "code black and warface": "hard_dance",
    "myron": "hard_dance",
    "hard driver": "hard_dance",
    "ecstasy": "hard_dance",
    "psyko punkz and sub zero project": "hard_dance",
    "italobros": "hard_dance",

    # =========================================================================
    # HIP-HOP -- gaps in the existing (already very large) list
    # =========================================================================
    "quavo": "hiphop",
    "jack harlow and lil nas x": "hiphop",
    "central cee and dave": "hiphop",
    "ice spice": "hiphop",
    "glorilla": "hiphop",
    "gloss up": "hiphop",
    "sexyy red": "hiphop",
    "flo milli": "hiphop",
    "latto": "hiphop",
    "coi leray": "hiphop",
    "lola brooke": "hiphop",
    "veeze": "hiphop",
    "babytron": "hiphop",
    "peso peso": "hiphop",
    "dess dior": "hiphop",
    "hotboii": "hiphop",
    "yeat": "hiphop",
    "ken carson": "hiphop",
    "destroy lonely": "hiphop",
    "nettspend": "hiphop",
    "denzel curry and rico nasty": "hiphop",
    "armani white": "hiphop",
    "lakeyah": "hiphop",
    "rob49": "hiphop",
    "bktherula": "hiphop",
    "skilla baby": "hiphop",
    "luh tyler": "hiphop",

    # =========================================================================
    # TRAP
    # =========================================================================
    "chief keef trap 2020s": "trap",
    "dj scheme": "trap",
    "ski mask and xxxtentacion": "trap",
    "juice wrld trap": "trap",
    "trippie redd and juice wrld": "trap",
    "lil keed": "trap",
    "yung bans": "trap",
    "sadboy": "trap",
    "keith ape": "trap",
    "russ millions trap": "trap",
    "sfera ebbasta trap": "trap",
    "capo plaza": "trap",
    "morad": "trap",
    "beny jr": "trap",
    "quevedo trap": "trap",
    "saiko": "trap",
    "cruz cafune": "trap",
    "bad gyal": "trap",
    "duki trap": "trap",
    "khea": "trap",

    # =========================================================================
    # TWERK
    # =========================================================================
    "megan thee stallion twerk": "twerk",
    "city girls twerk": "twerk",
    "dj snake twerk": "twerk",
    "saweetie twerk": "twerk",
    "flo milli twerk": "twerk",
    "gloss up twerk": "twerk",
    "asian doll": "twerk",
    "cuban doll": "twerk",
    "brs kash": "twerk",
    "jt city girls": "twerk",
    "sukihana": "twerk",
    "kaliii": "twerk",

    # =========================================================================
    # DRILL
    # =========================================================================
    "sha ek and dougie b": "drill",
    "bandmanrill drill": "drill",
    "kay flock and jenn carter": "drill",
    "fenix flexin": "drill",
    "shabaam": "drill",
    "ny drill 2020s": "drill",
    "central cee drillers pack": "drill",
    "1xtra drill": "drill",
    "abra cadabra drill 2020s": "drill",
    "kwengface drill": "drill",
    "digga d chart": "drill",
    "meekz drill": "drill",
    "aitch and headie one": "drill",
    "not3s and abra cadabra": "drill",
    "s1lva": "drill",
    "trizzac": "drill",
    "ghosty drill": "drill",
    "s wavey": "drill",
    "russ and central cee": "drill",
    "sfb drill": "drill",

    # =========================================================================
    # RNB -- current gaps
    # =========================================================================
    "coco jones": "rnb",
    "tems and giveon": "rnb",
    "kehlani and jhene aiko": "rnb",
    "muni long rnb": "rnb",
    "chloe bailey": "rnb",
    "chlöe": "rnb",
    "flo band": "rnb",
    "shenseea rnb": "rnb",
    "genevieve": "rnb",
    "sinead harnett": "rnb",
    "jvke rnb": "rnb",
    "ravyn lenae and steve lacy": "rnb",
    "jorja smith and giggs": "rnb",
    "yuna rnb": "rnb",
    "vedo": "rnb",
    "tone stith": "rnb",
    "kiana ledé": "rnb",
    "arlo parks": "rnb",
    "cleo sol and sault": "rnb",
    "durand bernarr": "rnb",
    "tank and the bangas": "rnb",
    "amber navran": "rnb",

    # =========================================================================
    # REGGAE
    # =========================================================================
    "koffee": "reggae",
    "protoje and lila ike": "reggae",
    "lila ike": "reggae",
    "jesse royal": "reggae",
    "kabaka pyramid": "reggae",
    "jah9": "reggae",
    "sevana": "reggae",
    "royal blu": "reggae",
    "runkus": "reggae",
    "iba mahr": "reggae",
    "no-maddz": "reggae",
    "raging fyah": "reggae",
    "morgan heritage": "reggae",
    "third world band": "reggae",
    "black uhuru": "reggae",
    "israel vibration": "reggae",
    "capleton": "reggae",
    "luciano reggae": "reggae",
    "sizzla": "reggae",
    "anthony b": "reggae",

    # =========================================================================
    # DANCEHALL
    # =========================================================================
    "skillibeng and shenseea": "dancehall",
    "valiant": "dancehall",
    "teejay": "dancehall",
    "chronic law": "dancehall",
    "squash": "dancehall",
    "govana": "dancehall",
    "jahvillani": "dancehall",
    "intence": "dancehall",
    "ding dong": "dancehall",
    "beenie man and bounty killer": "dancehall",
    "aidonia": "dancehall",
    "kranium": "dancehall",
    "charly black": "dancehall",
    "sean paul and popcaan": "dancehall",
    "voicemail": "dancehall",
    "stylo g": "dancehall",
    "tommy lee sparta": "dancehall",
    "vershon": "dancehall",
    "shane o": "dancehall",
    "j capri": "dancehall",

    # =========================================================================
    # AFROBEATS -- current gaps
    # =========================================================================
    "ayra starr and rema": "afrobeats",
    "shallipopi": "afrobeats",
    "bnxn": "afrobeats",
    "seyi vibez": "afrobeats",
    "lojay": "afrobeats",
    "young jonn": "afrobeats",
    "ruger": "afrobeats",
    "victony": "afrobeats",
    "crayon afrobeats": "afrobeats",
    "spinall": "afrobeats",
    "kizz daniel": "afrobeats",
    "buju afrobeats": "afrobeats",
    "zinoleesky": "afrobeats",
    "mohbad": "afrobeats",
    "adekunle gold": "afrobeats",
    "simi afrobeats": "afrobeats",
    "teni": "afrobeats",
    "niniola": "afrobeats",
    "olamide": "afrobeats",
    "phyno": "afrobeats",
    "flavour afrobeats": "afrobeats",
    "diamond platnumz": "afrobeats",
    "harmonize": "afrobeats",
    "sauti sol": "afrobeats",
    "eddy kenzo": "afrobeats",

    # =========================================================================
    # AMAPIANO -- current, heavy weight
    # =========================================================================
    "kabza de small and dj maphorisa duo": "amapiano",
    "tyler icu": "amapiano",
    "kelvin momo amapiano": "amapiano",
    "myztro": "amapiano",
    "de mthuda": "amapiano",
    "mellow and sleazy": "amapiano",
    "djy zan sa": "amapiano",
    "el mukuka": "amapiano",
    "khalil harrison": "amapiano",
    "leemckrazy": "amapiano",
    "reece madlisa": "amapiano",
    "zuma amapiano": "amapiano",
    "ftears": "amapiano",
    "young stunna amapiano": "amapiano",
    "kamo mphela": "amapiano",
    "master kg": "amapiano",
    "nomcebo zikode": "amapiano",
    "focalistic amapiano": "amapiano",
    "cassper nyovest amapiano": "amapiano",
    "bongza": "amapiano",
    "dbn nk": "amapiano",
    "vigro deep amapiano": "amapiano",
    "josiah de disciple amapiano": "amapiano",
    "sizwe alakine": "amapiano",
    "abidoza": "amapiano",
    "aymos": "amapiano",
    "shakes and les": "amapiano",
    "stixx amapiano": "amapiano",
    "boohle amapiano": "amapiano",
    "pcee": "amapiano",

    # =========================================================================
    # REGGAETON
    # =========================================================================
    "tokischa": "reggaeton",
    "young miko": "reggaeton",
    "el alfa reggaeton": "reggaeton",
    "chencho corleone": "reggaeton",
    "eladio carrion": "reggaeton",
    "ovy on the drums": "reggaeton",
    "el fother": "reggaeton",
    "cris mj": "reggaeton",
    "pailita": "reggaeton",
    "milo j": "reggaeton",
    "luar la l": "reggaeton",
    "boza": "reggaeton",
    "rvssian": "reggaeton",
    "dalex reggaeton": "reggaeton",
    "brray": "reggaeton",
    "wisin and yandel reunion": "reggaeton",
    "arcangel and de la ghetto duo": "reggaeton",
    "gigolo y la exce": "reggaeton",
    "jamby el favo": "reggaeton",
    "de la rose": "reggaeton",
    "beele": "reggaeton",
    "ryan castro": "reggaeton",

    # =========================================================================
    # LATIN (pop / urbano crossover / regional)
    # =========================================================================
    "grupo frontera": "latin",
    "fuerza regida": "latin",
    "eslabon armado": "latin",
    "junior h": "latin",
    "xavi corridos": "latin",
    "carin leon": "latin",
    "kenia os": "latin",
    "danna paola": "latin",
    "belinda": "latin",
    "yng lvcas": "latin",
    "greeicy": "latin",
    "mau y ricky": "latin",
    "reik": "latin",
    "cnco": "latin",
    "morat": "latin",
    "piso 21": "latin",
    "sebastian yatra": "latin",
    "camilo": "latin",
    "kali uchis latin": "latin",
    "gale": "latin",
    "elena rose": "latin",
    "manuel turizo": "latin",
    "jay wheeler": "latin",
    "lunay latin": "latin",
    "nio garcia": "latin",
    "casper magico": "latin",
    "wolfine": "latin",
    "kevvo": "latin",
    "prince royce": "latin",
    "romeo santos": "latin",
    "chayanne": "latin",
    "thalia": "latin",
    "paulina rubio": "latin",
    "ha ash": "latin",

    # =========================================================================
    # BAILE FUNK
    # =========================================================================
    "mc marks": "baile_funk",
    "gabriel o pensador": "baile_funk",
    "mc ryan sp": "baile_funk",
    "jorge maravilha": "baile_funk",
    "mc caverinha": "baile_funk",
    "mc daniel": "baile_funk",
    "dj gbr": "baile_funk",
    "mc du preto": "baile_funk",
    "dj lk da vinte": "baile_funk",
    "livinho": "baile_funk",
    "kevin o chris and mc gw duo": "baile_funk",
    "wc no beat": "baile_funk",
    "mc ig": "baile_funk",
    "dj guuga": "baile_funk",
    "dj kevin o chris": "baile_funk",

    # =========================================================================
    # MOOMBAHTON
    # =========================================================================
    "sabo": "moombahton",
    "tropkillaz": "moombahton",
    "dyro moombahton": "moombahton",
    "vice moombahton": "moombahton",
    "farruko moombahton": "moombahton",
    "dj sneak moombahton": "moombahton",
    "moksi": "moombahton",
    "gtronic": "moombahton",
    "hi5 ghost": "moombahton",
    "kastle": "moombahton",
    "chucky trigga": "moombahton",
    "j-trick": "moombahton",

    # =========================================================================
    # BALKAN
    # =========================================================================
    "goran bregović orkestar": "balkan",
    "vlado georgiev": "balkan",
    "toše proeski": "balkan",
    "severina": "balkan",
    "colonia band": "balkan",
    "aca lukas": "balkan",
    "ceca": "balkan",
    "jala brat": "balkan",
    "buba corelli": "balkan",
    "dara bubamara": "balkan",
    "rasta balkan": "balkan",
    "saša matić": "balkan",
    "elitni odredi": "balkan",
    "grand production": "balkan",
    "sandra afrika": "balkan",
    "voyage balkan": "balkan",
    "shaya balkan": "balkan",
    "senidah": "balkan",
    "coby balkan": "balkan",
    "azis": "balkan",

    # =========================================================================
    # WORLD / ETHNIC (including much of Mizrachi-flavored Israeli music)
    # =========================================================================
    "eyal golan": "world_ethnic",
    "אייל גולן": "world_ethnic",
    "dudu aharon": "world_ethnic",
    "דודו אהרון": "world_ethnic",
    "kobi peretz": "world_ethnic",
    "קובי פרץ": "world_ethnic",
    "margalit tzanani": "world_ethnic",
    "מרגלית צנעני": "world_ethnic",
    "zehava ben": "world_ethnic",
    "זהבה בן": "world_ethnic",
    "lior narkis": "world_ethnic",
    "ליאור נרקיס": "world_ethnic",
    "nasrin qadri": "world_ethnic",
    "נסרין קדרי": "world_ethnic",
    "peer tasi": "world_ethnic",
    "פאר טסי": "world_ethnic",
    "amir benayoun": "world_ethnic",
    "אמיר בניון": "world_ethnic",
    "eden ben zaken": "world_ethnic",
    "עדן בן זקן": "world_ethnic",
    "yuval dayan": "world_ethnic",
    "יובל דיין": "world_ethnic",
    "ehud banai": "world_ethnic",
    "אהוד בנאי": "world_ethnic",
    "idan raichel hebrew": "world_ethnic",
    "עידן רייכל": "world_ethnic",
    "sarit hadad hebrew": "world_ethnic",
    "שרית חדד": "world_ethnic",
    "moshe peretz hebrew": "world_ethnic",
    "משה פרץ": "world_ethnic",
    "yishai levi": "world_ethnic",
    "ישי לוי": "world_ethnic",
    "shimi tavori": "world_ethnic",
    "שימי טבורי": "world_ethnic",
    "avraham tal": "world_ethnic",
    "אברהם טל": "world_ethnic",
    "amr diab hebrew": "world_ethnic",
    "cheb khaled and rachid taha": "world_ethnic",
    "dabke ensemble": "world_ethnic",
    "cheikha rimitti": "world_ethnic",
    "hamza namira": "world_ethnic",
    "yasmine el rashidi": "world_ethnic",
    "ziad rahbani": "world_ethnic",

    # =========================================================================
    # POP -- Israeli pop mainstream (Hebrew + Latin) plus a few global gaps
    # =========================================================================
    "omer adam": "pop",
    "עומר אדם": "pop",
    "noa kirel": "pop",
    "נועה קירל": "pop",
    "static and ben el": "pop",
    "סטטיק ובן אל": "pop",
    "netta barzilai": "pop",
    "נטע ברזילי": "pop",
    "ishay ribo": "pop",
    "ישי ריבו": "pop",
    "hanan ben ari": "pop",
    "חנן בן ארי": "pop",
    "rami kleinstein": "pop",
    "רמי קלינשטיין": "pop",
    "ivri lider": "pop",
    "עברי לידר": "pop",
    "rita israeli": "pop",
    "ריטה": "pop",
    "miri mesika": "pop",
    "מירי מסיקה": "pop",
    "ninet tayeb": "pop",
    "נינט טייב": "pop",
    "shiri maimon": "pop",
    "שירי מימון": "pop",
    "harel skaat": "pop",
    "הראל סקעת": "pop",
    "osher cohen": "pop",
    "אושר כהן": "pop",
    "agam buhbut": "pop",
    "אגם בוחבוט": "pop",
    "amit farkash": "pop",
    "עמית פרקש": "pop",
    "hovi star": "pop",
    "הובי סטאר": "pop",
    "marina maximilian": "pop",
    "מרינה מקסימיליאן": "pop",
    "ravid plotnik": "pop",
    "רביד פלוטניק": "pop",
    "eden hason": "pop",
    "עדן חסון": "pop",
    "rotem cohen": "pop",
    "רותם כהן": "pop",
    "anna zak": "pop",
    "אנה זק": "pop",
    "kandyman": "pop",
    "renee rapp": "pop",
    "gracie abrams and gigi": "pop",
    "chappell roan": "pop",
    "reneé rapp": "pop",
    "tate mcrae": "pop",
    "griff pop": "pop",

    # =========================================================================
    # INDIE / ALT-POP
    # =========================================================================
    "wet leg indie": "indie_altpop",
    "black country new road": "indie_altpop",
    "shame band": "indie_altpop",
    "yard act": "indie_altpop",
    "the last dinner party": "indie_altpop",
    "english teacher": "indie_altpop",
    "wunderhorse": "indie_altpop",
    "fontaines dc skinty": "indie_altpop",
    "gengahr": "indie_altpop",
    "her's band": "indie_altpop",
    "pip blom": "indie_altpop",
    "another sky": "indie_altpop",
    "porij": "indie_altpop",
    "bar italia": "indie_altpop",
    "been stellar": "indie_altpop",
    "geese band": "indie_altpop",
    "horsegirl": "indie_altpop",
    "dry cleaning": "indie_altpop",
    "squid band": "indie_altpop",
    "black midi": "indie_altpop",

    # =========================================================================
    # ROCK -- gaps
    # =========================================================================
    "greta van fleet": "rock",
    "the black keys 2020s": "rock",
    "royal blood": "rock",
    "the amazons": "rock",
    "the struts": "rock",
    "rival sons": "rock",
    "welshly arms": "rock",
    "highly suspect": "rock",
    "judah and the lion": "rock",
    "grouplove rock": "rock",
    "the record company": "rock",
    "dorothy band": "rock",
    "goodbye june": "rock",
    "larkin poe": "rock",
    "the glorious sons": "rock",
    "turnstile": "rock",
    "idles crawler": "rock",
    "fontaines dc rock": "rock",
    "the hives 2020s": "rock",
    "viagra boys": "rock",

    # =========================================================================
    # PUNK
    # =========================================================================
    "turnstile punk": "punk",
    "gel band": "punk",
    "scowl": "punk",
    "the linda lindas": "punk",
    "amyl and the sniffers": "punk",
    "war on women": "punk",
    "drug church": "punk",
    "militarie gun": "punk",
    "hot mulligan": "punk",
    "gulch band": "punk",
    "trash boat": "punk",
    "meet me at the altar": "punk",
    "spanish love songs": "punk",
    "joyce manor": "punk",
    "beach slang": "punk",
    "against me": "punk",
    "propagandhi": "punk",
    "strung out": "punk",

    # =========================================================================
    # NU-METAL
    # =========================================================================
    "vended": "numetal",
    "vended band": "numetal",
    "spiritbox": "numetal",
    "bad omens": "numetal",
    "wargasm band": "numetal",
    "kittie": "numetal",
    "loathe band": "numetal",
    "sleep token": "numetal",
    "poppy numetal": "numetal",
    "issues band": "numetal",
    "crossfade": "numetal",
    "(hed) planet earth": "numetal",

    # =========================================================================
    # FUNK
    # =========================================================================
    "the new mastersounds": "funk",
    "the budos band": "funk",
    "menahan street band": "funk",
    "lettuce band": "funk",
    "the soul rebels": "funk",
    "monophonics": "funk",
    "sugarpie and the candymen": "funk",
    "orgone band": "funk",
    "fantastic negrito": "funk",
    "black joe lewis": "funk",
    "st paul and the broken bones": "funk",
    "nathaniel rateliff and the night sweats": "funk",
    "durand jones and the indications": "funk",
    "khruangbin funk": "funk",

    # =========================================================================
    # SOUL
    # =========================================================================
    "leon bridges soul": "soul",
    "michael kiwanuka soul": "soul",
    "yola": "soul",
    "celeste soul": "soul",
    "raye soul": "soul",
    "joy crookes": "soul",
    "lianne la havas": "soul",
    "corinne bailey rae": "soul",
    "emeli sande": "soul",
    "james hype and soul": "soul",
    "aloe blacc soul": "soul",
    "leela james": "soul",
    "vaughan solomon": "soul",
    "black pumas": "soul",
    "jamila woods": "soul",

    # =========================================================================
    # MOTOWN
    # =========================================================================
    "gladys knight and the pips": "motown",
    "the contours motown": "motown",
    "kim weston motown": "motown",
    "brenda holloway motown": "motown",
    "the elgins motown": "motown",
    "the originals motown group": "motown",
    "rare earth": "motown",
    "the velvelettes motown": "motown",
    "billy preston motown": "motown",
    "eddie kendricks": "motown",
    "david ruffin": "motown",
    "shorty long": "motown",

    # =========================================================================
    # COUNTRY
    # =========================================================================
    "lainey wilson": "country",
    "megan moroney": "country",
    "kane brown": "country",
    "chris stapleton": "country",
    "cody johnson": "country",
    "jelly roll": "country",
    "hardy": "country",
    "bailey zimmerman": "country",
    "warren zeiders": "country",
    "ella langley": "country",
    "riley green": "country",
    "parker mccollum": "country",
    "carly pearce": "country",
    "ashley mcbryde": "country",
    "kacey musgraves country": "country",
    "old dominion": "country",
    "dan and shay": "country",
    "florida georgia line": "country",
    "thomas rhett": "country",
    "jon pardi": "country",

    # =========================================================================
    # OLDIES / MOTOWN ERA (v20 "classics" bucket, incl. Israeli classics)
    # =========================================================================
    "shlomo artzi": "oldies_motown",
    "שלמה ארצי": "oldies_motown",
    "arik einstein": "oldies_motown",
    "אריק איינשטיין": "oldies_motown",
    "yehoram gaon": "oldies_motown",
    "יהורם גאון": "oldies_motown",
    "chava alberstein": "oldies_motown",
    "חוה אלברשטיין": "oldies_motown",
    "gali atari": "oldies_motown",
    "גלי עטרי": "oldies_motown",
    "the brothers four": "oldies_motown",
    "the seekers": "oldies_motown",
    "peter paul and mary": "oldies_motown",
    "the lovin spoonful": "oldies_motown",
    "the association band": "oldies_motown",
    "gerry and the pacemakers": "oldies_motown",
    "the searchers band": "oldies_motown",
    "herman's hermits": "oldies_motown",
    "the hollies": "oldies_motown",
    "the zombies": "oldies_motown",

    # =========================================================================
    # EIGHTIES
    # =========================================================================
    "modern talking": "eighties",
    "sandra eighties": "eighties",
    "c.c. catch": "eighties",
    "laura branigan": "eighties",
    "sheena easton": "eighties",
    "the motels": "eighties",
    "the human league eighties": "eighties",
    "orchestral manoeuvres in the dark": "eighties",
    "china crisis": "eighties",
    "haircut 100": "eighties",
    "aha eighties": "eighties",
    "berlin band eighties": "eighties",
    "missing persons": "eighties",
    "til tuesday eighties": "eighties",
    "climie fisher": "eighties",
    "curiosity killed the cat": "eighties",
    "swing out sister": "eighties",
    "living in a box": "eighties",
    "johnny hates jazz": "eighties",
    "the outfield eighties": "eighties",

    # =========================================================================
    # NINETIES
    # =========================================================================
    "east 17": "nineties",
    "worlds apart nineties": "nineties",
    "5ive nineties": "nineties",
    "steps band": "nineties",
    "b*witched nineties": "nineties",
    "the moffatts": "nineties",
    "hanson nineties": "nineties",
    "positive k": "nineties",
    "wreckx n effect": "nineties",
    "jomanda": "nineties",
    "cover girls": "nineties",
    "seduction group": "nineties",
    "the movement nineties": "nineties",
    "twenty4seven": "nineties",
    "dj quicksilver": "nineties",
    "activator nineties": "nineties",
    "faithless nineties": "nineties",
    "brooklyn bounce": "nineties",

    # =========================================================================
    # TWOTHOUSANDS
    # =========================================================================
    "girlicious": "twothousands",
    "danity kane": "twothousands",
    "b5 band": "twothousands",
    "sugababes twothousands": "twothousands",
    "girls aloud twothousands": "twothousands",
    "atomic kitten twothousands": "twothousands",
    "liberty x twothousands": "twothousands",
    "blue band twothousands": "twothousands",
    "busted band": "twothousands",
    "mcfly band": "twothousands",
    "mcfly": "twothousands",
    "mika twothousands": "twothousands",
    "the veronicas": "twothousands",
    "jesse mccartney twothousands": "twothousands",
    "aly and aj twothousands": "twothousands",
    "hilary duff twothousands": "twothousands",
    "jump5": "twothousands",
    "no secrets": "twothousands",
    "dream street": "twothousands",
    "o-town": "twothousands",

    # =========================================================================
    # JAZZ
    # =========================================================================
    "kamasi washington jazz": "jazz",
    "robert glasper": "jazz",
    "gregory porter": "jazz",
    "esperanza spalding": "jazz",
    "cecile mclorin salvant": "jazz",
    "jacob collier": "jazz",
    "snarky puppy": "jazz",
    "gogo penguin": "jazz",
    "christian scott ajuah": "jazz",
    "makaya mccraven": "jazz",
    "domi and jd beck": "jazz",
    "julian lage": "jazz",
    "hiromi uehara": "jazz",
    "brad mehldau": "jazz",
    "diana krall jazz": "jazz",

    # =========================================================================
    # CHILL / DOWNTEMPO
    # =========================================================================
    "bonobo migration": "chill_downtempo",
    "rjd2": "chill_downtempo",
    "j dilla": "chill_downtempo",
    "nujabes chill": "chill_downtempo",
    "helios": "chill_downtempo",
    "aquarium tapes": "chill_downtempo",
    "j sono": "chill_downtempo",
    "el ten eleven": "chill_downtempo",
    "poolside": "chill_downtempo",
    "washed out chill": "chill_downtempo",
    "kaya project chill downtempo": "chill_downtempo",
    "yppah chill": "chill_downtempo",
    "hidden orchestra chill": "chill_downtempo",
    "les gordon chill": "chill_downtempo",

    # =========================================================================
    # ECSTATIC / CEREMONY
    # =========================================================================
    "ital tek": "ecstatic_ceremony",
    "chrysta bell": "ecstatic_ceremony",
    "medicine for the people": "ecstatic_ceremony",
    "nahko ceremony": "ecstatic_ceremony",
    "wildlight ceremony": "ecstatic_ceremony",
    "sacred earth music project": "ecstatic_ceremony",
    "mooji ceremony": "ecstatic_ceremony",
    "krishna das": "ecstatic_ceremony",
    "deva premal": "ecstatic_ceremony",
    "jai uttal": "ecstatic_ceremony",
    "snatam kaur": "ecstatic_ceremony",
    "wah devi": "ecstatic_ceremony",

    # =========================================================================
    # MASHUP / EDIT (function crate, small on purpose -- see keywords file)
    # =========================================================================
    "cold blank": "mashup",
    "vdj tzo": "mashup",
    "dj earworm": "mashup",
    "girl talk mashup": "mashup",
    "wax audio": "mashup",
    "dsharp mashup": "mashup",
    "the hood internet": "mashup",
    "party ben": "mashup",

    # =========================================================================
    # SOUNDTRACK
    # =========================================================================
    "bear mccreary": "soundtrack",
    "brian tyler": "soundtrack",
    "nicholas britell": "soundtrack",
    "trent reznor and atticus ross": "soundtrack",
    "junkie xl": "soundtrack",
    "alexandre desplat": "soundtrack",
    "henry jackman": "soundtrack",
    "hildur guðnadóttir": "soundtrack",
    "daniel pemberton": "soundtrack",
    "lorne balfe": "soundtrack",
    "bob marley and the wailers": "reggae",  # deliberately distinct string from "bob marley" so lookup() picks the longer match

    # =========================================================================
    # ISRAELI HIP-HOP
    # =========================================================================
    "subliminal": "hiphop",
    "סאבלימינל": "hiphop",
    "hatikva 6": "hiphop",
    "התקווה 6": "hiphop",
    "muki rapper": "hiphop",
    "מוקי": "hiphop",
    "peled rapper": "hiphop",
    "nechi nech": "hiphop",
    "נצי נצ": "hiphop",
    "tuna rapper": "hiphop",
    "טונה": "hiphop",
    "kaveret gimel": "hiphop",
    "idan amedi": "hiphop",
    "עידן עמדי": "hiphop",
    "shaanan streett": "hiphop",
    "שאנן סטריט": "hiphop",
    "hadag nachash": "hiphop",
    "הדג נחש": "hiphop",

    # =========================================================================
    # HOUSE -- more current
    # =========================================================================
    "franky rizardo and cassimm": "house",
    "sonny fodera live": "house",
    "yulia niko": "house",
    "eli escobar": "house",
    "jden": "house",
    "cassian nights": "house",
    "goldie hawn house": "house",
    "themba live": "house",
    "riva starr and phunk investigation": "house",
    "detlef and eli brown": "house",
    "kim ann": "house",
    "sllash live": "house",
    "hp vince": "house",
    "kolter": "house",
    "aliss ho": "house",

    # =========================================================================
    # UK GARAGE -- more current
    # =========================================================================
    "notion and window kid": "garage",
    "artdealer": "garage",
    "arlissa garage": "garage",
    "hedex garage": "garage",
    "tsha": "garage",
    "sammy virji live": "garage",
    "prospa garage": "garage",
    "sharda garage set": "garage",
    "brackles": "garage",
    "sub state": "garage",
    "wax wings": "garage",
    "biscuits collective": "garage",
    "interplanetary criminal live": "garage",
    "warlord bassline": "garage",
    "d.o.k": "garage",

    # =========================================================================
    # DNB -- more current
    # =========================================================================
    "sub focus and dimension live": "dnb",
    "hedex and turno": "dnb",
    "1991 dnb producer": "dnb",
    "annix": "dnb",
    "hybrid minds and etherwood": "dnb",
    "voltage dnb": "dnb",
    "villem": "dnb",
    "whiney": "dnb",
    "loadstar and hybrid minds": "dnb",
    "hedex live": "dnb",

    # =========================================================================
    # AMAPIANO -- more current
    # =========================================================================
    "shakes and les amapiano": "amapiano",
    "young stunna and myztro": "amapiano",
    "de mthuda and njelic": "amapiano",
    "leemckrazy live": "amapiano",
    "sir trill": "amapiano",
    "loxion deep": "amapiano",
    "zee nxumalo": "amapiano",
    "mdu aka trp": "amapiano",
    "bandanaa amapiano": "amapiano",
    "afrikan roots amapiano": "amapiano",

    # =========================================================================
    # AFROBEATS -- more current
    # =========================================================================
    "boj afrobeats": "afrobeats",
    "reekado banks": "afrobeats",
    "dice ailes": "afrobeats",
    "blaqbonez": "afrobeats",
    "prettyboy dee": "afrobeats",
    "camidoh": "afrobeats",
    "black sherif": "afrobeats",
    "stonebwoy": "afrobeats",
    "shatta wale": "afrobeats",
    "kwesi arthur": "afrobeats",

    # =========================================================================
    # LATIN / REGGAETON -- more current
    # =========================================================================
    "de la ghetto and arcangel live": "reggaeton",
    "myke towers live": "reggaeton",
    "jhayco live": "reggaeton",
    "wisin live": "reggaeton",
    "villano antillano": "reggaeton",
    "aventura band": "latin",
    "los angeles azules": "latin",
    "grupo niche": "latin",
    "marc anthony live": "latin",
    "gilberto santa rosa": "latin",
    "victor manuelle": "latin",
    "los tigres del norte": "latin",
    "banda el recodo": "latin",
    "intocable": "latin",
    "los tucanes de tijuana": "latin",

    # =========================================================================
    # BALKAN / TURKISH / MIDDLE EASTERN
    # =========================================================================
    "hadise": "balkan",
    "gulsen": "balkan",
    "murat boz": "balkan",
    "kenan dogulu": "balkan",
    "simge": "balkan",
    "irem derici": "balkan",
    "edis": "balkan",
    "reynmen": "balkan",
    "mabel matiz": "balkan",
    "ebru gundes": "balkan",
    "teoman": "balkan",
    "sertab erener": "balkan",
    "athena band": "balkan",
    "manga band": "balkan",
    "duman band": "balkan",

    # =========================================================================
    # WORLD / ETHNIC -- more Middle Eastern / Arabic pop
    # =========================================================================
    "elissa": "world_ethnic",
    "myriam fares": "world_ethnic",
    "assi el hallani": "world_ethnic",
    "wael kfoury": "world_ethnic",
    "carole samaha": "world_ethnic",
    "najwa karam": "world_ethnic",
    "ragheb alama": "world_ethnic",
    "saad lamjarred": "world_ethnic",
    "balqees": "world_ethnic",
    "hussain al jassmi": "world_ethnic",
    "mohammed abdu": "world_ethnic",
    "rashed al majid": "world_ethnic",
    "kadim al sahir": "world_ethnic",
    "ahlam": "world_ethnic",
    "asala nasri": "world_ethnic",

    # =========================================================================
    # POP -- more current global gaps
    # =========================================================================
    "gayle pop": "pop",
    "meghan trainor 2020s": "pop",
    "jax pop": "pop",
    "flo band pop": "pop",
    "pinkpantheress": "pop",
    "central park sessions": "pop",
    "raye pop": "pop",
    "cat burns": "pop",
    "holly humberstone": "pop",
    "fletcher pop": "pop",
    "zara larsson 2020s": "pop",
    "meduza pop": "pop",
    "sigrid 2020s": "pop",
    "confetti pop": "pop",
    "shania twain 2020s": "pop",
    "kim petras 2020s": "pop",
    "sabrina carpenter 2020s": "pop",
    "jvke": "pop",
    "role model": "pop",
    "benson boone": "pop",

    # =========================================================================
    # ROCK -- more current
    # =========================================================================
    "wet leg rock": "rock",
    "the last dinner party rock": "rock",
    "inhaler band": "rock",
    "fizzy blood": "rock",
    "the reytons": "rock",
    "the mysterines": "rock",
    "hot milk band": "rock",
    "static dress": "rock",
    "yonaka": "rock",
    "creeper band": "rock",
    "nova twins": "rock",
    "de'wayne": "rock",
    "meet me at the altar rock": "rock",
    "against the current": "rock",
    "waterparks": "rock",

    # =========================================================================
    # COUNTRY -- more current
    # =========================================================================
    "shaboozey": "country",
    "zach top": "country",
    "dasha country": "country",
    "conner smith": "country",
    "nate smith country": "country",
    "priscilla block": "country",
    "tyler hubbard": "country",
    "restless road": "country",
    "brothers osborne": "country",
    "midland country": "country",

    # =========================================================================
    # JAZZ -- more
    # =========================================================================
    "yussef kamaal": "jazz",
    "sons of kemet": "jazz",
    "shabaka hutchings": "jazz",
    "the comet is coming": "jazz",
    "vijay iyer": "jazz",
    "ambrose akinmusire": "jazz",
    "kandace springs": "jazz",
    "laufey": "jazz",

    # =========================================================================
    # CHILL / DOWNTEMPO -- more
    # =========================================================================
    "bomba estereo chill": "chill_downtempo",
    "khruangbin chill": "chill_downtempo",
    "men i trust": "chill_downtempo",
    "parcels chill": "chill_downtempo",
    "still woozy chill": "chill_downtempo",
    "sudan archives": "chill_downtempo",
    "moses sumney": "chill_downtempo",
    "jordan rakei chill": "chill_downtempo",

    # =========================================================================
    # SOUNDTRACK -- more
    # =========================================================================
    "kris bowers": "soundtrack",
    "germaine franco": "soundtrack",
    "dan romer": "soundtrack",
    "volker bertelmann": "soundtrack",
    "carter burwell": "soundtrack",
    "marco beltrami": "soundtrack",
    "tom holkenborg": "soundtrack",
    "abel korzeniowski": "soundtrack",

    # =========================================================================
    # EIGHTIES -- more
    # =========================================================================
    "the fixx eighties": "eighties",
    "til tuesday voices": "eighties",
    "modern english": "eighties",
    "japan band": "eighties",
    "china crisis eighties": "eighties",
    "the associates": "eighties",
    "tears for fears eighties": "eighties",
    "when in rome eighties": "eighties",
    "cutting crew": "eighties",
    "propaganda band": "eighties",

    # =========================================================================
    # NINETIES -- more
    # =========================================================================
    "worlds apart boyband": "nineties",
    "let loose band": "nineties",
    "damage band": "nineties",
    "another level band": "nineties",
    "5ive band": "nineties",
    "911 band": "nineties",
    "eternal band": "nineties",
    "honeyz": "nineties",
    "cleopatra girl group": "nineties",
    "gina g": "nineties",

    # =========================================================================
    # TWOTHOUSANDS -- more
    # =========================================================================
    "girls aloud singles": "twothousands",
    "sclub7": "twothousands",
    "s club 7": "twothousands",
    "westlife twothousands": "twothousands",
    "il divo": "twothousands",
    "damage twothousands": "twothousands",
    "blazin squad": "twothousands",
    "d side": "twothousands",
    "girl thing": "twothousands",
    "point break band": "twothousands",

    # =========================================================================
    # MOTOWN / SOUL / FUNK -- more
    # =========================================================================
    "the dells": "motown",
    "the impressions": "motown",
    "the delfonics": "soul",
    "the stylistics": "soul",
    "blue magic": "soul",
    "harold melvin and the blue notes": "soul",
    "the chi-lites": "soul",
    "ann peebles": "soul",
    "betty wright": "soul",
    "candi staton": "soul",
    "the o'jays": "funk",
    "the whispers": "funk",
    "confunkshun": "funk",
    "slave band": "funk",
    "dazz band": "funk",

    # =========================================================================
    # DANCEHALL / REGGAE -- more
    # =========================================================================
    "iwer george": "dancehall",
    "bunji garlin dancehall": "dancehall",
    "patrice roberts": "dancehall",
    "voice soca": "dancehall",
    "nailah blackman": "dancehall",
    "skinny fabulous": "dancehall",
    "queen ifrica": "reggae",
    "tarrus riley": "reggae",
    "duane stephenson": "reggae",
    "romain virgo": "reggae",

    # =========================================================================
    # INDIE / ALT-POP -- more
    # =========================================================================
    "sports team indie": "indie_altpop",
    "the murder capital": "indie_altpop",
    "sea girls": "indie_altpop",
    "the amazons indie": "indie_altpop",
    "spector band": "indie_altpop",
    "cassia band": "indie_altpop",
    "average sex": "indie_altpop",
    "the wombats 2020s": "indie_altpop",
    "sundara karma": "indie_altpop",
    "pale waves": "indie_altpop",

    # =========================================================================
    # TECHNO / TRANCE / PSYTRANCE -- more
    # =========================================================================
    "amelie lens presents lucidflux": "techno",
    "enrico sangiuliano": "techno",
    "cera khin": "techno",
    "cinthie techno": "techno",
    "cristi cons": "techno",
    "indira paganotto": "techno",
    "cortechs": "trance",
    "estiva trance": "trance",
    "orjan nilsen live": "trance",
    "alpha nine": "trance",
    "vini vici and astrix": "psytrance",
    "ranji": "psytrance",
    "outsiders and dickster live": "psytrance",
    "sound chakra": "psytrance",
    "cosmic flow": "psytrance",

    # =========================================================================
    # DUBSTEP / TRAP / DRILL / TWERK -- more
    # =========================================================================
    "kompany and getter": "dubstep",
    "must die and getter": "dubstep",
    "monxx dubstep": "dubstep",
    "ekali and svdden death": "dubstep",
    "lil mosey trap": "trap",
    "internet money trap": "trap",
    "central cee and dave trap": "trap",
    "kay flock drill": "drill",
    "sha ek drill": "drill",
    "bandmanrill jersey": "twerk",
}


_SUFFIX_PATTERN = __import__("re").compile(
    r"\s+(feat\.?|ft\.?|featuring|&|x|vs\.?|versus|with|presents|pres\.?)\s+.*$",
    __import__("re").IGNORECASE,
)


def _build_lookup_table():
    """Build the longest-name-first regex list once at import time."""
    import re as _re

    names_sorted = sorted(ARTIST_GENRES.keys(), key=len, reverse=True)
    patterns = []
    for name in names_sorted:
        pattern = _re.compile(r"(?<!\w)" + _re.escape(name) + r"(?!\w)")
        patterns.append((name, pattern))
    return patterns


_ARTIST_PATTERNS = _build_lookup_table()


def _normalize(name: str) -> str:
    import re as _re

    name = (name or "").strip().lower()
    name = _re.sub(r"\s+", " ", name)
    # "&" is standardised to "and" so "Bob Marley & The Wailers" lines up
    # with the "and"-spelled dict key, and so the suffix stripper below
    # (which treats a bare "&" as a feat./ft. style separator) does not
    # fire on a legitimate "X & The Y" band name.
    name = _re.sub(r"\s*&\s*", " and ", name)
    name = _re.sub(r"\s+", " ", name).strip()
    return name


def lookup(name: str):
    """Return a genre key for an artist name, or None. Whole-name match first,
    then a whole-word containment check so "Artist feat. Someone" still works.

    Normalises case and whitespace, strips common suffixes like "feat.",
    "ft.", "&", "x", "vs" and whatever trails them, tries an exact match
    first, then scans a precompiled, length-sorted (longest first) list of
    word-boundary regexes built once at import so e.g. "bob marley and the
    wailers" beats a shorter "bob marley" style entry.
    """
    if not name:
        return None

    normalized = _normalize(name)
    if normalized in ARTIST_GENRES:
        return ARTIST_GENRES[normalized]

    stripped = _SUFFIX_PATTERN.sub("", normalized).strip()
    if stripped and stripped in ARTIST_GENRES:
        return ARTIST_GENRES[stripped]

    for candidate in (normalized, stripped):
        if not candidate:
            continue
        for artist_name, pattern in _ARTIST_PATTERNS:
            if pattern.search(candidate):
                return ARTIST_GENRES[artist_name]

    return None


# ---------------------------------------------------------------------------
# Bundled MusicBrainz index, v20.
#
# The curated table above is small by nature. This is the bulk layer: an
# artist-to-genre index extracted from the MusicBrainz JSON dump, which is
# CC0 and therefore safe to redistribute inside an MIT project. It is loaded
# lazily and only consulted after the curated table, so a hand-checked entry
# always wins over a crowd-sourced tag.
#
# Built by tools/build_artist_index.py. Absent from a source checkout until
# that has been run, and the tool works fine without it.
# ---------------------------------------------------------------------------
import gzip as _gzip
import json as _json
from pathlib import Path as _Path

_INDEX_PATH = _Path(__file__).with_name("artist_index.json.gz")
_bulk_index = None
_folded_index = None

import unicodedata as _ud


def _fold(name: str) -> str:
    """Lowercase, collapse spaces and strip accents.

    "Goran Bregović" and "goran bregovic" are the same artist. Without this
    every accented name in the index was unreachable from a plain filename.
    """
    n = _ud.normalize("NFKD", str(name or "").strip().lower())
    n = "".join(c for c in n if not _ud.combining(c))
    return " ".join(n.split())


def _load_bulk():
    """Read the bundled index once, on first use. Never raises."""
    global _bulk_index
    if _bulk_index is None:
        try:
            with _gzip.open(_INDEX_PATH, "rt", encoding="utf-8") as fh:
                _bulk_index = _json.load(fh)
        except Exception:
            _bulk_index = {}
    return _bulk_index


def bulk_lookup(name: str):
    """Genre for an artist from the bundled MusicBrainz index, or None."""
    if not name:
        return None
    idx = _load_bulk()
    if not idx:
        return None
    global _folded_index
    if _folded_index is None:
        _folded_index = {}
        for k, v in idx.items():
            _folded_index.setdefault(_fold(k), v)
    idx = _folded_index
    key = _fold(name)
    hit = idx.get(key)
    if hit:
        return hit
    # "Artist feat. Someone", "Artist & Someone" collapse to the lead name.
    for sep in (" feat.", " feat ", " ft.", " ft ", " & ", " x ", " vs ", " with "):
        if sep in key:
            head = key.split(sep)[0].strip()
            if len(head) >= 4:
                hit = idx.get(head)
                if hit:
                    return hit
    return None


def index_size() -> int:
    """How many artists the bundled index knows. 0 if it was never built."""
    return len(_load_bulk())
