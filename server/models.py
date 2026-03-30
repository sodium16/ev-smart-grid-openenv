from enum import Enum
from pydantic import BaseModel
from typing import List, Optional

class UserType(Enum):
    AMAZON_FLEET = "amazon_fleet"      # Strict 6 AM departure, high priority
    PERSONAL_COMMUTER = "personal"    # Messy departure times, price sensitive

class Observation(BaseModel):
    current_soc: float
    battery_health_soh: float
    electricity_price_inr: float
    is_grid_active: bool
    time_of_day: str
    user_type: UserType
    target_soc: float
    user_history: List[float]         # Last 5 departure times

class Action(BaseModel):
    charge_rate_kw: float             # -15.0 to 50.0

class State(BaseModel):
    current_soc: float
    soh: float
    total_bill_inr: float
    departure_time: float             # Secret ground truth
    user_type: UserType
    target_soc: float
    current_hour: float
    is_grid_active: bool
    user_history: List[float]