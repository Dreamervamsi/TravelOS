from ._shared import *

# ----------------------------------------------------------------------------
_CITY_DATA = """
Hyderabad|hyd,hydrabad,hyderbad,hydrebad
Secunderabad|secunderabad
Guntur
Vijayawada|bezawada,vja
Tirupati|tirupathi,tirumala
Nellore
Kurnool
Warangal
Ongole
Rajahmundry|rajamahendravaram,rajamundry
Visakhapatnam|vizag,vishakhapatnam,visakapatnam
Kakinada
Anantapur|ananthapur
Kadapa|cuddapah
Eluru
Nizamabad
Karimnagar
Khammam
Adilabad
Mahabubnagar|mahbubnagar
Nalgonda
Tenali
Machilipatnam|bandar
Chittoor
Srikakulam
Vizianagaram
Bhimavaram
Chennai|madras,chenai,chennnai
Coimbatore|kovai,cbe
Madurai|mdu
Salem
Vellore
Tiruchirappalli|trichy,tiruchi,tiruchirapalli
Tirunelveli|nellai
Thanjavur|tanjore
Erode
Tiruppur|tirupur
Kanyakumari|cape comorin
Nagercoil
Hosur
Dindigul
Karur
Namakkal
Kumbakonam
Rameswaram
Ooty|udhagamandalam,ootacamund
Kodaikanal|kodai
Cuddalore
Pollachi
Thoothukudi|tuticorin
Puducherry|pondicherry,pondy
Bengaluru|bangalore,blore,blr,bglr,bengalooru,banglore,bengalore,bangalor
Mysuru|mysore
Mangaluru|mangalore
Hubballi|hubli
Dharwad
Belagavi|belgaum
Kalaburagi|gulbarga
Ballari|bellary
Shivamogga|shimoga
Davanagere|davangere
Tumakuru|tumkur
Udupi
Madikeri|coorg,kodagu
Hassan
Chikkamagaluru|chikmagalur
Hosapete|hospet
Bidar
Vijayapura|bijapur
Raichur
Mandya
Gokarna
Hampi
Sakleshpur
Karwar
Kochi|cochin,ernakulam,ekm
Thiruvananthapuram|trivandrum,tvm
Kozhikode|calicut
Thrissur|trichur
Kannur|cannanore
Kollam|quilon
Alappuzha|alleppey
Palakkad|palghat
Kottayam
Munnar
Kasaragod
Malappuram
Guruvayur
Mumbai|bombay
Pune|poona
Nagpur
Nashik|nasik
Aurangabad|sambhajinagar,chhatrapati sambhajinagar
Kolhapur
Solapur
Shirdi
Satara
Sangli
Amravati
Lonavala
Mahabaleshwar
Navi Mumbai
Thane
Ratnagiri
Akola
Jalgaon
Nanded
Latur
Goa
Panaji|panjim
Margao|madgaon
Ahmedabad|amdavad,ahmadabad
Surat
Vadodara|baroda
Rajkot
Bhavnagar
Jamnagar
Gandhinagar
Junagadh
Bhuj
Dwarka
Somnath
Jaipur
Udaipur
Jodhpur
Jaisalmer
Ajmer
Bikaner
Kota
Pushkar
Mount Abu
Alwar
Chittorgarh|chittor
Bharatpur
Sikar
Bhopal
Indore
Gwalior
Jabalpur
Ujjain
Raipur
Bilaspur
Bhilai
Rewa
Sagar
Satna
Delhi|new delhi,dilli
Noida
Gurugram|gurgaon
Ghaziabad
Faridabad
Lucknow
Kanpur
Agra
Varanasi|banaras,benares,kashi
Prayagraj|allahabad
Mathura
Vrindavan
Ayodhya
Meerut
Gorakhpur
Bareilly
Aligarh
Jhansi
Dehradun
Haridwar
Rishikesh
Nainital
Mussoorie
Manali
Shimla
Dharamshala
Kullu
Chandigarh
Amritsar
Ludhiana
Jalandhar
Patiala
Pathankot
Ambala
Karnal
Panipat
Hisar
Rohtak
Jammu
Srinagar
Leh
Katra
Kolkata|calcutta
Howrah
Siliguri
Darjeeling
Durgapur
Asansol
Patna
Gaya
Muzaffarpur
Bhagalpur
Ranchi
Jamshedpur
Dhanbad
Bokaro
Bhubaneswar|bhubaneshwar
Cuttack
Puri
Rourkela
Sambalpur
Guwahati
Shillong
Gangtok
Imphal
Agartala
Dibrugarh
Silchar
Port Blair
"""

