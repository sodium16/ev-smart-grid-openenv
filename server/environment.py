import random
from .models import Observation, Action, State, UserType

class TataNexonEVEnv:
    def __init__(self):
        self.capacity_kwh = 45.0  # Nexon 45LR
        self.max_ac_rate = 7.2    # Standard Indian Home Charger
        self.max_dc_rate = 50.0   # Public Fast Charger
        
        # Archetype definitions
        self.profiles = {
            UserType.AMAZON_FLEET: {
                "avg_dep": 6.0, "var": 0.1, "target": 0.95, "start_soc": (0.1, 0.25)
            },
            UserType.PERSONAL_COMMUTER: {
                "avg_dep": 8.5, "var": 1.5, "target": 0.80, "start_soc": (0.2, 0.5)
            }
        }
        self.state = None

    def reset(self) -> Observation:
        u_type = random.choice(list(UserType))
        prof = self.profiles[u_type]
        
        # Randomize departure using Gaussian distribution for "messiness"
        actual_dep = random.gauss(prof["avg_dep"], prof["var"])
        
        self.state = State(
            current_soc=random.uniform(*prof["start_soc"]),
            soh=1.0,
            total_bill_inr=0.0,
            departure_time=actual_dep,
            user_type=u_type,
            target_soc=prof["target"],
            current_hour=22.0, # Starts at 10 PM
            is_grid_active=True
        )
        return self._get_obs()

    def step(self, action: Action):
        # 1. Grid Logic (Load Shedding)
        hour = self.state.current_hour % 24
        prob = 0.25 if (18 <= hour <= 22) else 0.05
        self.state.is_grid_active = random.random() > prob

        # 2. Physics
        actual_kw = 0.0
        if self.state.is_grid_active:
            # Clip action to car's hardware limits
            actual_kw = max(-15.0, min(action.charge_rate_kw, self.max_dc_rate))
        
        # 15 min steps (0.25h)
        self.state.current_soc += (actual_kw * 0.25) / self.capacity_kwh
        self.state.current_soc = max(0.0, min(1.0, self.state.current_soc))
        
        # Health loss formula: Degradation increases with power square
        self.state.soh -= 0.00001 * ((abs(actual_kw)/self.capacity_kwh)**2)
        
        self.state.current_hour += 0.25
        
        # Pricing: Peak vs Off-Peak
        price = 10.0 if (18 <= hour <= 22) else 6.5
        self.state.total_bill_inr += actual_kw * 0.25 * price
        target_time = self.state.departure_time + 24.0
        # Done if user leaves
        done = self.state.current_hour >= target_time

        if self.state.current_soc >= self.state.target_soc:
            pass
        
        return self._get_obs(), 0.0, done, {"type": self.state.user_type.value}

    def _get_obs(self) -> Observation:
        h = int(self.state.current_hour % 24)
        m = int((self.state.current_hour % 1) * 60)
        return Observation(
            current_soc=round(self.state.current_soc, 4),
            battery_health_soh=round(self.state.soh, 4),
            electricity_price_inr=10.0 if (18 <= int(h) <= 22) else 6.5,
            is_grid_active=self.state.is_grid_active,
            time_of_day=f"{h:02d}:{m:02d}",
            user_type=self.state.user_type,
            target_soc=self.state.target_soc,
            user_history=[6.0, 6.1, 5.9, 6.0, 6.0] if self.state.user_type == UserType.AMAZON_FLEET else [8.0, 9.5, 7.5, 8.2, 9.0]
        )