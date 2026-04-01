import random
from .models import Observation, Action, State, UserType
from .utils import generate_user_history

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

        dynamic_history = generate_user_history(prof["avg_dep"], prof["var"])
        
        self.state = State(
            current_soc=random.uniform(*prof["start_soc"]),
            soh=1.0,
            total_bill_inr=0.0,
            departure_time=actual_dep,
            user_type=u_type,
            target_soc=prof["target"],
            current_hour=22.0, # Starts at 10 PM
            is_grid_active=True,
            user_history = dynamic_history
        )
        return self._get_obs()

    def step(self, action: Action):
        # 1. Grid Logic (Stability & Load Shedding)
        # 15-minute steps (0.25h)
        hour = self.state.current_hour % 24
        is_peak = (18 <= hour <= 22)
        
        # High probability of load shedding during peak hours (6 PM - 10 PM)
        prob = 0.25 if is_peak else 0.05
        self.state.is_grid_active = random.random() > prob

        # Grid Stability Index: Simulates voltage fluctuations common in residential grids
        # Stability drops slightly during peak hours due to local network stress
        stability = random.uniform(0.75, 0.95) if is_peak else random.uniform(0.95, 1.0)

        # 2. Physics & Power Delivery
        actual_kw = 0.0
        if self.state.is_grid_active:
            # Clip action to car's hardware limits (e.g., -15.0 to 50.0 kW)
            requested_kw = max(-15.0, min(action.charge_rate_kw, self.max_dc_rate))
            # Prevent charging if battery is full (unless discharging)
            if requested_kw > 0 and self.state.current_soc >= 1.0:
                actual_kw = 0.0
            # Prevent discharging if battery is empty
            elif requested_kw < 0 and self.state.current_soc <= 0.0:
                actual_kw = 0.0
            else:
                # Power delivered is limited by the grid's immediate stability/voltage quality
                actual_kw = requested_kw * stability
        
        # Update State of Charge (SoC)
        self.state.current_soc += (actual_kw * 0.25) / self.capacity_kwh
        self.state.current_soc = max(0.0, min(1.0, self.state.current_soc))
        
        # 3. Refined Health Loss (SOH)
        # Degradation is higher for DC Fast Charging (>22kW) than standard AC charging
        c_rate = abs(actual_kw) / self.capacity_kwh
        if abs(actual_kw) > 22.0:
            # Accelerated wear-and-tear for fast charging/discharging
            self.state.soh -= 0.00005 * (c_rate ** 2)
        else:
            # Standard linear-square degradation for healthy charging rates
            self.state.soh -= 0.00001 * (c_rate ** 2)
        
        # 4. Pricing & Time Progression
        # Indian electricity slabs: ₹10.0 (Peak) vs ₹6.5 (Off-Peak)
        price = 10.0 if is_peak else 6.5
        self.state.total_bill_inr += actual_kw * 0.25 * price

        # Per-step reward for OpenEnv compliance
        soc_progress = (actual_kw * 0.25) / self.capacity_kwh
        reward = soc_progress * 10.0

        cost_penalty = (actual_kw * 0.25 * price) / 100.0
        reward -= cost_penalty

        health_penalty = (1.0 - stability) * 0.5 + (0.00005 if actual_kw > 22.0 else 0.0)
        reward -= health_penalty
        
        self.state.current_hour += 0.25
        
        # 5. Episode Termination
        # Departure time is treated as 'next day' (24h + dep_time)
        target_time = self.state.departure_time + 24.0
        done = self.state.current_hour >= target_time
        
        return self._get_obs(), round(reward, 4), done, {
            "type": self.state.user_type.value,
            "grid_stability": round(stability, 2),
            "is_power_cut": not self.state.is_grid_active,
            "bill": round(self.state.total_bill_inr, 2)
        }

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