CITY_ALIASES = {}
ALIAS_TO_CITY = {}
_ALIAS_RE = None
_FUZZY_KEYS = []
FUZZY_CUTOFF = 0.85   # catches "Bangalor", "Chenai", "Hyderbad", "Bengluru"


def _rebuild_city_index():
    global ALIAS_TO_CITY, _ALIAS_RE, _FUZZY_KEYS, _SPACY
    ALIAS_TO_CITY = {a: c for c, al in CITY_ALIASES.items() for a in al}
    alts = "|".join(re.escape(a) for a in sorted(ALIAS_TO_CITY, key=len, reverse=True))
    _ALIAS_RE = re.compile(r"(?<![A-Za-z])(" + alts + r")(?![A-Za-z])", re.I)
    _FUZZY_KEYS = [a for a in ALIAS_TO_CITY if len(a) >= 5 and " " not in a]
    _SPACY = None                                   # force PhraseMatcher rebuild


def register_city(canonical, aliases=(), rebuild=True):
    """Add (or extend) a city at runtime, e.g. register_city('Hosur', ['hosoor'])."""
    names = CITY_ALIASES.setdefault(canonical, [])
    for a in (canonical, *aliases):
        a = re.sub(r"\s+", " ", a.lower().strip())
        if a and a not in names:
            names.append(a)
    if rebuild:
        _rebuild_city_index()


def load_city_file(path):
    with open(path, "r", encoding="utf-8") as f:
        for canonical, aliases in json.load(f).items():
            register_city(canonical, aliases, rebuild=False)
    _rebuild_city_index()


for _line in _CITY_DATA.strip().splitlines():
    _canon, _, _al = _line.partition("|")
    register_city(_canon.strip(), [a for a in _al.split(",") if a], rebuild=False)
_rebuild_city_index()
if EXTRA_CITIES_PATH:
    load_city_file(EXTRA_CITIES_PATH)

_NON_CITY_WORDS = set("""
sleeper seater sleeping seating morning evening afternoon tomorrow tonight today budget before after
around maximum minimum passengers people persons tickets ticket please travel travelling traveling
leaving arrive arriving reach reaching price under within seats thanks hello night noon midnight
buses coach general ordinary express cheapest cheap sitting condition conditioned amount rupees
""".split())

_NON_CITY_CAPS = set("""
monday tuesday wednesday thursday friday saturday sunday january february march april may june july
august september october november december tomorrow today tonight next this the a an my our me us rs
inr ac non sleeper seater semi bus buses morning evening afternoon night noon midnight airport
station stand please also and with any some budget around about under latest early late india
sleeping seat seats ticket tickets people passengers
andhra pradesh telangana karnataka tamil nadu kerala maharashtra gujarat rajasthan punjab haryana
bihar odisha assam jharkhand chhattisgarh uttarakhand himachal bengal uttar madhya
""".split())

_UNKNOWN_CITY_RE = re.compile(
    r"\b(?i:from|to|towards?|reach(?:ing)?|arrive\s+(?:in|at)|arriving\s+(?:in|at)|into|for|"
    r"leaving|leave|via)\s+([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)\b")


def normalize_city(v):
    if v is None:
        return None
    s = re.sub(r"\s+", " ", re.sub(r"[^a-z ]", " ", str(v).lower())).strip()
    if s in ALIAS_TO_CITY:
        return ALIAS_TO_CITY[s]
    hit = difflib.get_close_matches(s, ALIAS_TO_CITY.keys(), n=1, cutoff=FUZZY_CUTOFF)
    return ALIAS_TO_CITY[hit[0]] if hit else str(v).strip().title()


