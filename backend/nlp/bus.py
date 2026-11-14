from ._shared import *
from .cities import *
import re

_CORRECTION_RE = re.compile(
    r"\b(i\s+mean|i\s+meant|actually|sorry|wait|instead|rather|correction|change\s+that|no\s+wait|make\s+that)\b", re.I)

_SEAT_PATTERNS = [
    ("semi-sleeper", r"\bsemi[\s\-]*sleep(?:er|ers|ing)\b"),
    ("sleeper", r"\bsleep(?:er|ers)\b|\bsleeping\s+(?:bus|coach|berth|class)\b|\bberths?\b|\bslpr\b"),
    ("seater", r"\bseaters?\b|\bsitting\b|\bpush[\s\-]?back\b|\breclin(?:er|ers|ing)\b|\bchair[\s\-]?car\b|\bseating\s+(?:bus|coach)\b"),
]
_NEG_BEFORE = re.compile(
    r"(?:\b(?:no|not|without|avoid|except|excluding|never|nor|neither)|don'?t\s+(?:want|need|like|prefer)|"
    r"do\s+not\s+(?:want|need|like)|anything\s+but|other\s+than|rather\s+than|instead\s+of)\s+(?:an?\s+|any\s+|the\s+)?$")
_NONAC_RE = re.compile(r"\bnon[\s\-]*a\.?\s*/?\s*c\b|\bnon[\s\-]*air[\s\-]*condition(?:ed|ing)?|\bnonac\b")
_AC_RE = re.compile(r"\ba\s*/\s*c\b|\bac\b|\ba\.c\b|\bair[\s\-]*condition(?:ed|ing)?\b")


def _negated(t, start):
    return bool(_NEG_BEFORE.search(t[max(0, start - 30):start]))


def extract_seat_type(text):
    t = text.lower()
    for label, pat in _SEAT_PATTERNS:
        for m in re.finditer(pat, t):
            if label == "sleeper" and re.search(r"semi[\s\-]*$", t[:m.start()]):
                continue
            if not _negated(t, m.start()):
                return label
    return None


def extract_ac_preference(text):
    t = text.lower()
    if any(not _negated(t, m.start()) for m in _NONAC_RE.finditer(t)):
        return "non-ac"
    nonac_spans = [m.span() for m in _NONAC_RE.finditer(t)]
    for m in _AC_RE.finditer(t):
        if any(s <= m.start() < e for s, e in nonac_spans):
            continue
        return "non-ac" if _negated(t, m.start()) else "ac"
    return None


def _seat_options(text):
    t = text.lower()
    out = []
    for label, pat in _SEAT_PATTERNS:
        for m in re.finditer(pat, t):
            if label == "sleeper" and re.search(r"semi[\s\-]*$", t[:m.start()]):
                continue
            if not _negated(t, m.start()) and label not in out:
                out.append(label)
    return out


def _ac_options(text):
    t = text.lower()
    out = set()
    nonac = list(_NONAC_RE.finditer(t))
    if any(not _negated(t, m.start()) for m in nonac):
        out.add("non-ac")
    spans = [m.span() for m in nonac]
    for m in _AC_RE.finditer(t):
        if any(a <= m.start() < b for a, b in spans):
            continue
        out.add("non-ac" if _negated(t, m.start()) else "ac")
    return out


def _tail_first(extractor, text, ctx, field):
    """If the user self-corrects, trust what comes after the last marker."""
    markers = list(_CORRECTION_RE.finditer(text))
    if markers:
        tv = extractor(text[markers[-1].end():])
        if tv is not None:
            hv = extractor(text[:markers[-1].start()])
            if ctx is not None and hv is not None and hv != tv:
                ctx.corrected.add(field)
            return tv
    return extractor(text)


def legacy_bus_pref(seat_type, ac_pref):
    """Old single-label contract: seat type wins over AC ('AC sleeper' -> 'sleeper')."""
    return seat_type or ac_pref


def extract_bus_pref(text):
    return legacy_bus_pref(extract_seat_type(text), extract_ac_preference(text))


def normalize_seat_type(v):
    if v is None or v == "":
        return None
    return extract_seat_type(str(v)) or str(v).strip().lower().replace("_", "-").replace(" ", "-")


def normalize_ac(v):
    if v is None or v == "":
        return None
    s = str(v).strip().lower()
    if s in ("true", "yes"):
        return "ac"
    if s in ("false", "no"):
        return "non-ac"
    return extract_ac_preference(s) or s


def normalize_bus_pref(v):
    if v is None or v == "":
        return None
    return extract_bus_pref(str(v)) or str(v).strip().lower()


# ----------------------------------------------------------------------------
# 2) PASSENGERS (context-aware)

__all__ = [name for name in globals() if not name.startswith("__")]
