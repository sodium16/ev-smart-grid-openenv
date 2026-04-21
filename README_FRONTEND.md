# NexonGuard Frontend — Setup Guide

## Overview

The `index.html` file is a standalone, zero-dependency* frontend dashboard for the Tata Nexon EV Smart Grid simulator. It connects to the FastAPI backend at `http://localhost:7860` and provides a real-time simulation UI.

> *Only requires Chart.js via CDN (loaded automatically).

---

## Quick Start

### 1. Start the backend server

```bash
# Option A: uvicorn directly
python -m uvicorn server.app:app --host 0.0.0.0 --port 7860

# Option B: via project script
pip install -e .
server

# Option C: Docker
docker build -t tata-nexon-grid-env .
docker run -p 7860:7860 tata-nexon-grid-env
```

### 2. Enable CORS (required for browser access)

Add CORS middleware to `server/app.py` if not already present:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # or restrict to ["null", "http://localhost:*"]
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 3. Open the frontend

Simply open `index.html` in any modern browser:
```bash
# macOS
open index.html

# Linux
xdg-open index.html

# Or serve it with a simple HTTP server
python -m http.server 8080
# Then visit http://localhost:8080
```

---

## Features

| Feature | Description |
|---|---|
| **Task Selector** | Choose Night Charging (easy), Grid Constraint (medium), or V2G Profit (hard) |
| **Live SOC Meter** | Real-time state-of-charge bar with target indicator |
| **Chart Timeline** | Multi-axis chart: SOC%, electricity price, and charge rate over time |
| **Grid Status** | Live indicator for grid active/outage with animated signal bars |
| **Price Ticker** | Off-peak (₹6.5) vs Peak (₹10.0) with mode badge |
| **Violation Counter** | Tracks grid constraint violations (relevant for grid_survivor task) |
| **Score Ring** | Animated circular score display with PASS/FAIL verdict |
| **Event Log** | Real-time timestamped log of simulation events |
| **Speed Control** | 1×, 2×, 5×, ⚡ simulation playback speeds |
| **Demo Mode** | Works without a server — runs local physics simulation |

---

## Demo Mode (no server needed)

If the server is offline, the dashboard automatically runs a **built-in physics simulation** that mirrors the real environment:
- Probabilistic grid outages during peak hours
- SOC physics with stability multiplier
- Battery health degradation
- Dynamic pricing based on time-of-day

This makes the demo fully self-contained for presentations.

---

## Architecture

```
index.html
├── Chart.js (CDN) — timeline visualization
├── Fetch API — connects to FastAPI backend
├── Smart Policy — computes charge rates per step
└── Fallback Physics — demo mode when offline
```

### API Calls Made

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Server connectivity check |
| `POST` | `/reset` | Initialize episode with task |
| `POST` | `/step` | Advance simulation one 15-min step |
| `GET` | `/grader/{task_id}` | Fetch final score |

---

## Customization

### Change server URL
At the top of the `<script>` tag in `index.html`:
```js
const SERVER_URL = 'http://localhost:7860';
```

### Change scoring threshold
```js
const PASS_THRESHOLD = 0.70; // default
```

### Adjust smart policy
The `computeAction(obs)` function implements the charging policy. Modify it to test different strategies:
```js
function computeAction(obs) {
  // Your custom logic here
  return chargeRateKw; // between -15.0 and 50.0
}
```