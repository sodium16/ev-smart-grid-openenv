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
# HELPER: Safe SOC Calculator
# =====================================================

def calculate_soc_component(state: Dict[str, Any], weight: float) -> float:
    """Calculates a weighted SOC score strictly between 0 and weight."""
    current_soc = state.get("current_soc", 0.0)
    target_soc = state.get("target_soc", 1.0)
    
    if target_soc <= 0:
        return 0.01 * weight
        
    # Limit internal ratio to 0.99 to avoid hitting boundaries too early
    ratio = min(current_soc / target_soc, 0.99)
    return weight * ratio


# =====================================================
# EASY TASK — Night Charging
# =====================================================

def night_charging_grader(state: Dict[str, Any]) -> float:
    """
    Goal:
    - Reach target SOC by departure
    - Prefer off-peak (cheap) charging
    """
    # Primary: SOC completion (0.0 -> 0.7)
    score = calculate_soc_component(state, 0.7)

    # Secondary: cost efficiency (0.0 -> 0.3)
    # ₹350 is a reasonable overnight full-charge bill; reward staying under it
    total_bill = state.get("total_bill_inr", 0.0)
    cost_ratio = min(total_bill / 350.0, 0.99)
    score += 0.3 * (1.0 - cost_ratio)

    # Final enforcement: Must be strictly between (0, 1)
    return round(max(0.01, min(0.99, score)), 3)


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
    # SOC completion (0.0 -> 0.6)
    score = calculate_soc_component(state, 0.6)

    # Grid constraint adherence (0.0 -> 0.25)
    # Each violation during grid-off costs 0.05
    grid_violations = state.get("grid_violation_count", 0)
    violation_penalty = min(grid_violations * 0.05, 0.24) # Cap penalty slightly below total weight
    score += (0.25 - violation_penalty)

    # Cost awareness (0.0 -> 0.15)
    total_bill = state.get("total_bill_inr", 0.0)
    cost_ratio = min(total_bill / 400.0, 0.99)
    score += 0.15 * (1.0 - cost_ratio)

    return round(max(0.01, min(0.99, score)), 3)


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
    """
    # Component 1: SOC completion (0.0 -> 0.40)
    score = calculate_soc_component(state, 0.40)

    # Component 2: Cost/profit performance (0.0 -> 0.35)
    net_bill = state.get("total_bill_inr", 0.0)
    # Map [-200, 500] -> [1.0, 0.0] linearly
    cost_perf = 1.0 - ((net_bill + 200.0) / 700.0)
    score += 0.35 * max(0.01, min(0.99, cost_perf))

    # Component 3: Battery health preservation (0.0 -> 0.25)
    soh = state.get("battery_health_soh", 1.0)
    health_score = max(0.01, min(0.99, soh)) # Direct map SOH to score component
    score += 0.25 * health_score

    return round(max(0.01, min(0.99, score)), 3)


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