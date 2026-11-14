import re
from ._shared import *
from .cities import *

# ----------------------------------------------------------------------------
_CORRECTION_RE = re.compile(
    r"\b(i\s+mean|i\s+meant|actually|sorry|wait|instead|rather|correction|change\s+that|no\s+wait|make\s+that)\b", re.I)

_NUMW = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
         "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
         "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20}
NUM_WORDS = _NUMW
_NUMW_HI = {"ek": 1, "do": 2, "teen": 3, "char": 4, "chaar": 4, "paanch": 5, "panch": 5,
            "chhe": 6, "che": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10}
_NUMTOK = r"(?<![\w.,:/₹\-])(\d{1,2}|" + "|".join(_NUMW) + r")\b(?![.,]\d)"

_MONTH_NAMES = {"jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3, "apr": 4,
                "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7, "aug": 8,
                "august": 8, "sep": 9, "sept": 9, "september": 9, "oct": 10, "october": 10,
                "nov": 11, "november": 11, "dec": 12, "december": 12}
MONTHS = _MONTH_NAMES
_MONTH_ALT = "|".join(sorted(MONTHS, key=len, reverse=True))

# Things a "headcount-looking" number must NOT be followed by (time, money, duration, date, distance)
_PAX_AFTER_BAD = (r"\s*(?::|\.\d|am\b|pm\b|a\.m|p\.m|rs\b|rupees?\b|inr\b|₹|k\b|hrs?\b|hours?\b|"
                  r"mins?\b|minutes?\b|days?\b|nights?\b|weeks?\b|months?\b|km\b|kms\b|kilomet|stops?\b|"
                  r"bags?\b|suitcases?\b|boxes\b|luggage\b|pieces?\b|parcels?\b|packages?\b|backpacks?\b|"
                  r"st\b|nd\b|rd\b|th\b|%|/-|o'?clock|(?:" + _MONTH_ALT + r")\b)")
_NOT_PAX_AFTER = r"(?!" + _PAX_AFTER_BAD + r")"

_MOD = (r"(?:(?:ac|non[\s\-]*ac|sleeper|seater|semi[\s\-]*sleeper|window|lower|upper|aisle|adult|senior|"
        r"full|more|extra|additional|confirmed|bus)\s+)*")
_PAX_NOUN = (r"(?:passengers?|pax|people|persons?|adults?|seats?|tickets?|members?|travell?ers?|"
             r"of\s+us|guys|folks|heads|berths?|seniors?)")
_PAX_NOUN_RE = re.compile(_NUMTOK + r"\s*(?:-\s*)?" + _MOD + _PAX_NOUN + r"\b", re.I)
_PAX_PARTY_RE = re.compile(
    r"\b(?:we\s+are|we're|we\s+r|there\s+are|party\s+of|group\s+of|family\s+of|team\s+of|gang\s+of|total\s+of)\s+"
    + _NUMTOK + _NOT_PAX_AFTER, re.I)
_PAX_VERB_RE = re.compile(
    r"\b(?:for|so|book(?:ing)?|need|want|require|reserve|get|buy|take|make\s+it)\s+(?:for\s+)?"
    + _NUMTOK + _NOT_PAX_AFTER, re.I)
_PAX_HI_RE = re.compile(r"\b(" + "|".join(_NUMW_HI) + r")\s+(?:log|logon|aadmi|sawari|seats?|tickets?|passengers?)\b", re.I)
_ADULT_RE = re.compile(_NUMTOK + r"\s*(?:adults?|seniors?|men|women|gents|ladies)\b", re.I)
_CHILD_RE = re.compile(_NUMTOK + r"\s*(?:kids?|children|child|boys?|girls?|minors?)\b", re.I)
_PAX_COUPLE_RE = re.compile(
    r"\bboth\s+of\s+us\b|\bcouple\b(?!\s+of\s+(?:days?|hours?|nights?|weeks?|months?|minutes?|mins?))", re.I)
_PAX_SOLO_RE = re.compile(
    r"\b(?:just\s+me|only\s+me|solo|alone|myself|single\s+(?:passenger|traveller|traveler|seat|ticket)|"
    r"one\s+person|1\s+person)\b", re.I)

