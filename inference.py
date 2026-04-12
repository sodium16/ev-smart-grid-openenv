#!/usr/bin/env python3
"""
inference.py - OpenEnv Inference Script for Tata Nexon EV Smart Grid
Runs all three tasks with LLM policy and emits structured logs.
"""

import os
import json
import textwrap
from typing import List, Dict, Any, Optional

from openai import OpenAI
import requests

# Environment variables — NO defaults for critical ones
API_BASE_URL = os.getenv("API_BASE_URL") or "https://api.openai.com/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "gpt-3.5-turbo"
HF_TOKEN = os.getenv("HF_TOKEN")

if not HF_TOKEN:
    raise ValueError("HF_TOKEN environment variable is required")

# Initialize OpenAI Client
client = OpenAI(
    api_key=HF_TOKEN,
    base_url=API_BASE_URL
)

# Server endpoint (local or remote)
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:7860")

SYSTEM_PROMPT = textwrap.dedent(
    """
    You are an EV charging optimization AI agent. You must decide how much to charge (or discharge via V2G) 
    at each 15-minute step based on:
    - Current battery state of charge (SoC)
    - Target SoC before departure
    - Current electricity price (peak vs off-peak)
    - Grid availability
    - Battery health
    
    Reply with ONLY a single number between -15.0 and 50.0 (kW).
    No explanations, no quotes, just the number.
    """
).strip()

TASKS = ["night_owl", "grid_survivor", "v2g_profit"]


def log_start(task: str, env: str, model: str) -> None:
    """Emit [START] log"""
    print(f"[START] task={task} env=tata-nexon-grid-env model={model}", flush=True)


def log_step(
    step: int, 
    action: str, 
    reward: float, 
    done: bool, 
    error: Optional[str]
) -> None:
    """Emit [STEP] log"""
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(
    success: bool, 
    steps: int, 
    score: float, 
    rewards: List[float]
) -> None:
    """Emit [END] log"""
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    success_val = str(success).lower()
    print(
        f"[END] success={success_val} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


def build_lm_prompt(step: int, obs: Dict[str, Any], last_reward: float) -> str:
    """Build prompt for LLM decision-making"""
    return textwrap.dedent(
        f"""
        Step: {step}
        Current SoC: {obs['current_soc']:.2f}
        Target SoC: {obs['target_soc']:.2f}
        Battery Health: {obs['battery_health_soh']:.3f}
        Electricity Price (INR): {obs['electricity_price_inr']:.1f}
        Grid Active: {obs['is_grid_active']}
        Time: {obs['time_of_day']}
        Last Reward: {last_reward:.2f}
        
        Decide charge rate in kW (negative = V2G discharge, positive = charging).
        Reply with only a number between -15.0 and 50.0.
        """
    ).strip()


def get_lm_action(step: int, obs: Dict[str, Any], last_reward: float) -> float:
    """Call LLM to get next action"""
    prompt = build_lm_prompt(step, obs, last_reward)
    
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=50,
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip()
        
        # Parse the number from response
        try:
            charge_rate = float(text)
            # Clamp to valid range
            charge_rate = max(-15.0, min(50.0, charge_rate))
            return charge_rate
        except ValueError:
            # If parsing fails, return safe default (no action)
            return 0.0
            
    except Exception as exc:
        print(f"[DEBUG] LLM request failed: {exc}", flush=True)
        return 0.0


def run_task(task_id: str) -> Dict[str, Any]:
    """Run a single task with LLM policy"""
    
    log_start(task=task_id, env="tata-nexon-grid-env", model=MODEL_NAME)
    
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False
    last_error = None
    
    try:
        # Reset the environment for this task
        reset_resp = requests.post(
            f"{SERVER_URL}/reset",
            json={"task_name": task_id},
            timeout=10
        )
        reset_resp.raise_for_status()
        reset_data = reset_resp.json()
        obs = reset_data["observation"]
        last_reward = 0.0
        
        max_steps = 48 if task_id in ["night_owl", "grid_survivor"] else 72
        
        for step in range(1, max_steps + 1):
            # Get action from LLM
            charge_rate = get_lm_action(step, obs, last_reward)
            action_str = f"charge_rate={charge_rate:.2f}"
            
            # Step the environment
            step_resp = requests.post(
                f"{SERVER_URL}/step",
                json={"charge_rate_kw": charge_rate},
                timeout=10
            )
            step_resp.raise_for_status()
            step_data = step_resp.json()
            
            obs = step_data["observation"]
            reward = step_data.get("reward", 0.0)
            done = step_data.get("done", False)
            
            rewards.append(reward)
            steps_taken = step
            last_reward = reward
            last_error = None
            
            log_step(
                step=step,
                action=action_str,
                reward=reward,
                done=done,
                error=last_error
            )
            
            if done:
                break
        
        # Get final score from grader
        grader_resp = requests.get(
            f"{SERVER_URL}/grader/{task_id}",
            timeout=10
        )
        grader_resp.raise_for_status()
        grader_data = grader_resp.json()
        score = grader_data.get("score", 0.0)
        
        # Clamp to [0, 1]
        score = max(0.0, min(1.0, score))
        success = score >= 0.70  # Threshold from README
        
    except Exception as exc:
        last_error = str(exc)
        print(f"[DEBUG] Task {task_id} error: {exc}", flush=True)
        success = False
    
    finally:
        log_end(
            success=success,
            steps=steps_taken,
            score=score,
            rewards=rewards
        )
    
    return {
        "task_id": task_id,
        "steps": steps_taken,
        "score": score,
        "rewards": rewards,
        "success": success
    }


def main() -> None:
    """Run all three tasks"""
    print("[DEBUG] Starting inference.py", flush=True)
    print(f"[DEBUG] API_BASE_URL: {API_BASE_URL}", flush=True)
    print(f"[DEBUG] MODEL_NAME: {MODEL_NAME}", flush=True)
    print(f"[DEBUG] SERVER_URL: {SERVER_URL}", flush=True)
    
    all_results = []
    
    for task_id in TASKS:
        result = run_task(task_id)
        all_results.append(result)
        print(f"[DEBUG] Task {task_id} complete: score={result['score']:.3f}", flush=True)
    
    # Summary
    avg_score = sum(r["score"] for r in all_results) / len(all_results)
    total_success = sum(1 for r in all_results if r["success"])
    
    print(f"[DEBUG] Inference complete. Avg score: {avg_score:.3f}, Successful: {total_success}/{len(all_results)}", flush=True)
    
    return {
        "tasks": all_results,
        "average_score": avg_score,
        "successful_tasks": total_success
    }


if __name__ == "__main__":
    main()