import random

def generate_user_history(avg_dep: float, variance: float) -> list[float]:
    """
    Generates 5 days of synthetic departure times based on user archetypes.
    - Amazon: Tight variance (e.g., 0.1)
    - Personal: Wide variance (e.g., 1.5)
    """
    history = []
    for _ in range(5):
        # Use Gaussian distribution to simulate human-like 'mostly-consistent' behavior
        time = random.gauss(avg_dep, variance)
        # Keep times within a logical 24-hour window for the display
        history.append(round(max(0.0, min(23.9, time)), 2))
    return history