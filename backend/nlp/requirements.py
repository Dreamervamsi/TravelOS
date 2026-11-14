from ._shared import *
from .passengers import *
from .passengers import _num
from .passengers import _NUMTOK
# ----------------------------------------------------------------------------
_REQ_NEG_BEFORE = re.compile(
    r"(?:\b(?:no|not|without|never|nor|neither|zero)|(?:don'?t|doesn'?t|do\s+not|does\s+not|n'?t)\s+"
    r"(?:need|want|require|have|carry|prefer))\s+(?:\w+\s+){0,2}$")
_REQ_NEG_AFTER = re.compile(
    r"^\s*(?:(?:is|are)\s+)?(?:not|isn'?t|aren'?t)\s+(?:needed|required|necessary|a\s+must)|"
    r"^\s*(?:not\s+needed|not\s+required|nahi\s+chahiye)")


def _req_negated(t, s, e):
    return bool(_REQ_NEG_BEFORE.search(t[max(0, s - 35):s]) or _REQ_NEG_AFTER.match(t[e:]))


def _tag(x):
    return re.sub(r"[\s\-]+", "_", str(x).strip().lower())


def _collect_tags(text, table):
    t = text.lower()
    out = []
    for tag, pat in table:
        for m in re.finditer(pat, t):
            if not _req_negated(t, m.start(), m.end()):
                if tag not in out:
                    out.append(tag)
                break
    return out or None


# ---- luggage
_LUG_MOD = (r"(?:(?:big|large|small|heavy|huge|extra|cabin|check(?:ed)?[\s\-]?in|hand|laptop|travel|medium|"
            r"bulky|duffel)\s+)*")
_LUG_NOUN = (r"(?:bags?|suitcases?|luggage|baggage|backpacks?|rucksacks?|trolleys?|boxes|box|cartons?|parcels?|"
             r"packages?|trunks?|duffels?|bundles?)")
_LUG_COUNT_RE = re.compile(_NUMTOK + r"\s*(?:pieces?\s+of\s+)?" + _LUG_MOD + _LUG_NOUN + r"\b", re.I)
_LUG_A_RE = re.compile(r"\b(?:a|an)\s+" + _LUG_MOD + r"(?:bag|suitcase|backpack|rucksack|trolley|duffel|box|trunk)\b", re.I)
_LUG_NONE_RE = re.compile(
    r"\b(?:no|zero|without|nil)\s+(?:any\s+)?(?:luggage|baggage|bags?)\b|\bnothing\s+to\s+carry\b|"
    r"\bnot\s+carrying\s+(?:any\s+)?(?:luggage|baggage|bags?)\b|\bnothing\s+but\s+myself\b", re.I)
_LUG_HEAVY_RE = re.compile(
    r"\b(?:heavy|bulky|huge|big|large|lots?\s+of|a\s+lot\s+of|loads?\s+of|plenty\s+of|too\s+much|overweight)\s+"
    r"(?:\w+\s+){0,2}?(?:luggage|baggage|bags?|suitcases?|boxes|trunks?|stuff|items)\b", re.I)
_LUG_EXTRA_RE = re.compile(r"\b(?:extra|additional|excess)\s+(?:\w+\s+)?(?:luggage|baggage|bags?)\b", re.I)
_LUG_OVERSIZED_RE = re.compile(
    r"\b(?:bicycles?|cycles?|bikes?|motorcycles?|scooters?|guitars?|violins?|keyboards?|instruments?|surfboards?|"
    r"golf\s+kit|sports\s+kit|cricket\s+kit|strollers?|prams?|oversized|over[\s\-]sized)\b", re.I)
_LUG_LIGHT_RE = re.compile(
    r"\b(?:light\s+(?:luggage|baggage|bag)|little\s+(?:luggage|baggage)|minimal\s+(?:luggage|baggage)|"
    r"hand\s+(?:luggage|baggage|bag)|cabin\s+(?:luggage|baggage|bag)|"
    r"(?:just|only)\s+(?:a|an|one)\s+(?:small\s+)?(?:backpack|laptop\s+bag|handbag|bag|rucksack)|"
    r"small\s+(?:bag|backpack)|backpack\s+only|travel(?:l?ing)?\s+light|"
    r"not\s+much\s+(?:luggage|baggage)|not\s+a\s+lot\s+of\s+(?:luggage|baggage))\b", re.I)
_LUG_WORD_RE = re.compile(r"\b(?:luggage|baggage|bags?|suitcases?)\b", re.I)


def extract_luggage(text):
    """-> tags like ['2_bags', 'heavy'] | ['light'] | ['none'] | ['oversized'] | ['has_luggage'] | None"""
    t = text.lower()
    if _LUG_NONE_RE.search(t):
        return ["none"]
    count = 0
    for rx in (_LUG_COUNT_RE, _LUG_A_RE):
        for m in rx.finditer(t):
            if not _req_negated(t, m.start(), m.end()):
                count += _num(m.group(1)) if rx is _LUG_COUNT_RE else 1
    found = [tag for tag, rx in (("heavy", _LUG_HEAVY_RE), ("extra_luggage", _LUG_EXTRA_RE),
                                 ("oversized", _LUG_OVERSIZED_RE), ("light", _LUG_LIGHT_RE))
             if any(not _req_negated(t, m.start(), m.end()) for m in rx.finditer(t))]
    tags = []
    if count and not (count == 1 and "light" in found):
        tags.append(f"{count}_bag{'s' if count > 1 else ''}")
    tags += found
    if not tags and any(not _req_negated(t, m.start(), m.end()) for m in _LUG_WORD_RE.finditer(t)):
        tags.append("has_luggage")
    return tags or None


