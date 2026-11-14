from ._shared import *
from .cities import *
import re
from .passengers import *

# ----------------------------------------------------------------------------
_CORRECTION_RE = re.compile(
    r"\b(i\s+mean|i\s+meant|actually|sorry|wait|instead|rather|correction|change\s+that|no\s+wait|make\s+that)\b", re.I)

_NUMW = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
         "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
         "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20}

_MONTH_ALT = "|".join(sorted(MONTHS, key=len, reverse=True))

_WORDVAL = {"a": 1, **_NUMW, "thirty": 30, "forty": 40, "fifty": 50}
_MULTVAL = {"k": 1000, "thousand": 1000, "hazaar": 1000, "hazar": 1000, "lakh": 100000, "lakhs": 100000,
            "lac": 100000, "lacs": 100000, "hundred": 100}
_MONEY_RE = re.compile(
    r"(?<![\w.,])(?:(?P<pre>rs\.?|inr|₹|rupees?)\s*)?"
    r"(?P<num>\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?)"
    r"(?:\s?(?P<mult>k|thousand|hazaar|hazar|lakhs?|lacs?|hundred)\b)?"
    r"(?:\s*(?P<post>rs\b\.?|rupees?\b|inr\b|₹|/-|bucks\b))?", re.I)
_WORD_MONEY_RE = re.compile(
    r"\b(?P<w>(?:a|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty|fifty)"
    r"(?:\s+and\s+a\s+half)?)\s+(?P<m>hundred|thousand|lakh)\b", re.I)
_NOT_MONEY_AFTER = re.compile(
    r"^\s*(?::|am\b|pm\b|a\.m|p\.m|km\b|kms\b|kilomet|hrs?\b|hours?\b|mins?\b|minutes?\b|people\b|persons?\b|"
    r"passengers?\b|pax\b|seats?\b|tickets?\b|days?\b|nights?\b|weeks?\b|months?\b|st\b|nd\b|rd\b|th\b|%|"
    r"o'?clock|stops?\b|(?:" + _MONTH_ALT + r")\b)", re.I)
_NOT_MONEY_BEFORE = re.compile(r"(?:seat|bus|coach|route|platform|gate|row|no|number|nr|#|pnr|flight|train)\s*\.?\s*$", re.I)
_STRONG_CUE = re.compile(
    r"\b(?:budget|fares?|prices?|priced|costs?|pay(?:ing)?|spend(?:ing)?|afford|max|maximum|upto|up\s*to|under|"
    r"below|within|less\s+than|lesser\s+than|not\s+more\s+than|no\s+more\s+than|at\s+most|upper\s+limit|limit|"
    r"caps?|capped|exceed(?:ing)?|charges?|rates?|can\s+go|ceiling|not\s+above|nothing\s+above|cheaper\s+than|"
    r"i\s+have|can\s+stretch|stretch)\b", re.I)
_WEAK_CUE = re.compile(r"\b(?:around|about|approx(?:imately)?|roughly|nearly|almost|somewhere)\b|~", re.I)
_SUFFIX_CUE = re.compile(
    r"^\s*(?:tak\b|ke\s+andar|ke\s+ander|se\s+kam|se\s+neeche|or\s+less|and\s+below|or\s+below|and\s+under|"
    r"or\s+lower|max\b|maximum|at\s+most|tops\b|only\b)", re.I)
_PER_PERSON_RE = re.compile(
    r"\bper\s*(?:head|person|passenger|ticket|seat|pax|adult|individual|traveller|traveler)\b|"
    r"\beach\b(?!\s+way)|/\s*(?:person|head|pax|seat)\b|\ba\s+head\b|\bpp\b|\bapiece\b|"
    r"\bevery\s+(?:person|one)\b|\ba\s+piece\b", re.I)
_TOTAL_RE = re.compile(
    r"\btotal\b|\boverall\b|\bin\s+all\b|\baltogether\b|\ball\s+together\b|\bcombined\b|"
    r"\bfor\s+(?:all|everyone|everybody|the\s+(?:whole|entire)\s+group|the\s+group|both)\b|\bentire\s+trip\b", re.I)


