from pydantic import BaseModel
from typing import List, Optional

# What the AI sees
class Observation(BaseModel):
    current_soc: float           # 0.0 to 1.0
    current_time: str            # "HH:MM"
    electricity_price: float     # Price per kWh
    grid_limit_kw: float         # Max power available
    user_history: List[str]      # Last 5 departure times

# What the AI can do
class Action(BaseModel):
    charge_rate_kw: float        # e.g., 0.0 to 11.0 kW
    discharge_to_grid: bool      # V2G toggle

# The result of a step
class StepResponse(BaseModel):
    observation: Observation
    reward: float
    done: bool
    info: dict