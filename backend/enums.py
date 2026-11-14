from enum import Enum

class SeatType(str, Enum):
    SLEEPER = "sleeper"
    SEATER = "seater"

class FieldStatusEnum(str, Enum):
    NOT_ASKED = "not_asked"
    PROVIDED = "provided"
    ASKED_UNKNOWN = "asked_unknown"
    DECLINED = "declined"
    NEEDS_CLARIFICATION = "needs_clarification"
    DEFAULTED = "defaulted"

class ACType(str, Enum):
    AC = "ac"
    NON_AC = "non-ac"

class TimePreferences(str, Enum):
    MORNING = "morning"       # e.g., 06:00 - 12:00
    AFTERNOON = "afternoon"   # e.g., 12:00 - 18:00
    EVENING = "evening"       # e.g., 18:00 - 22:00
    NIGHT = "night"           # e.g., 22:00 - 06:00
