import os
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# ----------------------------
# Toggle Configuration
# ----------------------------
# 1. To use OLLAMA: Keep OPENAI_API_KEY empty or set to 'ollama' in .env
# 2. To use OPENAI: Set actual OPENAI_API_KEY in .env and comment out OPENAI_BASE_URL
# 3. For the Judges: They will provide OPENAI_API_KEY via env vars.

API_KEY = os.getenv("OPENAI_API_KEY", "ollama")
BASE_URL = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1") # Default to local Ollama
MODEL = os.getenv("OPENAI_MODEL", "llama3") # Change to 'gpt-4o' or similar for production

# The 'if' ensures that if the judges don't provide a Base URL, it uses OpenAI's official one.
client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL if os.getenv("OPENAI_BASE_URL") else None
)

# App Configuration
APP_URL = "http://localhost:7860"
RESET_ENDPOINT = f"{APP_URL}/reset"
STEP_ENDPOINT = f"{APP_URL}/step"
STATE_ENDPOINT = f"{APP_URL}/state"

# ----------------------------
# LLM-assisted policy
# ----------------------------
def llm_policy(observation: dict) -> float:
    """
    Decides the optimal charging rate based on environment observations.
    """

    prompt = f"""
You are the Energy Management System for a Tata Nexon EV in Bangalore, India.
Your goal is to optimize charging based on cost, battery health, and user departure patterns.

Observation:
{json.dumps(observation, indent=2)}

Strategic Rules:
1. Safety First: If is_grid_active is False, you CANNOT charge (set charge_rate_kw to 0).
2. Economics: Indian peak hours are 6PM-10PM (₹10/kWh). Off-peak is ₹6.5/kWh. 
3. V2G Opportunity: If price is high (₹10) and SOC is > 80%, you can sell power (negative charge_rate_kw).
4. Battery Health: Avoid aggressive DC charging (> 22kW) unless the user is leaving soon.
5. User History: Analyze the 'user_history' to predict the secret departure time.

Respond ONLY with a JSON object:
{{
  "reasoning": "Brief explanation of your strategy",
  "charge_rate_kw": number (-15.0 to 50.0)
}}
Crucial: If the current SOC is already at or above target_soc, STOP charging (set charge_rate_kw to 0) to avoid wasting money, or set a negative rate during peak hours (₹10/kWh) to sell power back to the grid.
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a professional EV fleet optimizer."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            response_format={ "type": "json_object" } # Ensures strict JSON output
        )

        raw = response.choices[0].message.content.strip()
        data = json.loads(raw)
        rate = float(data.get("charge_rate_kw", 0.0))
        
        # Logging reasoning helps you debug why the LLM is making certain choices
        print(f"   [LLM Reasoning]: {data.get('reasoning')}")

    except Exception as e:
        print(f"⚠️ LLM error: {e}")
        rate = 0.0

    # Safety clamp based on Tata Nexon specs
    return max(-15.0, min(50.0, rate))


# ----------------------------
# Task Execution Loop
# ----------------------------
def run_task(task):
    print(f"\n" + "="*50)
    print(f"🚀 MISSION: {task.name}")
    print(f"📝 {task.description}")
    print("="*50)

    # 1. Reset environment
    # Sending task_name in body to match Shreya's ResetRequest model
    reset_resp = requests.post(RESET_ENDPOINT, json={"task_name": task.name})
    reset_resp.raise_for_status()
    obs = reset_resp.json()["observation"]

    print(f"🏠 Start SOC: {obs['current_soc']*100:.1f}% | User: {obs['user_type']}")

    done = False
    step_count = 0
    cumulative_reward = 0.0

    # 2. Interaction loop
    while not done and step_count < task.max_steps:
        charge_rate = llm_policy(obs)

        step_resp = requests.post(
            STEP_ENDPOINT,
            json={"charge_rate_kw": charge_rate},
        )
        step_resp.raise_for_status()

        data = step_resp.json()
        obs = data["observation"]
        reward = data["reward"]
        done = data["done"]
        cumulative_reward += reward

        if step_count % 4 == 0: # Print every hour (4 steps * 15 min)
            print(
                f"   🕒 {obs['time_of_day']} | SOC: {obs['current_soc']*100:>4.1f}% | "
                f"Grid: {'ON' if obs['is_grid_active'] else 'OFF'} | Reward: {reward:+.4f}"
            )

        step_count += 1

    # 3. Final Grading
    state_resp = requests.get(STATE_ENDPOINT)
    state_resp.raise_for_status()
    final_state = state_resp.json()

    # Calculate final score using Amogh's grader
    score = task.grader(final_state)

    print("-" * 50)
    print(f"✅ Finished Task: {task.name}")
    print(f"📊 Total Steps: {step_count}")
    print(f"💰 Total Reward: {cumulative_reward:.4f}")
    print(f"🎯 FINAL SCORE: {score:.3f}")
    print("-" * 50)


# ----------------------------
# Main Execution
# ----------------------------
if __name__ == "__main__":
    from server.tasks import TASKS
    
    # Check if server is up
    try:
        requests.get(APP_URL)
    except requests.exceptions.ConnectionError:
        print(f"❌ ERROR: FastAPI server is not running on {APP_URL}")
        exit(1)

    for task in TASKS:
        run_task(task)