import uvicorn
from fastapi import FastAPI, HTTPException
from .environment import TataNexonEVEnv
from .models import Action, Observation, State
from .tasks import TASKS # Import the task list

app = FastAPI(title="NexonGuard: Indian EV Smart Grid")
env = TataNexonEVEnv()

@app.get("/tasks")
def get_tasks():
    """Returns the standardized task list with metadata."""
    return [
        {
            "id": t.name.lower().replace(" ", "_"),
            "name": t.name,
            "description": t.description,
            "max_steps": t.max_steps
        } for t in TASKS
    ]

@app.post("/reset")
def reset(task_id: str = "night_charging"):
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
    # Find the task in TASKS list
    task = next((t for t in TASKS if t.name.lower().replace(" ", "_") == task_id), None)
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
        "version": "0.1.0",           # Matches your pyproject.toml
        "category": "sustainability/engineering"
    }

@app.get("/schema")
async def get_schema():
    # We use .model_json_schema() but we can clean it if needed.
    # Usually, the validator is happy if the types and constraints match.
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
    uvicorn.run("server.app:app", host = "0.0.0.0", port = 7860, reload = False)

if __name__ == "__main__":
    main();