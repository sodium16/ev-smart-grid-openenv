# Tata Nexon Smart Grid OpenEnv

OpenEnv-compatible EV charging simulator focused on Indian residential grid conditions. The environment models charging and V2G behavior under time-varying tariffs, probabilistic grid outages, and battery degradation constraints.

This repository is designed for evaluator-friendly reproducibility:
- Deterministic grading endpoints per task
- FastAPI runtime with schema introspection
- Dockerized deployment path
- LLM-policy baseline runner via OpenAI-compatible API

## Quick Start

### Prerequisites
- Python 3.10+
- Optional: Docker
- Optional: local LLM endpoint (Ollama) or hosted OpenAI-compatible endpoint

### Option A: venv + pip
```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

### Option B: uv
```bash
uv sync
```

### Run the API server
```bash
python -m uvicorn server.app:app --host 0.0.0.0 --port 7860
```

Server base URL: `http://localhost:7860`

### Validate submission compatibility
```bash
sh validate-submission.sh http://localhost:7860 .
```

## Why This Environment

The simulator targets practical EV optimization in Indian grid conditions:
- **Load shedding and voltage stress** around evening peak windows
- **Dynamic electricity pricing** (off-peak vs peak slabs)
- **Hardware diversity** from home AC charging to DC fast charging
- **Battery health impact** from aggressive charging/discharging behavior

## Environment Contract

Contract is defined by `openenv.yaml` and mirrored in Pydantic models.

### Action Space

| Field | Type | Bounds | Meaning |
| --- | --- | --- | --- |
| `charge_rate_kw` | float | `[-15.0, 50.0]` | Positive = charging, negative = V2G discharge |

### Observation Space

| Field | Type | Meaning |
| --- | --- | --- |
| `current_soc` | float | Battery state of charge in `[0.0, 1.0]` |
| `battery_health_soh` | float | Battery state of health in `[0.0, 1.0]` |
| `electricity_price_inr` | float | Current tariff in INR per unit |
| `is_grid_active` | bool | Grid availability flag |
| `time_of_day` | str | Simulation time formatted as `HH:MM` |
| `user_type` | str | Current archetype label |
| `target_soc` | float | Required SoC goal |
| `user_history` | list[float] | Last 5 synthetic departure-time observations |

### Internal State (for grading/debug)

`GET /state` returns extended state including:
- `current_hour`
- `total_bill_inr`
- `departure_time`

## Task Set and Scoring

Three built-in tasks are exposed by `GET /tasks` and scored via `GET /grader/{task_id}`.

| Task ID | Name | Difficulty | Max Steps | Grading Emphasis |
| --- | --- | --- | --- | --- |
| `night_owl` | Night Charging | easy | 48 | SoC completion + cost efficiency |
| `grid_survivor` | Grid Constraint | medium | 48 | SoC + grid-aware behavior + cost |
| `v2g_profit` | V2G Profit Optimization | hard | 72 | SoC + net bill/profit + SoH preservation |

### Baseline reference scores

| Task ID | Threshold | Baseline |
| --- | --- | --- |
| `night_owl` | `0.70` | `0.742` |
| `grid_survivor` | `0.70` | `0.911` |
| `v2g_profit` | `0.70` | `0.767` |

## API Reference

### `GET /health`
Returns service status.

Example response:
```json
{ "status": "healthy" }
```

### `GET /metadata`
Returns environment metadata (name, description, version, category).

### `GET /schema`
Returns JSON schema for action, observation, and state contracts.

### `GET /tasks`
Returns task descriptors (`id`, `name`, `description`, `max_steps`).

### `POST /reset`
Resets episode state and returns initial observation.

Example request:
```json
{}
```

Example response:
```json
{
	"observation": {
		"current_soc": 0.24,
		"battery_health_soh": 1.0,
		"electricity_price_inr": 6.5,
		"is_grid_active": true,
		"time_of_day": "22:00",
		"user_type": "amazon_fleet",
		"target_soc": 0.9,
		"user_history": [6.03, 6.11, 5.94, 6.08, 5.99]
	}
}
```

### `POST /step`
Advances one 15-minute step.

Example request:
```json
{ "charge_rate_kw": 12.5 }
```

Example response:
```json
{
	"observation": {
		"current_soc": 0.31,
		"battery_health_soh": 0.9999,
		"electricity_price_inr": 6.5,
		"is_grid_active": true,
		"time_of_day": "22:15",
		"user_type": "amazon_fleet",
		"target_soc": 0.9,
		"user_history": [6.03, 6.11, 5.94, 6.08, 5.99]
	},
	"reward": 0.14,
	"done": false,
	"info": {
		"info": "step successful"
	}
}
```

### `GET /state`
Returns full internal state object.

### `GET /grader/{task_id}`
Returns deterministic final score for current episode state.

Example response:
```json
{ "score": 0.811 }
```

### `POST /mcp`
Connectivity placeholder for MCP-style checks.

## Simulation Details

### Time and pricing
- Step size: `0.25h` (15 minutes)
- Peak window: `18:00` to `22:00`
- Peak tariff: `10.0`
- Off-peak tariff: `6.5`

### Grid dynamics
- `is_grid_active` sampled each step with higher outage chance during peak
- Stability multiplier scales delivered power (`actual_kw = requested_kw * stability`)

### Battery model
- Nominal capacity: `45.0 kWh`
- Hardware limits in environment constants include AC and DC rates
- SoH degradation scales with C-rate squared and applies stronger penalty for high-rate usage

## Inference Runner

`inference.py` provides a baseline LLM policy loop:
1. Reset each task
2. Call model with current observation
3. Submit action to `/step`
4. Grade at `/grader/{task_id}`
5. Emit structured logs (`[START]`, `[STEP]`, `[END]`)

### Environment variables

Use `.env.example` for defaults:

| Variable | Purpose | Example |
| --- | --- | --- |
| `API_BASE_URL` | OpenAI-compatible endpoint | `https://api.openai.com/v1` |
| `MODEL_NAME` | Model identifier | `gpt-4o` or `llama3` |
| `HF_TOKEN` | API key/token | `your_openai_key_here` |
| `PORT` | Server port | `7860` |

Run inference:
```bash
python inference.py
```

## Docker

Build and run:
```bash
docker build -t tata-nexon-grid-env .
docker run -p 7860:7860 tata-nexon-grid-env
```

Container startup command uses:
```bash
python -m uvicorn server.app:app --host 0.0.0.0 --port 7860
```

## Development and Testing

### Physics script
```bash
python test_physics.py
```

### Validation script
```bash
sh validate-submission.sh http://localhost:7860 .
```

The validator checks:
1. `POST /reset` returns HTTP `200`
2. Docker image builds successfully
3. `/schema` exposes expected action constraints

## Repository Structure

```text
ev-smart-grid-openenv/
├── data/
│   └── user_profiles.json
├── server/
│   ├── __init__.py
│   ├── app.py
│   ├── environment.py
│   ├── models.py
│   ├── tasks.py
│   └── utils.py
├── .env
├── .env.example
├── Dockerfile
├── inference.py
├── openenv.yaml
├── pyproject.toml
├── requirements.txt
├── test_physics.py
├── uv.lock
└── validate-submission.sh
```

## Tech Stack

- FastAPI
- Pydantic
- Uvicorn
- OpenAI Python SDK
- Requests/httpx
- OpenEnv Core

## Roadmap

- Add richer evaluator diagnostics at episode end
- Expand user-profile driven initialization from external data
- Add scenario-specific benchmark policies (rule-based and RL)
- Extend metrics for grid stress and V2G profitability analysis
