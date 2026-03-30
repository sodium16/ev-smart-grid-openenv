from fastapi import FastAPI, HTTPException
from typing import List, Dict, Any

# Internal imports from Vishwas's work
from server.models import Action, Observation, State
from server.environment import TataNexonEVEnv
# Note: Assuming Amogh creates a tasks.py with a TASK_REGISTRY
# from server.tasks import TASK_REGISTRY 

app = FastAPI(title="Tata Nexon EV Smart Grid OpenEnv")

# Initialize the simulator
env = TataNexonEVEnv()

@app.get("/tasks")
async def get_tasks():
    """Returns the tasks available for the agent."""
    # Placeholder for Amogh's task logic
    return [
        {"id": "night_owl", "name": "The Night Owl", "difficulty": "easy"},
        {"id": "fleet_manager", "name": "Fleet Manager", "difficulty": "medium"},
        {"id": "energy_arbitrage", "name": "V2G Arbitrage", "difficulty": "hard"}
    ]

@app.post("/reset")
async def reset(task_id: str = "night_owl") -> Observation:
    """Resets the environment to initial state."""
    # For now, just calls Vishwas's reset
    return env.reset()

@app.post("/step")
async def step(action: Action):
    """Executes a 15-minute time step in the simulation."""
    obs, reward, done, info = env.step(action)
    return {
        "observation": obs,
        "reward": reward,
        "done": done,
        "info": info
    }

@app.get("/state")
async def get_state() -> State:
    """Returns the internal raw state of the battery and grid."""
    return env.state

@app.get("/grader/{task_id}")
async def get_grader(task_id: str):
    """Calculates the score based on SoC and Bill."""
    state = env.state
    # Logic: High SoC + Low Bill = High Score
    if state.current_soc >= 0.8:
        score = 1.0 - (state.total_bill_inr / 500.0) # Penalty for high cost
        return {"score": max(0.0, score)}
    return {"score": 0.0}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)