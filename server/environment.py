import random
from .models import Observation, Action, State

class TataNexonEVEnv:
    def __init__(self):
        self.capacity_kwh = 45.0
        self.max_ac_rate = 7.2
        self.state = self.reset()

    def reset(self) -> Observation:
        self.state = State(
            current_soc=0.20,
            soh=1.0,
            total_bill_inr=0.0,
            departure_time=8.5,
            is_grid_active=True,
            current_hour=22.0 # Starts at 10 PM
        )
        return self._get_obs()

    def step(self, action: Action):
        # 1. UPDATE GRID STATUS (The "India Factor")
        # Higher chance of power cuts during evening peak (18:00 - 22:00)
        hour = self.state.current_hour % 24
        cut_probability = 0.05 # 5% base chance
        if 18 <= hour <= 21:
            cut_probability = 0.25 # 25% chance of load shedding in peak hours
            
        self.state.is_grid_active = random.random() > cut_probability

        # 2. APPLY PHYSICS (Only if Grid is Active)
        actual_kw = 0.0
        if self.state.is_grid_active:
            # If AI asks for 50kW but it's a home charger, we cap it at 7.2kW
            actual_kw = max(-15.0, min(action.charge_rate_kw, self.max_ac_rate))
        else:
            # POWER CUT: No energy flows, regardless of the AI's action
            actual_kw = 0.0

        energy_added = actual_kw * 0.25
        self.state.current_soc += energy_added / self.capacity_kwh
        self.state.current_soc = max(0.0, min(1.0, self.state.current_soc))

        # 3. TIME PROGRESSION
        self.state.current_hour += 0.25 # Advance 15 mins
        
        # 4. PRICING
        price = 10.0 if (18 <= hour <= 22) else 6.0
        self.state.total_bill_inr += actual_kw * 0.25 * price

        done = self.state.current_hour >= 32.5 # Ends at 8:30 AM next day
        return self._get_obs(), 0.0, done, {"power_cut_occurred": not self.state.is_grid_active}

    def _get_obs(self) -> Observation:
        h = int(self.state.current_hour % 24)
        m = int((self.state.current_hour % 1) * 60)
        return Observation(
            current_soc=round(self.state.current_soc, 3),
            battery_health_soh=round(self.state.soh, 4),
            electricity_price_inr=10.0 if (18 <= h <= 22) else 6.0,
            is_grid_active=self.state.is_grid_active,
            grid_stability_index=0.95 if self.state.is_grid_active else 0.0,
            time_of_day=f"{h:02d}:{m:02d}",
            user_history=[8.0, 8.5, 7.75, 8.25, 8.0]
        )