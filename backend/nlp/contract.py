from ._shared import *

def _blueprint_time(value):
    """Convert the extractor's time strings to values accepted by TravelBlueprint."""
    if value is None or isinstance(value, time):
        return value
    if re.fullmatch(r"\d{2}:\d{2}", str(value)):
        return time.fromisoformat(str(value))
    return value


def _blueprint_date(value):
    if value is None or isinstance(value, date):
        return value
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(value)):
        return date.fromisoformat(str(value))
    return value

def _blueprint_luggage(tags):
    if not tags:
        return None, None
    count = None
    notes = []
    for tag in tags:
        match = re.fullmatch(r"(\d+)_bags?", tag)
        if match:
            count = int(match.group(1))
        elif tag != "none":
            notes.append(tag)
    if "none" in tags:
        return 0, None
    return count, ", ".join(notes) or None


def to_travel_blueprint(result):
    """Adapt the flat extractor result to the validated TravelBlueprint contract."""
    luggage_count, luggage_notes = _blueprint_luggage(result.get("luggage"))
    field_status = {
        field: {
            "filled": "provided",
            "corrected": "provided",
            "ambiguous": "needs_clarification",
            "missing": "not_asked",
        }.get(status, status)
        for field, status in (result.get("field_status") or {}).items()
        if field in {"origin", "destination", "travel_date", "passengers"}
    }
    print(result.get("travel_date"))
    return TravelBlueprint.model_validate({
        "origin": result.get("origin"),
        "destination": result.get("destination"),
        "travel_date": _blueprint_date(result.get("travel_date")),
        "passengers": result.get("passengers"),
        "departure_time_preference": _blueprint_time(result.get("departure_preference")),
        "arrival_deadline": _blueprint_time(result.get("arrival_deadline")),
        "bus_preferences": {
            "seat_type": result.get("seat_type"),
            "ac_type": result.get("ac_preference"),
        },
        "budget": result.get("budget"),
        "requirements": {
            "luggage_count": luggage_count,
            "luggage_notes": luggage_notes,
            "accessibility_requirements": result.get("accessibility") or [],
            "comfort_preferences": result.get("comfort_preferences") or [],
        },
        "field_status": field_status,
        "clarification_needed": result.get("clarification_fields") or [],
    })



__all__ = [name for name in globals() if not name.startswith("__")]
