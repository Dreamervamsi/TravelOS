from ._shared import *
from .cities import *
from .passengers import *
from .passengers import _num
from .times import *
from .cities import _CORRECTION_RE
from .times import _clause_before, _nearest_cue


# ----------------------------------------------------------------------------
_NUMW = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
         "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
         "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20}

_MONTH_ALT = "|".join(sorted(MONTHS, key=len, reverse=True))
_DATE_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DATE_NUM_FULL = re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4}|\d{2})\b")
_DATE_NUM_SHORT = re.compile(r"(?<![\d/])(\d{1,2})/(\d{1,2})(?![\d/])")
_DATE_DM = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s*(?:of\s+)?(" + _MONTH_ALT + r")\b")
_DATE_MD = re.compile(r"\b(" + _MONTH_ALT + r")\s+(\d{1,2})(?:st|nd|rd|th)?\b")
_DATE_ORD = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)\b")
WEEKDAYS = {"monday": 0, "mon": 0, "tuesday": 1, "tues": 1, "tue": 1, "wednesday": 2, "wed": 2,
            "thursday": 3, "thurs": 3, "thu": 3, "friday": 4, "fri": 4,
            "saturday": 5, "sat": 5, "sunday": 6, "sun": 6}
_WEEKDAY_RE = re.compile(r"\b(?:(next|this|coming|upcoming)\s+)?(" + "|".join(sorted(WEEKDAYS, key=len, reverse=True)) + r")\b")
_TMRW_ALT = "tomorrow|tomorow|tommorow|tmrw|tmr|tmw|2morrow|2mrw"
_DAY_AFTER_RE = re.compile(r"\b(?:day\s+after\s+(?:" + _TMRW_ALT + r")|parso|overmorrow)\b")
_TMRW_RE = re.compile(r"\b(?:" + _TMRW_ALT + r"|kal)\b")
_TODAY_RE = re.compile(r"\b(?:today|tonight|tonite|2day|aaj|right\s+now|this\s+(?:morning|afternoon|evening|night))\b")
_IN_DAYS_RE = re.compile(r"\b(?:in|after)\s+(\d{1,2}|" + "|".join(_NUMW) + r")\s+days?\b|\b(\d{1,2})\s+days?\s+(?:later|from\s+now)\b")
_NEG_DATE_BEFORE = re.compile(r"\b(?:not|no|never|except|instead\s+of|rather\s+than|n't)\s*$")


def _safe_date(y, m, d):
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _resolve_day(day, month=None):
    base = BASE_DATE.date()
    if month:
        d = _safe_date(base.year, month, day)
        return d if d and d >= base else _safe_date(base.year + 1, month, day)
    y, m = base.year, base.month
    if day < base.day:
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return _safe_date(y, m, day)


def _resolve_weekday(target, qualifier):
    base = BASE_DATE.date()
    qualifier = (qualifier or "").lower()
    if qualifier == "next":      # "next Monday" = that day in next calendar week
        return base + timedelta(days=7 - base.weekday()) + timedelta(days=target)
    diff = (target - base.weekday()) % 7
    if diff == 0 and qualifier != "this":
        diff = 7
    return base + timedelta(days=diff)


def _find_date_hits(t):
    base = BASE_DATE.date()
    hits, spans = [], []

    def free(m):
        return not any(m.start() < e and m.end() > s for s, e in spans)

    def add(m, d):
        if d is not None and free(m):
            hits.append((m.start(), m.end(), d))
            spans.append((m.start(), m.end()))

    for m in _DATE_ISO.finditer(t):
        add(m, _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
    for m in _DATE_NUM_FULL.finditer(t):
        y = int(m.group(3))
        add(m, _safe_date(y + 2000 if y < 100 else y, int(m.group(2)), int(m.group(1))))
    for m in _DATE_NUM_SHORT.finditer(t):
        d, mo = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12 and 1 <= d <= 31:
            add(m, _resolve_day(d, mo))
    for m in _DATE_DM.finditer(t):
        add(m, _resolve_day(int(m.group(1)), MONTHS[m.group(2)]))
    for m in _DATE_MD.finditer(t):
        add(m, _resolve_day(int(m.group(2)), MONTHS[m.group(1)]))
    for m in _DATE_ORD.finditer(t):
        add(m, _resolve_day(int(m.group(1))))
    for m in _DAY_AFTER_RE.finditer(t):
        add(m, base + timedelta(days=2))
    for m in _TMRW_RE.finditer(t):
        add(m, base + timedelta(days=1))
    for m in _TODAY_RE.finditer(t):
        add(m, base)
    for m in _IN_DAYS_RE.finditer(t):
        n = m.group(1) or m.group(2)
        add(m, base + timedelta(days=_num(n)))
    for m in _WEEKDAY_RE.finditer(t):
        add(m, _resolve_weekday(WEEKDAYS[m.group(2)], m.group(1)))
    for m in re.finditer(r"\bweekend\b", t):
        add(m, base + timedelta(days=(5 - base.weekday()) % 7))
    return sorted(hits)


def _date_is_arrival(t, start):
    window = _clause_before(t, start, 50)
    cue = _nearest_cue(window)
    if cue == "arr":
        return True
    if cue == "dep":
        return False
    return bool(re.search(r"\b(?:by|before|till|until)\s+(?:the\s+)?$", window))


def extract_dates(text, ctx=None):
    """-> (travel_date, arrival_date). Arrival-cued dates ('reach by Saturday') go to arrival_date;
    if they are the only date mentioned they also serve as travel_date."""
    t = text.lower()
    base = BASE_DATE.date()
    hits = [h for h in _find_date_hits(t) if not _NEG_DATE_BEFORE.search(t[max(0, h[0] - 14):h[0]].rstrip())]
    markers = list(_CORRECTION_RE.finditer(t))
    if markers and hits:
        cut = markers[-1]
        tail = [h for h in hits if h[0] >= cut.end()]
        head = [h for h in hits if h[0] < cut.start()]
        if tail:
            if ctx is not None and head and {h[2] for h in head} != {h[2] for h in tail}:
                ctx.corrected.add("travel_date")
            hits = tail
    if not hits:
        if re.search(r"\bnext\s+week\b", t):
            if ctx is not None:
                ctx.amb("travel_date", "vague_date")
            return ("sometime next week" if "sometime" in t else "next week"), None
        return None, None
    trav, arr = [], []
    for s_, _, d in hits:
        (arr if _date_is_arrival(t, s_) else trav).append(d.isoformat())

    def uniq(xs):
        out = []
        for x in xs:
            if x not in out:
                out.append(x)
        return out
    trav, arr = uniq(trav), uniq(arr)
    if ctx is not None:
        if len(trav) > 1:
            ctx.amb("travel_date", "multiple_dates")
        elif re.search(r"\bweekend\b", t) and trav == [(base + timedelta(days=(5 - base.weekday()) % 7)).isoformat()]:
            ctx.amb("travel_date", "vague_date")        # Saturday or Sunday?
    travel = " or ".join(trav) if trav else (" or ".join(arr) if arr else None)
    return travel, (" or ".join(arr) if arr else None)


def extract_date(text):
    return extract_dates(text)[0]


# ----------------------------------------------------------------------------
# Shared result helpers

__all__ = [name for name in globals() if not name.startswith("__")]
