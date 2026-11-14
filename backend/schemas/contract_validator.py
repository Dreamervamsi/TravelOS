from datetime import time, date
from pydantic import BaseModel, Field, ConfigDict
from enums import TimePreferences, SeatType, ACType, FieldStatusEnum
from typing import Optional, List

class BusPreferences(BaseModel):
    seat_type: Optional[SeatType] = None
    ac_type: Optional[ACType] = None

class TravelRequirements(BaseModel):
    luggage_count: Optional[int] = None
    luggage_notes: Optional[str] = None
    accessibility_requirements: List[str] = Field(default_factory=list)
    comfort_preferences: List[str] = Field(default_factory=list)

class FieldStatus(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    origin: FieldStatusEnum = Field(default=FieldStatusEnum.NOT_ASKED)
    destination: FieldStatusEnum = Field(default=FieldStatusEnum.NOT_ASKED)
    travel_date: FieldStatusEnum = Field(default=FieldStatusEnum.NOT_ASKED)
    passengers: FieldStatusEnum = Field(default=FieldStatusEnum.NOT_ASKED)
    
class TravelBlueprint(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
     
    origin: str = Field(...,description="Starting city or town",examples=["Guntur"])
    destination: str = Field(..., description="Destination city or town",examples=["Hyderabad"])
    travel_date: Optional[date] = Field(..., description="Travel date in YYYY-MM-DD format", examples=["2026-11-22"])
    passengers: int = Field(..., description="No.of passengers travelling", examples=[2,3])
    
    departure_time_preference: Optional[time | TimePreferences] = Field(None, description="Prefered time for departure", examples=["night","morning"])
    arrival_deadline: Optional[time] = Field(None, description="Exact time to reach the destination", examples=["19:00","4:30"])
    bus_preferences: BusPreferences = Field(default_factory=BusPreferences)
    budget: Optional[int] = Field(None, description="Desired price range to have for ticket")
    requirements: TravelRequirements = Field(default_factory=TravelRequirements)

    field_status: Optional[dict] = Field(default_factory=FieldStatus)
    clarification_needed: List[str] = Field(default_factory=list)


