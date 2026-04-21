import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .environment import TataNexonEVEnv
from .models import Action, Observation, State
from .tasks import TASKS
from pydantic import BaseModel
import os

class ResetRequest(BaseModel):
    task_name: str = "night_owl"

app = FastAPI(title="NexonGuard: Indian EV Smart Grid")

# ─── CORS: Allow browser-based frontend access ───
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

env = TataNexonEVEnv()
TASK_ID_MAP = {
    "night_owl": TASKS[0],
    "grid_survivor": TASKS[1],
    "v2g_profit": TASKS[2],
}

# ─── Serve frontend if index.html exists at project root ───
FRONTEND_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "index.html")

@app.get("/ui", include_in_schema=False)
def serve_frontend():
    if os.path.exists(FRONTEND_PATH):
        return FileResponse(FRONTEND_PATH)
    return {"message": "Frontend not found. Place index.html in the project root."}


@app.get("/tasks")
def get_tasks():
    """Returns the standardized task list with metadata."""
    return [
        {
            "id": task_id,
            "name": t.name,
            "description": t.description,
            "max_steps": t.max_steps
        } for task_id, t in TASK_ID_MAP.items()
    ]

@app.post("/reset")
def reset(request: ResetRequest = None):
    """Resets the environment for a specific task."""
    obs = env.reset()
    return {"observation": obs}

@app.post("/step")
def step(action: Action):
    """Executes a simulation step."""
    obs, reward, done, info = env.step(action)
    return {
        "observation": obs,
        "reward": reward,
        "done": done,
        "info": info
    }

@app.get("/state")
def get_state() -> State:
    """Returns the internal raw state for the grader."""
    return env.state

@app.get("/grader/{task_id}")
def get_grader(task_id: str):
    """Programmatic grader scoring performance (0.0-1.0)."""
    task = TASK_ID_MAP.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    score = task.grader(env.state.dict())
    return {"score": score}

@app.get("/health")
async def health():
    """Requirement: GET /health returns healthy status"""
    return {"status": "healthy"}

@app.get("/metadata")
async def metadata():
    return {
        "name": "tata-nexon-grid-env",
        "description": "Simulates EV charging in the Indian context, including grid instability and load shedding.",
        "version": "1.0.0",
        "category": "sustainability/engineering"
    }

@app.get("/schema")
async def get_schema():
    return {
        "action": Action.model_json_schema(),
        "observation": Observation.model_json_schema(),
        "state": State.model_json_schema()
    }

@app.post("/mcp")
async def mcp():
    """Requirement: POST /mcp is reachable (Model Context Protocol placeholder)"""
    return {
        "jsonrpc": "2.0",
        "result": {"status": "connected"}
    }

def main():
    """The entry point for the 'server' command."""
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860, reload=False)

if __name__ == "__main__":
    main()