_REL = (r"(?:wife|husband|spouse|partner|friend|kid|child|son|daughter|brother|sister|mother|father|mom|mum|dad|"
        r"parents|colleague|cousin|boss|girlfriend|boyfriend|fiance|fiancee|uncle|aunt|grandmother|grandfather|"
        r"grandma|grandpa|roommate|relative|neighbou?r|baby|bro)")
_UNKNOWN_GROUP = r"(?:friends|kids|children|colleagues|cousins|relatives|family|team|group|siblings|roommates)"
_ITEM = (r"(?:(?:my|our)\s+(?:" + _REL + r"|" + _UNKNOWN_GROUP + r")\b"
         r"|\d{1,2}\s+(?:more\s+)?(?:friends?|kids?|children|colleagues?|cousins?|relatives?|parents|siblings|"
         r"brothers?|sisters?|people)\b"
         r"|(?:a|one)\s+(?:friend|kid|child|colleague|cousin|baby)\b)")
_ITEM_RE = re.compile(_ITEM, re.I)
_PAX_GROUP_ME_RE = re.compile(
    r"\b(?:me|myself|i)\b((?:\s*(?:,|and|&|\+|with|plus)\s*" + _ITEM + r")+)", re.I)
_PAX_GROUP_WITH_RE = re.compile(
    r"\bwith\s+(" + _ITEM + r"(?:\s*(?:,|and|&|\+|plus)\s*" + _ITEM + r")*)", re.I)
_PAX_MYX_AND_I_RE = re.compile(r"\b(?:my|our)\s+" + _REL + r"\s+(?:and|&)\s+(?:i|me)\b", re.I)


def _num(tok):
    tok = tok.lower()
    return _NUMW[tok] if tok in _NUMW else int(tok)


def _count_items(blob):
    total = 1                                           # the speaker
    for it in _ITEM_RE.finditer(blob):
        tok = it.group(0).lower()
        if tok.startswith(("my ", "our ")):
            w = tok.split(None, 1)[1]
            if re.fullmatch(_UNKNOWN_GROUP, w):
                return None                             # unknown size -> don't guess
            total += 2 if w == "parents" else 1
        elif tok[0].isdigit():
            total += int(re.match(r"\d+", tok).group())
        else:
            total += 1
    return total


def _valid_pax(n):
    return n if n is not None and 1 <= n <= 60 else None


def extract_passengers_composite(text):
    """Headcounts that need composition: '2 adults and 1 child', 'me and my wife', 'couple'."""
    a, c = _ADULT_RE.search(text), _CHILD_RE.search(text)
    if a and c:
        return _valid_pax(_num(a.group(1)) + _num(c.group(1)))
    m = _PAX_GROUP_ME_RE.search(text)
    if m:
        n = _count_items(m.group(1))
        if n:
            return _valid_pax(n)
    if _PAX_MYX_AND_I_RE.search(text):
        return 2
    m = _PAX_GROUP_WITH_RE.search(text)
    if m:
        n = _count_items(m.group(1))
        if n:
            return _valid_pax(n)
    return None


def _passengers_core(text):
    n = extract_passengers_composite(text)
    if n:
        return n
    for rx in (_PAX_NOUN_RE, _PAX_PARTY_RE):
        m = rx.search(text)
        if m:
            return _valid_pax(_num(m.group(1)))
    m = _PAX_HI_RE.search(text)
    if m:
        return _NUMW_HI[m.group(1).lower()]
    if _PAX_COUPLE_RE.search(text):
        return 2
    m = _PAX_VERB_RE.search(text)
    if m:
        return _valid_pax(_num(m.group(1)))
    if _PAX_SOLO_RE.search(text):
        return 1
    return None


def extract_passengers(text, ctx=None):
    markers = list(_CORRECTION_RE.finditer(text))
    n = None
    if markers:
        tn = _passengers_core(text[markers[-1].end():])
        if tn:
            hn = _passengers_core(text[:markers[-1].start()])
            if ctx is not None and hn and hn != tn:
                ctx.corrected.add("passengers")
            n = tn
    if n is None:
        n = _passengers_core(text)
    if ctx is not None and n and not markers and extract_passengers_composite(text) is None:
        if len({_num(m.group(1)) for m in _PAX_NOUN_RE.finditer(text)}) > 1:
            ctx.amb("passengers", "conflicting_counts")
    return n


# ----------------------------------------------------------------------------
# 3) BUDGET (fare / per-person / conversational)

__all__ = [name for name in globals() if not name.startswith("__")]