def _overlaps(pos, spans):
    return any(s <= pos < e for s, e, *_ in spans)


def fuzzy_mentions(text, taken):
    """Typo-tolerant fallback for tokens that exact alias matching missed."""
    out = []
    for m in re.finditer(r"[A-Za-z]{5,}", text):
        w = m.group(0).lower()
        if _overlaps(m.start(), taken) or w in _NON_CITY_WORDS or w in ALIAS_TO_CITY:
            continue
        hit = difflib.get_close_matches(w, _FUZZY_KEYS, n=1, cutoff=FUZZY_CUTOFF)
        if hit and hit[0][0] == w[0]:
            out.append((m.start(), m.end(), ALIAS_TO_CITY[hit[0]]))
    return out


def unknown_city_mentions(text, taken, extra=()):
    """Cities missing from the gazetteer: capitalised words after from/to/..., or NER (GPE) spans."""
    out = list(extra)
    for m in _UNKNOWN_CITY_RE.finditer(text):
        toks = []
        for tok in m.group(1).split():
            if tok.lower() in _NON_CITY_CAPS:
                break
            toks.append(tok)
        if not toks:
            continue
        s = m.start(1)
        e = s + len(" ".join(toks))
        out.append((s, e, " ".join(toks).title()))
    res = []
    for s, e, c in out:
        if c.lower() in _NON_CITY_CAPS or c.lower() in _NON_CITY_WORDS:
            continue
        if any(not (e <= ts or s >= te) for ts, te, *_ in list(taken) + res):
            continue
        res.append((s, e, c))
    return res


def find_city_mentions_regex(text):
    ms = [(m.start(), m.end(), ALIAS_TO_CITY[m.group(1).lower()]) for m in _ALIAS_RE.finditer(text)]
    ms += fuzzy_mentions(text, ms)
    if len({c for *_, c in ms}) < 2:
        ms += unknown_city_mentions(text, ms)
    return sorted(ms)


# ---- role assignment ---------------------------------------------------------
_FILLER_TAIL = re.compile(r"(?:[\s,.]+(?:uh+|um+|hmm+|er+|like|ok|okay|yeah))*[\s,.]*$", re.I)
_ORIGIN_PREFIX = re.compile(
    r"\b(?:from|leaving|leave|leaves|left|departing(?:\s+from)?|departure\s+(?:from|point|city)?|"
    r"starting(?:\s+(?:from|at|point))?|starts?\s+(?:from|at)|out\s+of|origin|source|"
    r"pick(?:ing)?[\s\-]?up(?:\s+(?:at|from|in))?|boarding(?:\s+(?:at|from|in))?|board(?:\s+(?:at|from))?|"
    r"travell?ing\s+from|coming\s+from|returning\s+from|back\s+from)$", re.I)
_DEST_PREFIX = re.compile(
    r"\b(?:to|towards?|reach(?:es|ing|ed)?|into|arrive\s+(?:in|at)|arriving\s+(?:in|at)|arrival\s+(?:in|at)|"
    r"in|at|for|destination|drop(?:ping)?(?:\s+(?:at|in|off\s+at))?|going\s+to|heading\s+to|headed\s+to|"
    r"back\s+to|return(?:ing)?\s+to|get\s+to|getting\s+to)$", re.I)
_VIA_PREFIX = re.compile(r"\b(?:via|through|thru|passing(?:\s+through)?|stop(?:ping)?\s+(?:at|in)|halt\s+at|crossing)$", re.I)
_NEG_PREFIX = re.compile(r"\b(?:not|no|never|instead\s+of|rather\s+than|other\s+than|except|n't)$", re.I)
_ORIGIN_SUFFIX = re.compile(r"^\s*,?\s*(?:to\b|se\b|till\b|->|→|–|—|-)", re.I)
_DEST_SUFFIX = re.compile(r"^[\s,]*(?:ke\s+liye|ko|jana|jaana|ja\s+raha|tak|pahunchna|pahuchna)\b", re.I)
_CORRECTION_RE = re.compile(
    r"\b(i\s+mean|i\s+meant|actually|sorry|wait|instead|rather|correction|change\s+that|no\s+wait|make\s+that)\b", re.I)