# ---- accessibility
_ACCESS_TABLE = [
    ("wheelchair", r"\bwheel[\s\-]?chairs?\b"),
    ("mobility_assistance",
     r"\b(?:disabled|disability|handicapped|physically\s+challenged|differently[\s\-]abled|"
     r"mobility\s+(?:issues?|problems?|assistance|support)|crutch(?:es)?|walker|walking\s+(?:difficulty|problems?|stick)|"
     r"knee\s+(?:pain|problems?|issues?)|can'?t\s+climb|cannot\s+climb|can'?t\s+walk|cannot\s+walk|limited\s+mobility|"
     r"need\s+(?:some\s+)?assistance|need\s+help\s+(?:boarding|climbing))\b"),
    ("senior_citizen",
     r"\b(?:elderly|senior\s+citizens?|old\s+(?:age\s+)?(?:parents?|mother|father|man|woman|lady|couple|person|people)|"
     r"aged\s+(?:parents?|mother|father|person)|grand(?:mother|father|ma|pa|parents?)|old\s+folks)\b"),
    ("visually_impaired", r"\b(?:blind|visually\s+impaired|low\s+vision|vision\s+impair\w*)\b"),
    ("hearing_impaired", r"\b(?:deaf|hearing\s+impair\w*|hard\s+of\s+hearing)\b"),
    ("pregnant", r"\b(?:pregnant|pregnancy|expecting\s+mother)\b"),
    ("with_infant", r"\b(?:infants?|newborns?|toddlers?|babies|baby)\b"),
    ("low_floor_access", r"\b(?:low[\s\-]floor|ramp|easy\s+(?:boarding|access)|ground\s+floor)\b"),
    ("medical_assistance", r"\b(?:stretcher|oxygen|medical\s+(?:assistance|emergency|condition|help))\b"),
    ("service_animal", r"\b(?:service|guide)\s+dog\b|\bseeing[\s\-]eye\b"),
]


def extract_accessibility(text):
    return _collect_tags(text, _ACCESS_TABLE)


# ---- comfort preferences
_COMFORT_TABLE = [
    ("window_seat", r"\bwindow\b"),
    ("aisle_seat", r"\baisle\b"),
    ("front_seat", r"\bfront\s+(?:seats?|rows?|side)\b|\bfirst\s+row\b|\bnear\s+(?:the\s+)?driver\b"),
    ("back_seat", r"\b(?:back|rear|last)\s+(?:seats?|rows?|side)\b"),
    ("lower_berth", r"\blower\s+(?:berth|bunk|deck|sleeper)\b"),
    ("upper_berth", r"\bupper\s+(?:berth|bunk|deck|sleeper)\b"),
    ("single_berth", r"\bsingle\s+(?:berth|sleeper|bunk)\b"),
    ("charging_point", r"\b(?:charg(?:ing|er)(?:\s+(?:point|port|socket))?|usb\s+(?:port|charging)|power\s+(?:outlet|socket|point))\b"),
    ("wifi", r"\bwi[\s\-]?fi\b"),
    ("blanket", r"\b(?:blankets?|pillows?|bedsheets?)\b"),
    ("legroom", r"\b(?:leg[\s\-]?room|extra\s+leg\s+space|leg[\s\-]?space|stretch\s+(?:my\s+)?legs)\b"),
    ("washroom", r"\b(?:washrooms?|toilets?|restrooms?|lavatory|attached\s+bath)\b"),
    ("entertainment", r"\b(?:entertainment|movies?|tv|screens?)\b"),
    ("snacks", r"\b(?:snacks?|meals?|food|refreshments?|water\s+bottles?|dinner\s+stop|breakfast)\b"),
    ("quiet", r"\b(?:quiet|silent|peaceful|low\s+noise|no\s+(?:loud\s+)?(?:music|noise))\b"),
    ("ladies_seat", r"\b(?:ladies|women'?s?|female)[\s\-]*(?:seat|only|quota|coach)\b|\bwomen[\s\-]only\b"),
    ("direct", r"\b(?:direct|non[\s\-]?stop|no\s+(?:stops?|changes?|transfers?)|without\s+(?:any\s+)?(?:stops?|changes?))\b"),
    ("clean", r"\b(?:clean|hygienic|well[\s\-]maintained|sanitized)\b"),
    ("motion_sickness", r"\b(?:motion\s+sickness|travel\s+sickness|vomit\w*|nausea)\b"),
]


def extract_comfort_preferences(text):
    return _collect_tags(text, _COMFORT_TABLE)


# ----------------------------------------------------------------------------
# 4) TIME SEMANTICS: departure preference vs arrival deadline

__all__ = [name for name in globals() if not name.startswith("__")]
