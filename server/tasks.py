from typing import Callable, Dict, Any
from enum import Enum


class Task:
    def __init__(
        self,
        name: str,
        description: str,
        max_steps: int,
        grader: Callable[[Dict[str, Any]], float],
    ):
        self.name = name
        self.description = description
        self.max_steps = max_steps
        self.grader = grader


# =====================================================
# EASY TASK — Night Charging (Cost-aware SOC completion)
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

    score = 0.0

    # Primary objective: reach target SOC
    if current_soc >= target_soc:
        score += 0.7
    else:
        score += 0.7 * (current_soc / target_soc)

    # Secondary objective: keep cost low (₹)
    # Assume ₹350 is a "reasonable" overnight bill
    cost_penalty = min(total_bill / 350.0, 1.0)
    score += 0.3 * (1.0 - cost_penalty)

    return round(max(0.0, min(1.0, score)), 3)


night_charging_task = Task(
    name="Night Charging",
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
    """

    current_soc = state.get("current_soc", 0.0)
    target_soc = state.get("target_soc", 1.0)
    grid_active = state.get("is_grid_active", True)
    total_bill = state.get("total_bill_inr", 0.0)

    score = 0.0

    # SOC completion (most important)
    if current_soc >= target_soc:
        score += 0.6
    else:
        score += 0.6 * (current_soc / target_soc)

    # Grid friendliness reward
    if grid_active:
        score += 0.25

    # Cost awareness
    cost_penalty = min(total_bill / 400.0, 1.0)
    score += 0.15 * (1.0 - cost_penalty)

    return round(max(0.0, min(1.0, score)), 3)


grid_constraint_task = Task(
    name="Grid Constraint",
    description="Charge the EV while respecting grid availability and minimizing stress.",
    max_steps=48,
    grader=grid_constraint_grader,
)


# =====================================================
# HARD TASK — User-Aware Cost & Battery Optimization
# =====================================================

def v2g_profit_grader(state: Dict[str, Any]) -> float:
    """
    Goal:
    - Minimize electricity bill
    - Maintain battery health (SOH)
    - Reach target SOC
    """

    current_soc = state.get("current_soc", 0.0)
    target_soc = state.get("target_soc", 1.0)
    soh = state.get("soh", 1.0)
    total_bill = state.get("total_bill_inr", 0.0)

    # Normalize components
    soc_score = min(current_soc / target_soc, 1.0)
    health_penalty = max(0.0, 1.0 - soh)          # 0 = perfect, ↑ worse
    cost_penalty = min(total_bill / 500.0, 1.0)  # normalize bill

    # Core formula (as required conceptually)
    score = (soc_score * (1.0 - cost_penalty)) - health_penalty

    return round(max(0.0, min(1.0, score)), 3)


v2g_profit_task = Task(
    name="V2G Profit Optimization",
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