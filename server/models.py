from pydantic import BaseModel
from typing import List

class Observation(BaseModel):
    current_soc: float
    battery_health_soh: float
    electricity_price_inr: float
    is_grid_active: bool         # NEW: True = Power is on, False = Power cut/Load shedding
    grid_stability_index: float  # 0.0 to 1.0 (Voltage quality)
    time_of_day: str
    user_history: List[float]

class Action(BaseModel):
    charge_rate_kw: float        # -15.0 to 50.0

class State(BaseModel):
    current_soc: float
    soh: float
    total_bill_inr: float
    departure_time: float
    is_grid_active: bool
    current_hour: float          # To track 24-hour cycle