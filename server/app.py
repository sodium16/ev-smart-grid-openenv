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