from ._shared import *
from .cities import *
from .passengers import *
from .budget import _MONTH_ALT
# ----------------------------------------------------------------------------
_DEP_CUE = re.compile(
    r"\b(?:leav(?:e|es|ing)|left|depart\w*|start(?:s|ing)?|board(?:ing)?|pick[\s\-]?up|pickup|"
    r"set(?:ting)?\s+off|dep|nikal\w*|bus\s+(?:at|timing|leaving))\b", re.I)
_ARR_CUE = re.compile(
    r"\b(?:reach\w*|arriv\w*|get(?:ting)?\s+(?:there|to|in|down)|be\s+(?:there|in|at|back|home|present)|"
    r"land\w*|deadline|latest|no\s+later|must\s+be|need\s+to\s+be|interview|meeting|exam|appointment|flight|"
    r"train|class|office|wedding|event|function|conference|shift|duty|join\w*|check[\s\-]?in|presentation|"
    r"seminar|lecture|doctor|hospital|report(?:ing)?\s+(?:at|by)|pahunch\w*)\b", re.I)
_END_PREPS = {"by", "before", "till", "until", "latest", "latest by", "no later than", "not later than", "on or before"}

_TIME_CORE = (
    r"(?:(?P<named>noon|midnight)\b"
    r"|half\s+past\s+(?P<hp>\d{1,2})\b|quarter\s+past\s+(?P<qp>\d{1,2})\b|quarter\s+to\s+(?P<qt>\d{1,2})\b"
    r"|(?P<h24>[01]?\d|2[0-3])(?P<m24>[0-5]\d)\s*(?:hrs|hours|h)\b"
    r"|(?P<h>\d{1,2})(?:[:.](?P<m>[0-5]\d))?(?!\d)\s*"
    r"(?:(?P<ap>a\.?\s?m\.?|p\.?\s?m\.?)(?![a-z])|(?P<oc>o'?\s?clock))?)"
    r"(?:\s*(?:sharp|ish))?"
    r"(?:\s+(?:in\s+the\s+)?(?P<part>morning|afternoon|evening|night)\b)?")
_TIME_RE = re.compile(
    r"(?<![\w.,:/₹\-])(?:(?P<prep>no\s+later\s+than|not\s+later\s+than|on\s+or\s+before|latest\s+by|latest|"
    r"by|before|after|at|around|till|until|from|between|@)\s*)?" + _TIME_CORE, re.I)
_NOT_TIME_AFTER = re.compile(
    r"^\s*(?:people|persons?|pax|passengers?|seats?|tickets?|rs\b|rupees?\b|inr\b|₹|k\b|km\b|kms\b|hours?\b|"
    r"days?\b|nights?\b|mins?\b|minutes?\b|weeks?\b|months?\b|st\b|nd\b|rd\b|th\b|/|%|(?:" + _MONTH_ALT + r")\b)", re.I)
_BARE_OK_PREPS = {"by", "before", "after", "at", "around", "till", "until", "latest", "latest by",
                  "no later than", "not later than", "on or before", "@"}
_DAYPART_RE = re.compile(
    r"\b(?:(?P<mod>early|late)\s+)?(?P<part>morning|afternoon|evening|night|overnight|tonight|tonite)\b", re.I)
_ARR_DAYPART_CTX = re.compile(
    r"(?:\b(?:by|before|till|until)\s+(?:the\s+)?|"
    r"(?:reach\w*|arriv\w*|land\w*|get\s+there|be\s+there)\b[^.;!?]{0,40}\b(?:in|by|on|during|at)\s+(?:the\s+)?)"
    r"(?:early\s+|late\s+)?$", re.I)


def _norm_prep(p):
    if not p:
        return None
    p = re.sub(r"\s+", " ", p.lower().strip())
    return "at" if p == "@" else p


def _nearest_cue(window):
    best, kind = -1, None
    for m in _DEP_CUE.finditer(window):
        if m.start() > best:
            best, kind = m.start(), "dep"
    for m in _ARR_CUE.finditer(window):
        if m.start() > best:
            best, kind = m.start(), "arr"
    return kind


def _clause_before(text, s, width=70):
    return re.split(r"[.;!?\n]", text[max(0, s - width):s])[-1]


def _classify_time(prep, cue):
    """-> ('arr',) | ('dep', 'exact'|'after'|'before') | None"""
    if cue == "arr":
        return ("arr",) if prep in _END_PREPS or prep in (None, "at", "around") else None
    if cue == "dep":
        if prep in ("after", "from"):
            return ("dep", "after")
        if prep in _END_PREPS:
            return ("dep", "before")
        return ("dep", "exact")
    if prep in _END_PREPS:
        return ("arr",)
    if prep in ("after", "from"):
        return ("dep", "after")
    return ("dep", "exact")


