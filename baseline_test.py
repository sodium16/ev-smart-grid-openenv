import json
import requests
from openai import OpenAI

# ----------------------------
# Configuration
# ----------------------------
BASE_URL = "http://localhost:7860"
RESET_ENDPOINT = "/reset"
STEP_ENDPOINT = "/step"
STATE_ENDPOINT = "/state"

# Ollama uses OpenAI-compatible API
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

# ----------------------------
# LLM-assisted policy
# ----------------------------
def llm_policy(observation: dict) -> float:
    """
    Returns a charge_rate_kw based on observation.
    """

    prompt = f"""
You are an EV energy management agent in India.

Observation:
{json.dumps(observation, indent=2)}

Rules:
- If is_grid_active is false, charge_rate_kw must be 0
- Try to reach target_soc before departure
- Prefer charging when electricity price is low
- Avoid aggressive charging

Respond ONLY with JSON:
{{ "charge_rate_kw": number }}
"""

    try:
        response = client.chat.completions.create(
            model="llama3",
            messages=[
                {"role": "system", "content": "You are a cautious EV energy management agent."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )

        raw = response.choices[0].message.content.strip()
        action = json.loads(raw)
        rate = float(action.get("charge_rate_kw", 0.0))

    except Exception as e:
        print(f"⚠️ LLM error: {e}")
        rate = 0.0

    # Safety clamp (AC charging baseline)
    return max(0.0, min(7.2, rate))


# ----------------------------
# Run one task
# ----------------------------
def run_task(task):
    print(f"\n🚀 Running task: {task.name}")

    # 1. Reset environment
    reset_resp = requests.post(f"{BASE_URL}{RESET_ENDPOINT}")
    reset_resp.raise_for_status()
    obs = reset_resp.json()["observation"]

    done = False
    step_count = 0

    # 2. Interaction loop
    while not done and step_count < task.max_steps:
        charge_rate = llm_policy(obs)

        step_resp = requests.post(
            f"{BASE_URL}{STEP_ENDPOINT}",
            json={"charge_rate_kw": charge_rate},
        )
        step_resp.raise_for_status()

        data = step_resp.json()
        obs = data["observation"]
        done = data["done"]

        if step_count % 5 == 0:
            print(
                f"   Step {step_count}: "
                f"SOC={obs['current_soc']:.2f}, "
                f"Grid={obs['is_grid_active']}, "
                f"Price={obs['electricity_price_inr']}"
            )

        step_count += 1

    # 3. Get final state & grade
    state_resp = requests.get(f"{BASE_URL}{STATE_ENDPOINT}")
    state_resp.raise_for_status()
    final_state = state_resp.json()

    score = task.grader(final_state)

    print(f"✅ Finished in {step_count} steps")
    print(f"🎯 Score: {score:.3f}")


# ----------------------------
# Main
# ----------------------------
if __name__ == "__main__":
    from server.tasks import TASKS

    for task in TASKS:
        run_task(task)