def _classify_mention(text, s, e):
    before = _FILLER_TAIL.sub("", text[:s]).rstrip(" ,.")
    before = re.sub(r"\b(?:the|city\s+of|town\s+of)$", "", before.strip(), flags=re.I).rstrip(" ,.").lower()
    after = text[e:]
    if _NEG_PREFIX.search(before) or _VIA_PREFIX.search(before):
        return "skip"
    if _ORIGIN_PREFIX.search(before):
        return "origin"
    if _DEST_PREFIX.search(before):
        return "dest"
    if _ORIGIN_SUFFIX.match(after):                      # "Hyd to Blore", "Chennai se Bangalore", "A-B"
        return "origin"
    if _DEST_SUFFIX.match(after):
        return "dest"
    return "unresolved"


def _roles(text, mentions):
    origin = dest = None
    unresolved = []
    for s, e, city in mentions:
        role = _classify_mention(text, s, e)
        if role == "skip":
            continue
        if role == "origin":
            origin = origin or city
        elif role == "dest":
            dest = dest or city
        else:
            unresolved.append(city)
    return origin, dest, unresolved


def assign_roles(text, mentions):
    o, d, u = _roles(text, mentions)
    if o is None and d is None:
        if len(u) >= 2:
            o, d = u[0], u[1]
    elif o is None and u:
        o = u[0]
    elif d is None and u:
        d = u[0]
    return o, d


def _cities_core(text, mentions):
    """-> (origin, destination, head_roles). head_roles is set only when a self-correction was applied."""
    markers = list(_CORRECTION_RE.finditer(text))
    if not markers:
        o, d = assign_roles(text, mentions)
        return o, d, None
    last = markers[-1]
    head = [m for m in mentions if m[0] < last.start()]
    tail = [m for m in mentions if m[0] >= last.end()]
    if not tail:
        o, d = assign_roles(text, mentions)
        return o, d, None
    head_o, head_d = assign_roles(text, head) if head else (None, None)
    t_o, t_d, t_u = _roles(text, tail)
    if t_o is None and t_d is None:
        if len(t_u) >= 2:
            return t_u[0], t_u[1], (head_o, head_d)
        if len(t_u) == 1 and head:                      # replace the role of the city just corrected
            role = _classify_mention(text, head[-1][0], head[-1][1])
            o, d = (t_u[0], head_d) if role == "origin" else (head_o, t_u[0])
            return o, d, (head_o, head_d)
        o, d = assign_roles(text, mentions)
        return o, d, None
    u = list(t_u)
    if t_o is None and t_d is not None and u:
        t_o = u.pop(0)
    elif t_d is None and t_o is not None and u:
        t_d = u.pop(0)
    return t_o or head_o, t_d or head_d, (head_o, head_d)


def extract_cities(text, mentions, ctx=None):
    """Handles self-corrections: 'to Mysore, I mean Mysuru' / 'sorry, Chennai to Madurai'."""
    o, d, head = _cities_core(text, mentions)
    if ctx is not None:
        if head:
            if head[0] and o and head[0] != o:
                ctx.corrected.add("origin")
            if head[1] and d and head[1] != d:
                ctx.corrected.add("destination")
        _, _, unresolved = _roles(text, mentions)
        live = {c for s_, e_, c in mentions if _classify_mention(text, s_, e_) != "skip"}
        if o and d and o == d:
            ctx.amb("destination", "same_as_origin")
        elif o is None and d is None and len(unresolved) == 1:
            ctx.info["lone_city"] = unresolved[0]
            ctx.amb("origin", "role_unclear")
            ctx.amb("destination", "role_unclear")
        elif head is None and len(live) > 2:
            ctx.amb("destination", "multiple_cities")
    return o, d


# ----------------------------------------------------------------------------
# 5) SEAT TYPE and AC PREFERENCE (two independent slots)

__all__ = [name for name in globals() if not name.startswith("__")]