def _resolve_hour(h, ap, part, text_lc, role):
    ap = (ap or "").lower().replace(".", "").replace(" ", "")
    part = (part or "").lower()
    if ap == "pm":
        return h + 12 if h < 12 else h
    if ap == "am":
        return 0 if h == 12 else h
    if part in ("afternoon", "evening"):
        return h + 12 if 1 <= h < 12 else h
    if part == "night":
        return 0 if h == 12 else (h + 12 if 6 <= h <= 11 else h)
    if part == "morning":
        return h
    # no marker at all -> use the rest of the sentence as a hint
    morning = re.search(r"\bmorning\b", text_lc)
    if role == "dep":
        if re.search(r"\b(?:night|evening|afternoon|tonight|tonite)\b", text_lc) and not morning and 1 <= h <= 11:
            return h + 12
    else:
        if re.search(r"\b(?:evening|afternoon)\b", text_lc) and not morning and not re.search(r"\b(?:night|overnight)\b", text_lc) \
                and 1 <= h <= 11:
            return h + 12
    return h


def _hhmm_from_match(m, text_lc, role):
    g = m.groupdict()
    if g["named"]:
        return "12:00" if g["named"].lower() == "noon" else "00:00"
    if g["m24"] and g["h24"] is not None:
        h, mi = int(g["h24"]), int(g["m24"])
        return f"{h:02d}:{mi:02d}" if h <= 23 else None
    if g["hp"]:
        h, mi = int(g["hp"]), 30
    elif g["qp"]:
        h, mi = int(g["qp"]), 15
    elif g["qt"]:
        h, mi = (int(g["qt"]) - 1) or 12, 45
    else:
        h, mi = int(g["h"]), int(g["m"] or 0)
    if not (0 <= h <= 23):
        return None
    h = _resolve_hour(h, g.get("ap"), g.get("part"), text_lc, role)
    return f"{h % 24:02d}:{mi:02d}"


def _store_time(result, kind, hhmm):
    if kind[0] == "arr":
        result["arrival_deadline"] = result["arrival_deadline"] or hhmm
    else:
        val = hhmm if kind[1] == "exact" else f"{kind[1]} {hhmm}"
        result["departure_preference"] = result["departure_preference"] or val


def _apply_dayparts(result, text, consumed):
    for m in _DAYPART_RE.finditer(text):
        if any(s <= m.start() < e for s, e in consumed):
            continue
        before = text[:m.start()]
        if re.search(r"\bgood\s+$", before, re.I):
            continue
        part = m.group("part").lower()
        part = "night" if part in ("overnight", "tonight", "tonite") else part
        mod = (m.group("mod") or "").lower()
        if _ARR_DAYPART_CTX.search(_clause_before(text, m.start(), 90)):
            if INFER_DEADLINE_FROM_DAYPART and not result["arrival_deadline"]:
                result["arrival_deadline"] = DAYPART_DEADLINE.get((mod, part)) or DAYPART_DEADLINE.get(("", part))
        elif not result["departure_preference"]:
            result["departure_preference"] = part


def _meridiem_unclear(g, text_lc):
    """'by 7', 'at 9:30' with no am/pm, no daypart and nothing in the sentence that settles it."""
    if g["ap"] or g["part"] or g["named"] or g["m24"]:
        return False
    hv = g["h"] or g["hp"] or g["qp"] or g["qt"]
    if hv is None or not 1 <= int(hv) <= 12:
        return False
    return not re.search(r"\b(?:morning|afternoon|evening|night|overnight|tonight|tonite)\b", text_lc)


def extract_times(text, ctx=None):
    """-> (departure_preference, arrival_deadline). Departure: 'HH:MM' | 'after HH:MM' | 'before HH:MM' | daypart."""
    res = {"departure_preference": None, "arrival_deadline": None}
    t_lc = text.lower()
    consumed, between_end = [], -1
    for m in _TIME_RE.finditer(text):
        g = m.groupdict()
        prep = _norm_prep(g["prep"])
        s, e = m.start(), m.end()
        if s < between_end:
            continue
        bare = not (g["ap"] or g["oc"] or g["m"] or g["named"] or g["hp"] or g["qp"] or g["qt"]
                    or g["m24"] or g["part"])
        if bare and (prep not in _BARE_OK_PREPS or _NOT_TIME_AFTER.match(text[e:])):
            continue
        if prep == "between":
            m2 = re.match(r"\s*(?:and|to|-|–)\s*[\d:.]+\s*(?:a\.?m\.?|p\.?m\.?)?", text[e:], re.I)
            if m2:
                between_end = e + m2.end()
        cue = _nearest_cue(_clause_before(text, s))
        kind = _classify_time(prep, cue)
        if not kind:
            continue
        hhmm = _hhmm_from_match(m, t_lc, kind[0])
        if not hhmm:
            continue
        consumed.append((s, e))
        fld = "arrival_deadline" if kind[0] == "arr" else "departure_preference"
        first = res[fld] is None
        _store_time(res, kind, hhmm)
        if ctx is not None and first and _meridiem_unclear(g, t_lc):
            ctx.amb(fld, "meridiem_unclear")
    _apply_dayparts(res, text, consumed)
    return res["departure_preference"], res["arrival_deadline"]


def extract_time(text):
    """Back-compat: the arrival deadline only."""
    return extract_times(text)[1]


# ----------------------------------------------------------------------------
# 4b) DATES (rule-based, resolved against BASE_DATE)

__all__ = [name for name in globals() if not name.startswith("__")]