def _money_candidates(text):
    t = text
    cands = []
    for m in _MONEY_RE.finditer(t):
        s, e = m.start(), m.end()
        has_cur = bool(m.group("pre") or m.group("post"))
        # time / date / version fragments
        if s > 0 and t[s - 1] in ":/" or (e < len(t) and t[e:e + 1] in ":/"):
            continue
        if not has_cur and (_NOT_MONEY_AFTER.match(t[e:]) or _NOT_MONEY_BEFORE.search(t[max(0, s - 14):s])):
            continue
        amt = float(m.group("num").replace(",", ""))
        mult = (m.group("mult") or "").lower()
        if mult:
            amt *= _MULTVAL[mult]
        cands.append({"s": s, "e": e, "amt": int(amt), "cur": has_cur, "mult": bool(mult)})
    for m in _WORD_MONEY_RE.finditer(t):
        w = m.group("w").lower()
        half = w.endswith("and a half")
        base = _WORDVAL[w.split()[0]] + (0.5 if half else 0)
        cands.append({"s": m.start(), "e": m.end(), "amt": int(base * _MULTVAL[m.group("m").lower()]),
                      "cur": False, "mult": True})
    cands.sort(key=lambda c: c["s"])
    # drop overlaps (e.g. "twelve hundred" picked up twice)
    out = []
    for c in cands:
        if out and c["s"] < out[-1]["e"]:
            continue
        out.append(c)
    # merge ranges: "800-1200", "800 to 1200", "between 800 and 1200" -> upper bound
    merged = []
    for c in out:
        if merged and re.fullmatch(r"\s*(?:-|–|—|to|and|or|se)\s*", t[merged[-1]["e"]:c["s"]], re.I):
            p = merged[-1]
            p.update(e=c["e"], amt=max(p["amt"], c["amt"]), cur=p["cur"] or c["cur"], mult=p["mult"] or c["mult"])
        else:
            merged.append(dict(c))
    return merged


def _score_candidate(text, c):
    clause = re.split(r"[.;!?\n]", text[max(0, c["s"] - 45):c["s"]])[-1]
    score = 0.0
    if c["cur"]:
        score += 3
    if _STRONG_CUE.search(clause):
        score += 3
    elif _WEAK_CUE.search(clause):
        score += 1
    if _SUFFIX_CUE.match(text[c["e"]:]):
        score += 3
    if c["mult"]:
        score += 1
    bare = not (c["cur"] or c["mult"])
    if bare and score == 0:
        if not (100 <= c["amt"] <= 50000) or 1990 <= c["amt"] <= 2100:
            return None
        score = 0.5
    if score >= 1 and c["amt"] < 100 and not c["cur"] and not c["mult"]:
        return None                                     # "max 4", "under 50" without a currency
    return score


def extract_budget_info(text, ctx=None):
    """Returns (amount_in_INR_as_stated, scope) where scope in {'per_person','total',None}."""
    cands = _money_candidates(text)
    markers = list(_CORRECTION_RE.finditer(text))
    if markers:                                         # "budget 1000, sorry, make it 1500"
        cut = markers[-1]
        tail = [c for c in cands if c["s"] >= cut.end()]
        if tail:
            head = [c for c in cands if c["e"] <= cut.start()]
            if ctx is not None and head and max(c["amt"] for c in head) != max(c["amt"] for c in tail):
                ctx.corrected.add("budget")
            cands = tail
    best, best_score = None, 0
    for c in cands:
        sc = _score_candidate(text, c)
        if sc is not None and sc > best_score:
            best, best_score = c, sc
    if best is None:
        return None, None
    if ctx is not None and best_score < 1:
        ctx.amb("budget", "unclear_amount")             # a bare number with no money cue
    near = text[max(0, best["s"] - 25):best["e"] + 35]
    for region in (near, text):
        per, tot = _PER_PERSON_RE.search(region), _TOTAL_RE.search(region)
        if per and tot:
            return best["amt"], ("per_person" if per.start() >= tot.start() else "total")
        if per:
            return best["amt"], "per_person"
        if tot:
            return best["amt"], "total"
    return best["amt"], None


def extract_budget(text):
    return extract_budget_info(text)[0]


# ----------------------------------------------------------------------------
# 6) TRAVEL REQUIREMENTS: luggage, accessibility, comfort preferences
#    Each is a list of normalised tags (or None when nothing is mentioned).

__all__ = [name for name in globals() if not name.startswith("__")]
