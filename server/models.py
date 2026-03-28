from pydantic import BaseModel
from typing import List, Dict, Any

class Observation(BaseModel):
    current_soc: float           # State of Charge (0.0 to 1.0)
    battery_health: float        # State of Health (0.0 to 1.0)
    electricity_price: float     # Current price per kWh
    grid_load_kw: float          # Total demand on the local grid
    time_of_day: str             # "HH:MM"
    user_history: List[float]    # Last 5 departure times (decimal hours)

class Action(BaseModel):
    charge_rate_kw: float        # Target charging speed (e.g., -10.0 to 22.0)
    # Note: Negative values = V2G (discharging back to grid)

class State(BaseModel):
    """Internal state that the AI doesn't see directly but the grader uses."""
    current_soc: float
    battery_health: float
    total_cost_saved: float
    departure_time: float        # The 'secret' time the user actually leaves
    is_plugged_in: bool
    step_count: int