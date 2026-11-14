from ._shared import *

# 7) CONVERSATION STATE: field status + clarification requirements
#    field_status[f]  : filled | missing | ambiguous | corrected
#    clarification_reasons codes: missing, multiple_dates, vague_date, same_as_origin, role_unclear,
#      multiple_cities, meridiem_unclear, scope_unclear, unclear_amount, conflicting_counts, multiple_options
# ----------------------------------------------------------------------------
def _clarification_prompt(field, reason, r, ctx):
    n = r.get("passengers")
    if reason == "missing":
        return {"origin": "Which city are you travelling from?",
                "destination": "Where would you like to go?",
                "travel_date": "Which date do you want to travel on?"}.get(field, f"Could you tell me your {field.replace('_', ' ')}?")
    return {
        "multiple_dates": f"I see more than one date ({r.get('travel_date')}). Which one is the travel date?",
        "vague_date": f"Could you give me the exact date? ('{r.get('travel_date')}' is a bit vague.)",
        "same_as_origin": "Your origin and destination look the same. Where are you travelling to?",
        "role_unclear": f"Is {ctx.info.get('lone_city', 'that city')} your starting point or your destination?",
        "multiple_cities": "I noticed more than two cities. Which are the starting point and the final destination?",
        "meridiem_unclear": f"Is that {'arrival' if field == 'arrival_deadline' else 'departure'} time AM or PM?",
        "scope_unclear": f"Is ₹{r.get('budget')} per person or for all {n} passengers?",
        "unclear_amount": f"Just to confirm, is ₹{r.get('budget')} your budget?",
        "conflicting_counts": "I heard different passenger counts. How many people are travelling?",
        "multiple_options": ("Would you like a sleeper, semi-sleeper or seater?" if field == "seat_type"
                             else "Do you prefer AC or non-AC?"),
    }.get(reason, f"Could you clarify your {field.replace('_', ' ')}?")


def build_conversation_state(r, ctx):
    status, reasons = {}, {}
    if r.get("budget") and r.get("passengers") and r["passengers"] > 1 and not r.get("budget_scope"):
        ctx.amb("budget", "scope_unclear")
    for f in STATUS_FIELDS:
        filled = r.get(f) not in (None, "", [])
        if f in ctx.ambiguous:
            status[f], reasons[f] = "ambiguous", ctx.ambiguous[f]
        elif filled and f in ctx.corrected:
            status[f] = "corrected"
        elif filled:
            status[f] = "filled"
        else:
            status[f] = "missing"
            if f in REQUIRED_FIELDS:
                reasons[f] = "missing"
    ask = [f for f in STATUS_FIELDS if f in reasons]
    r["field_status"] = status
    r["clarification_needed"] = bool(ask)
    r["clarification_fields"] = ask or None
    r["clarification_reasons"] = {f: reasons[f] for f in ask} or None
    prompts = []
    for f in ask:
        q = _clarification_prompt(f, reasons[f], r, ctx)
        if q not in prompts:
            prompts.append(q)
    r["clarification_prompts"] = prompts or None
    return r


def group_by_category(result):
    """Re-nest a flat result by category, e.g. result['travel_requirements']['luggage']."""
    out = {}
    for f, v in result.items():
        out.setdefault(FIELD_CATEGORY.get(f, "other"), {})[f] = v
    return out


# ----------------------------------------------------------------------------
# 1) spaCy baseline: PhraseMatcher + NER fallback for cities, deterministic slot rules

__all__ = [name for name in globals() if not name.startswith("__")]
