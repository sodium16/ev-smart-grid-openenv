from typing import Callable, Dict, Any


class Task:
    def __init__(
        self,
        name: str,
        task_id: str,
        description: str,
        max_steps: int,
        grader: Callable[[Dict[str, Any]], float],
    ):
        self.name = name
        self.task_id = task_id          # matches openenv.yaml task ids
        self.description = description
        self.max_steps = max_steps
        self.grader = grader


# =====================================================
# EASY TASK — Night Charging
# =====================================================

def night_charging_grader(state: Dict[str, Any]) -> float:
    """
    Goal:
    - Reach target SOC by departure
    - Prefer off-peak (cheap) charging
    """
    current_soc = state.get("current_soc", 0.0)
    target_soc = state.get("target_soc", 1.0)
    total_bill = state.get("total_bill_inr", 0.0)

    # Primary: SOC completion (0.0 -> 0.7)
    soc_score = min(current_soc / target_soc, 1.0) if target_soc > 0 else 1.0
    score = 0.7 * soc_score

    # Secondary: cost efficiency (0.0 -> 0.3)
    # ₹350 is a reasonable overnight full-charge bill; reward staying under it
    cost_ratio = min(total_bill / 350.0, 1.0)
    score += 0.3 * (1.0 - cost_ratio)

    return round(max(0.0, min(1.0, score)), 3)


night_charging_task = Task(
    name="Night Charging",
    task_id="night_owl",
    description="Charge the EV overnight at low cost and reach the target SOC.",
    max_steps=48,
    grader=night_charging_grader,
)


# =====================================================
# MEDIUM TASK — Grid-Aware Charging
# =====================================================

def grid_constraint_grader(state: Dict[str, Any]) -> float:
    """
    Goal:
    - Reach target SOC
    - Avoid charging during grid inactive periods
    - Keep cost low
    """
    current_soc = state.get("current_soc", 0.0)
    target_soc = state.get("target_soc", 1.0)
    grid_violations = state.get("grid_violation_count", 0)
    total_bill = state.get("total_bill_inr", 0.0)

    # SOC completion (0.0 -> 0.6)
    soc_score = min(current_soc / target_soc, 1.0) if target_soc > 0 else 1.0
    score = 0.6 * soc_score

    # Grid constraint adherence (0.0 -> 0.25)
    # Each violation during grid-off costs 0.05, floored at 0
    violation_penalty = min(grid_violations * 0.05, 0.25)
    score += 0.25 - violation_penalty

    # Cost awareness (0.0 -> 0.15)
    cost_ratio = min(total_bill / 400.0, 1.0)
    score += 0.15 * (1.0 - cost_ratio)

    return round(max(0.0, min(1.0, score)), 3)


grid_constraint_task = Task(
    name="Grid Constraint",
    task_id="grid_survivor",
    description="Charge the EV while respecting grid availability and minimizing stress.",
    max_steps=48,
    grader=grid_constraint_grader,
)


# =====================================================
# HARD TASK — V2G Profit Optimization
# =====================================================

def v2g_profit_grader(state: Dict[str, Any]) -> float:
    """
    Goal:
    - Reach target SOC
    - Minimize electricity bill (buy low, sell high via V2G)
    - Preserve battery health (SOH)

    Formula: additive components so each goal contributes independently.
    Max possible = 0.4 + 0.35 + 0.25 = 1.0
    """
    current_soc = state.get("current_soc", 0.0)
    target_soc = state.get("target_soc", 1.0)
    soh = state.get("battery_health_soh", 1.0)
    net_bill = state.get("total_bill_inr", 0.0)   # negative = profit from V2G

    # Component 1: SOC completion (0.0 -> 0.40)
    soc_score = min(current_soc / target_soc, 1.0) if target_soc > 0 else 1.0
    soc_component = 0.40 * soc_score

    # Component 2: Cost/profit performance (0.0 -> 0.35)
    # ₹500 is a bad bill (agent charged at peak), ₹0 is neutral, negative = earned via V2G
    # Map [-200, 500] -> [1.0, 0.0] linearly; clamp to [0, 1]
    cost_score = 1.0 - ((net_bill + 200.0) / 700.0)
    cost_component = 0.35 * max(0.0, min(1.0, cost_score))

    # Component 3: Battery health preservation (0.0 -> 0.25)
    # SOH starts near 1.0 and degrades; penalize degradation proportionally
    # Assume SOH below 0.95 is concerning; below 0.85 is bad
    health_score = min(soh / 0.95, 1.0)
    health_component = 0.25 * health_score

    score = soc_component + cost_component + health_component
    return round(max(0.0, min(1.0, score)), 3)


v2g_profit_task = Task(
    name="V2G Profit Optimization",
    task_id="v2g_profit",
    description="Optimize charging to minimize cost while preserving battery health.",
    max_steps=72,
    grader=v2g_profit_grader,
)


# =====================================================
# EXPORT
# =====================================================

TASKS = [
    night_charging_task,
    grid_constraint_task,
    v2g_profit_task,
]