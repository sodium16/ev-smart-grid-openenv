import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi import FastAPI
from .environment import TataNexonEVEnv
from .models import Action

app = FastAPI(title="EV Smart Grid OpenEnv")

# Global environment instance
env = TataNexonEVEnv()


from typing import Optional
from pydantic import BaseModel

class ResetRequest(BaseModel):
    task_name: Optional[str] = None


@app.post("/reset")
def reset(req: ResetRequest = ResetRequest()):
    obs = env.reset()
    return {
        "observation": obs
    }


@app.post("/step")
def step(action: Action):
    obs, reward, done, info = env.step(action)
    return {
        "observation": obs,
        "reward": reward,
        "done": done,
        "info": info
    }


@app.get("/state")
def state():
    return env.state
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
