import os
import json
import requests
from typing import List
from openai import OpenAI
from server.tasks import TASKS

# ─── Mandatory Variables ──────────────────────────────────────────────────────
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:11434/v1")
MODEL    = os.getenv("MODEL_NAME", "llama3")
API_KEY  = os.getenv("HF_TOKEN", "ollama")
APP_URL      = "http://localhost:7860"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# ─── Mandatory Structured Logging ────────────────────────────────────────────
def log_start(task: str, env_name: str, model: str):
    print(f"[START] {json.dumps({'task': task, 'env': env_name, 'model': model})}", flush=True)

def log_step(step: int, action: float, reward: float, done: bool, error: str = None):
    print(f"[STEP] {json.dumps({'step': step, 'action': action, 'reward': reward, 'done': done, 'error': error})}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]):
    print(f"[END] {json.dumps({'success': success, 'steps': steps, 'score': score, 'rewards': rewards})}", flush=True)

# ─── LLM Policy ──────────────────────────────────────────────────────────────
def llm_policy(observation: dict) -> float:
    """
    EV Energy Management Policy.
    Returns a charge_rate_kw value. Positive = charging, negative = V2G discharge.
    """
    system_prompt = (
        "You are an EV charging optimization agent. "
        "Given an observation, decide the charge rate in kW. "
        "Positive values charge the battery, negative values discharge to grid (V2G). "
        "Respond ONLY with valid JSON: {\"charge_rate_kw\": <number between -15.0 and 50.0>}. "
        "No extra text, no markdown."
    )
    user_prompt = f"Current observation: {json.dumps(observation)}"

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content)
        raw = float(data.get("charge_rate_kw", 0.0))
        # Clamp to action space bounds defined in openenv.yaml
        return max(-15.0, min(50.0, raw))
    except Exception:
        return 0.0   # safe fallback: do nothing


# ─── Main Runner ─────────────────────────────────────────────────────────────
def run_submission():
    for task in TASKS:
        # Reset environment for this specific task using task_id from openenv.yaml
        reset_resp = requests.post(
            f"{APP_URL}/reset",
            json={"task_id": task.task_id},
        )
        reset_resp.raise_for_status()
        obs = reset_resp.json()["observation"]

        log_start(
            task=task.task_id,
            env_name="tata-nexon-grid-env",
            model=MODEL,
        )

        rewards: List[float] = []
        steps_taken = 0
        done = False

        while not done and steps_taken < task.max_steps:
            steps_taken += 1
            action_val = llm_policy(obs)

            step_resp = requests.post(
                f"{APP_URL}/step",
                json={"charge_rate_kw": action_val},
            )
            step_resp.raise_for_status()
            res = step_resp.json()

            obs    = res["observation"]
            reward = float(res.get("reward", 0.0))
            done   = bool(res.get("done", False))
            error  = res.get("error", None)

            rewards.append(reward)
            log_step(step=steps_taken, action=action_val, reward=reward, done=done, error=error)

        # Grade the completed episode using task_id (matches openenv.yaml + grader endpoint)
        grade_resp = requests.get(f"{APP_URL}/grader/{task.task_id}")
        grade_resp.raise_for_status()
        score = float(grade_resp.json().get("score", 0.0))

        log_end(
            success=(score >= 0.7),
            steps=steps_taken,
            score=score,
            rewards=rewards,
        )


if __name__ == "__main__":
    run_submission()