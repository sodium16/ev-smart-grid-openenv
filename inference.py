import os
import json
import requests
from typing import List
from openai import OpenAI
from server.tasks import TASKS

# 1. Mandatory Variable Mapping
API_BASE_URL = os.getenv("API_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME")
HF_TOKEN = os.getenv("HF_TOKEN")
APP_URL = "http://localhost:7860" # Local internal URL for Docker/Space

client = OpenAI(api_key=HF_TOKEN, base_url=API_BASE_URL)

# 2. Mandatory Structured Logging Functions
def log_start(task: str, env_name: str, model: str):
    print(f"[START] {json.dumps({'task': task, 'env': env_name, 'model': model})}", flush=True)

def log_step(step: int, action: float, reward: float, done: bool, error: str = None):
    print(f"[STEP] {json.dumps({'step': step, 'action': action, 'reward': reward, 'done': done, 'error': error})}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]):
    print(f"[END] {json.dumps({'success': success, 'steps': steps, 'score': score, 'rewards': rewards})}", flush=True)

def llm_policy(observation: dict) -> float:
    """EV Energy Management Policy"""
    prompt = f"Observation: {json.dumps(observation)}. Respond ONLY with JSON: {{'charge_rate_kw': number}}"
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        data = json.loads(response.choices[0].message.content)
        return float(data.get("charge_rate_kw", 0.0))
    except Exception as e:
        return 0.0

def run_submission():
    for task in TASKS:
        # Reset Env
        reset_resp = requests.post(f"{APP_URL}/reset")
        obs = reset_resp.json()["observation"]
        
        log_start(task=task.name, env_name="tata-nexon-grid-env", model=MODEL_NAME)
        
        rewards = []
        steps_taken = 0
        done = False
        
        while not done and steps_taken < task.max_steps:
            steps_taken += 1
            action_val = llm_policy(obs)
            
            # Step Env
            step_resp = requests.post(f"{APP_URL}/step", json={"charge_rate_kw": action_val})
            res = step_resp.json()
            
            obs = res["observation"]
            reward = res.get("reward", 0.0)
            done = res.get("done", False)
            rewards.append(reward)
            
            log_step(step=steps_taken, action=action_val, reward=reward, done=done)
            
        # Get Final Grade
        task_id = task.name.lower().replace(" ", "_")
        grade_resp = requests.get(f"{APP_URL}/grader/{task_id}")
        score = grade_resp.json().get("score", 0.0)
        
        log_end(success=(score >= 0.7), steps=steps_taken, score=score, rewards=rewards)

if __name__ == "__main__":
    run_submission()