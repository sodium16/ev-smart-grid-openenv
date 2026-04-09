from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional

class UserType(Enum):
    AMAZON_FLEET = "amazon_fleet"      # Strict 6 AM departure, high priority
    PERSONAL_COMMUTER = "personal"    # Messy departure times, price sensitive

class Observation(BaseModel):
    current_soc: float = Field(..., ge=0.0, le=1.0)
    battery_health_soh: float = Field(..., ge=0.0, le=1.0)
    electricity_price_inr: float
    is_grid_active: bool
    time_of_day: str
    user_type: str # Change from Enum to str to match YAML "string"
    target_soc: float
    user_history: List[float] # List[float] translates perfectly to array of numbers         # Last 5 departure times

class Action(BaseModel):
    charge_rate_kw: float = Field(..., ge=-15.0, le=50.0)             # -15.0 to 50.0

# State doesn't need to match YAML, but it should be consistent
class State(BaseModel):
    current_soc: float
    current_hour: float
    battery_health_soh: float
    electricity_price_inr: float
    is_grid_active: bool
    time_of_day: str
    user_type: str
    target_soc: float
    user_history: List[float]
    total_bill_inr: float
    departure_time: float
    grid_violation_count: int = 0