from ._shared import _Ctx
from .bus import _tail_first, _ac_options, _seat_options
from .cities import *
from .bus import *
from .passengers import *
from .budget import *
from .requirements import *
from .cities import _CORRECTION_RE
from .times import *
from .dates import *
from .conversation import *

# ----------------------------------------------------------------------------
def empty_result():
    r = {f: None for f in ALL_FIELDS + OUTPUT_ONLY_FIELDS}
    r["is_correction"] = False
    return r


def finalize(result):
    """Keep seat_type / ac_preference / legacy bus_preference mutually consistent."""
    result["bus_preference"] = result.get("bus_preference") or legacy_bus_pref(
        result.get("seat_type"), result.get("ac_preference"))
    if result.get("bus_preference") in ("sleeper", "seater", "semi-sleeper") and not result.get("seat_type"):
        result["seat_type"] = result["bus_preference"]
    if result.get("bus_preference") in ("ac", "non-ac") and not result.get("ac_preference"):
        result["ac_preference"] = result["bus_preference"]
    if BUDGET_AS_TOTAL and result.get("budget") and result.get("budget_scope") == "per_person" and result.get("passengers"):
        result["budget"] *= result["passengers"]
        result["budget_scope"] = "total"
    return result


def _rule_extract(text, mentions):
    ctx = _Ctx()
    r = empty_result()
    r["origin"], r["destination"] = extract_cities(text, mentions, ctx)
    r["travel_date"], r["arrival_date"] = extract_dates(text, ctx)
    r["departure_preference"], r["arrival_deadline"] = extract_times(text, ctx)
    r["passengers"] = extract_passengers(text, ctx)
    r["budget"], r["budget_scope"] = extract_budget_info(text, ctx)
    r["seat_type"] = _tail_first(extract_seat_type, text, ctx, "seat_type")
    r["ac_preference"] = _tail_first(extract_ac_preference, text, ctx, "ac_preference")
    if not _CORRECTION_RE.search(text):
        if len(_seat_options(text)) > 1:
            ctx.amb("seat_type", "multiple_options")
        if len(_ac_options(text)) > 1:
            ctx.amb("ac_preference", "multiple_options")
    r["luggage"] = extract_luggage(text)
    r["accessibility"] = extract_accessibility(text)
    r["comfort_preferences"] = extract_comfort_preferences(text)
    r["is_correction"] = bool(_CORRECTION_RE.search(text))
    finalize(r)
    return build_conversation_state(r, ctx)


# ----------------------------------------------------------------------------

__all__ = [name for name in globals() if not name.startswith("__")]
