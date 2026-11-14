from datetime import datetime
import json
from datetime import date, timedelta
import re
import difflib
import time

import pandas as pd

from schemas.contract_validator import TravelBlueprint

BASE_DATE = datetime(2026, 11, 12)          # Thursday

CORE_FIELDS = [
    "origin", "destination", "travel_date", "arrival_deadline",
    "budget", "bus_preference", "passengers",
]
ALL_FIELDS = [
    "origin", "destination", "travel_date", "arrival_date",
    "departure_preference", "arrival_deadline", "budget", "budget_scope",
    "seat_type", "ac_preference", "bus_preference", "passengers",
    "luggage", "accessibility", "comfort_preferences",
    "field_status", "clarification_needed", "clarification_fields", "clarification_reasons",
]
OUTPUT_ONLY_FIELDS = ["clarification_prompts"]
FIELD_CATEGORY = {
    "origin": "trip", "destination": "trip", "travel_date": "schedule", "arrival_date": "schedule",
    "departure_preference": "schedule", "arrival_deadline": "schedule", "budget": "pricing",
    "budget_scope": "pricing", "seat_type": "bus_type", "ac_preference": "bus_type",
    "bus_preference": "bus_type", "passengers": "group", "luggage": "travel_requirements",
    "accessibility": "travel_requirements", "comfort_preferences": "travel_requirements",
    "field_status": "conversation_state", "clarification_needed": "conversation_state",
    "clarification_fields": "conversation_state", "clarification_reasons": "conversation_state",
}
LIST_FIELDS = {"luggage", "accessibility", "comfort_preferences", "clarification_fields"}
DICT_FIELDS = {"field_status", "clarification_reasons"}
BOOL_FIELDS = {"clarification_needed"}
STATUS_FIELDS = ["origin", "destination", "travel_date", "departure_preference", "arrival_deadline",
                 "budget", "passengers", "seat_type", "ac_preference", "luggage", "accessibility",
                 "comfort_preferences"]
REQUIRED_FIELDS = ["origin", "destination", "travel_date"]
FIELDS = CORE_FIELDS
GT_ALIASES = {"departure_time": "departure_preference", "deadline": "arrival_deadline",
              "comfort": "comfort_preferences", "comfort_preference": "comfort_preferences",
              "luggage_requirements": "luggage", "accessibility_needs": "accessibility",
              "needs_clarification": "clarification_needed", "clarification_required": "clarification_needed",
              "clarification_requirements": "clarification_fields", "fields_status": "field_status"}
NESTED_GT_KEYS = ("travel_requirements", "conversation_state")
BUDGET_AS_TOTAL = False
INFER_DEADLINE_FROM_DAYPART = True
DAYPART_DEADLINE = {("", "morning"): "09:00", ("early", "morning"): "07:00",
                    ("", "afternoon"): "15:00", ("", "evening"): "19:00",
                    ("", "night"): "23:00", ("late", "night"): "23:59"}
EXTRA_CITIES_PATH = None
_SPACY = None

class _Ctx:
    """Collects conversation-state evidence while the slot extractors run."""

    def __init__(self):
        self.ambiguous = {}
        self.corrected = set()
        self.info = {}

    def amb(self, field, reason):
        self.ambiguous.setdefault(field, reason)

__all__ = [name for name in globals() if not name.startswith("__")]
