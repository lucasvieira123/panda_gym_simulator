# Self-Adaptive Arm Simulator

> Franka Panda robotic arm simulation with a MAPE-K feedback loop for autonomous task adaptation — built on PyBullet and panda-gym, controlled through a REST API.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![PyBullet](https://img.shields.io/badge/PyBullet-3.2.7-green)
![panda--gym](https://img.shields.io/badge/panda--gym-3.0.7-green)
![FastAPI](https://img.shields.io/badge/FastAPI-REST-orange)

---

## Overview

The simulator runs as two independent Python processes that communicate over HTTP:

```
┌──────────────────────┐        GET /perception        ┌──────────────────────┐
│      manager/        │  ─────────────────────────►  │      managing/        │
│   MAPE-K loop        │                               │   PyBullet + panda-gym│
│  Monitor→Analyze     │  ◄─────────────────────────  │   FastAPI on :8000    │
│  →Plan→Execute       │        PUT /task              └──────────────────────┘
└──────────────────────┘
```

- **`managing/`** — owns the physics engine (PyBullet), executes robot tasks, and exposes perception via FastAPI.
- **`manager/`** — reads live perception and issues adaptation commands when the situation changes.

---

## MAPE-K Architecture

Each perception step flows through four stages. Situation classification and strategy mapping are defined entirely in YAML — no code changes needed to add new adaptive behaviors.

| Stage | Responsibility | File |
|---|---|---|
| **Monitor** | Reads raw perception from the API and populates `SystemState` | `monitor.py` |
| **Analyze** | Evaluates Python expressions from YAML to classify the current situation | `analyze.py` |
| **Plan** | Maps the classified situation to a task strategy via `plan_options.yaml` | `plan.py` |
| **Execute** | Issues a `PUT /task` command to the simulator when the strategy changes | `execute.py` |

---

## Installation

### Prerequisites

- Python 3.11+
- Windows (the `run.sh` script uses `mintty`) — or start each process manually on any OS

### Setup

```bash
# Clone the repository
git clone https://github.com/lucasvieira123/panda_gym_simulator.git
cd panda_gym_simulator

# Create a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux / macOS

# Install dependencies
pip install -r requirements.txt
```

---

## Running

### Quick start (Windows — mintty)

```bash
bash run.sh
```

Opens two terminal windows: one for the simulator (`managing/`) and one for the MAPE-K manager (`manager/`).

### Manual start (any OS)

```bash
# Terminal 1 — simulator
cd managing
python main.py

# Terminal 2 — MAPE-K manager
cd manager
python main.py
```

> **Note:** The simulator exposes a REST API on `http://localhost:8000`. Start the simulator before the manager.

---

## Configuration

All behavior is driven by YAML. **Restart the simulator after any change.**

| File | Location | Controls |
|---|---|---|
| `simulation.yaml` | `managing/configs/` | Episodes, seed, step delay, task parameters (grasp height, approach height, friction offsets) |
| `environment*.yaml` | `managing/configs/environments/` | Robot, table, objects and obstacles — size, mass, position, friction, color |
| `target_goal.yaml` | `managing/configs/` | Goal positions and sequence mode |
| `scripts.yaml` | `managing/configs/` | Waypoint sequences for `SCRIPTED_TASK` strategies |
| `adaptation_options.yaml` | `manager/configs/` | Named situations defined as Python expressions evaluated each step |
| `plan_options.yaml` | `manager/configs/` | Maps each situation name → task strategy |

### Defining situations

Situations are pure Python expressions evaluated against live state fields:

```yaml
# manager/configs/adaptation_options.yaml
one_obstacle_situation:  "obstacle_count_in_path == 1"
two_obstacles_situation: "obstacle_count_in_path >= 2"
```

Available fields: `ee_x/y/z`, `cube_x/y/z`, `cube_roll/pitch/yaw`, `cube_vx/vy/vz`, `dist_ee_to_cube`, `dist_cube_to_target`, `fingers_width`, `obstacle_in_path`, `obstacle_count_in_path`, `reward`, `is_success`, `j0`–`j6`, `step`, `episode`.

### Mapping situations to strategies

```yaml
# manager/configs/plan_options.yaml
one_obstacle_situation:  "PICK_AND_PLACE"
two_obstacles_situation: "SCRIPTED_TASK.left_right"
```

---

## Execution Modes

The simulator supports two execution modes. **The entry point determines the mode** — no flags or extra setup required.

### Normal mode

Reads configuration from `managing/configs/`. Used for interactive development and manual testing.

AQUI EXECUTA COMO A GENTE JA CONHECE PEGANGO AS CONFIGURACOES PADROES JA ESTABELECIDAS NA PASTA CONFIG
```bash
cd managing
python main.py
```

### Experiment mode

Reads configuration from a folder inside `experiments/results/`. Used for running automated batches with different parameters. Each experiment gets its own isolated process — PyBullet is fully restarted between runs, guaranteeing no state contamination.

AQUI EXECUTA AS CONFIG DENTRO DA experiments/ AQUI É IMPORTANTE PQ NOS PERMITE EXECUTAR VARIAS VEZES A SIMULACAO COM DIVERSAS CONFIGURACOES SEM SEGUIDA (BATCH)

```bash
cd experiments
python runner.py
```

The runner iterates over the experiments defined in `experiments/batch.yaml`, launches `managing/main.py` as a subprocess for each one, and saves the trace alongside the exact config used.

```
experiments/
├── runner.py
├── batch.yaml
└── results/
    ├── slip-lateral-0.124/
    │   ├── simulation.yaml      ← exact config used
    │   ├── environment.yaml
    │   └── trace.log
    └── slip-vertical-0.10/
        ├── simulation.yaml
        ├── environment.yaml
        └── trace.log
```

**How it works:** the runner sets the environment variable `MANAGING_CONFIG_DIR` pointing to the experiment's folder before launching the subprocess. `config_loader.py` reads this variable — if present, loads from that path; if absent, loads from the default `managing/configs/`.

```
MANAGING_CONFIG_DIR not set  →  normal mode   →  reads from managing/configs/
MANAGING_CONFIG_DIR set      →  experiment mode →  reads from the given path
```

### batch.yaml — defining experiments

Only specify what differs from the defaults. The runner deep-merges with the original configs.

```yaml
experiments:
  - name: "slip-lateral-0.124"
    simulation:
      render_mode: "direct"   # headless — no GUI
      step_delay: 0
    environment:
      objects:
        - name: "object_1"
          lateral_friction: 0.124

  - name: "slip-vertical-0.10"
    simulation:
      render_mode: "direct"
      step_delay: 0
    environment:
      objects:
        - name: "object_1"
          lateral_friction: 0.10
```

---

## Task Strategies

| Strategy | Description |
|---|---|
| `PICK_AND_PLACE` | 6-phase autonomous pick-and-place: approach, grasp, lift, move, place, release |
| `PUSH` | Approaches the object from behind and pushes it toward the target |
| `REACH` | Moves the end-effector to a target position without manipulating any object |
| `HOLD` | Keeps the end-effector stationary at its current position |
| `SCRIPTED_TASK.<name>` | Executes a waypoint sequence from `scripts.yaml` (e.g. `SCRIPTED_TASK.left_right`) |
| `API_TASK` | Receives waypoints via `PUT /waypoints` at runtime for externally driven control |
| `MANUAL` | Interactive keyboard control for manual exploration |

---

## REST API

The simulator exposes a FastAPI server on `http://localhost:8000`.

| Endpoint | Method | Description |
|---|---|---|
| `/perception` | GET | Full state snapshot: EE position/velocity, cube pose, distances, reward, joints, rotation |
| `/environment/obstacles` | GET | Obstacles with config and current position |
| `/environment/objects` | GET | Manipulable objects with config and current position |
| `/task` | PUT | Switch task strategy |
| `/waypoints` | PUT | Push a waypoint list for `API_TASK` |
| `/environment` | PUT | Mutate the scene: `move_obstacle`, `add_obstacle`, `remove_obstacle`, `move_object`, `move_robot_base` |
| `/goal` | PUT | Reposition a target or change goal mode at runtime |

### Examples

```bash
# Switch to pick-and-place
curl -X PUT http://localhost:8000/task \
  -H "Content-Type: application/json" \
  -d '{"strategy": "PICK_AND_PLACE"}'

# Move an obstacle
curl -X PUT http://localhost:8000/environment \
  -H "Content-Type: application/json" \
  -d '{"action": "move_obstacle", "name": "obstacle_1", "position": [0.12, 0.0, 0.04]}'

# Read live perception
curl http://localhost:8000/perception
```

---

## Friction Tuning

PyBullet computes effective friction as the **product** of the two bodies in contact. To simulate grip slip while keeping the object stable on the table, set a high table friction (`lateral_friction: 3.0`) and tune the object's `lateral_friction` in the environment YAML.

| `lateral_friction` (object) | Behavior |
|---|---|
| ≥ 0.126 | Object stays firmly in gripper — no slip |
| 0.124 – 0.125 | Partial lateral slip (~16 mm) — object carried but not rigidly held |
| ≤ 0.120 | Vertical slip within gripper — cube descends relative to EE during lift |
| ≤ 0.10 | Object falls from gripper |

> **Warning:** Config changes require a simulator restart. All YAML is loaded once at startup via `config_loader.py`.

---

## API Tests

Jupyter notebooks in `api_test/` demonstrate each API endpoint interactively. Run with the simulator already started.

| Notebook | Covers |
|---|---|
| `01_perception.ipynb` | Reading live perception state |
| `02_task.ipynb` | Switching task strategies |
| `03_waypoints.ipynb` | Sending custom waypoints |
| `04_environment.ipynb` | Mutating the scene at runtime |
| `05_goal.ipynb` | Repositioning targets |

---

## Project Structure

```
self-adaptive-arm-simulator/
├── managing/                  # simulator process
│   ├── main.py                # entry point
│   ├── api.py                 # FastAPI server (:8000)
│   ├── environment_manager.py
│   ├── config_loader.py
│   ├── tasks/                 # PUSH, PICK_AND_PLACE, REACH, HOLD, MANUAL …
│   ├── sensors/               # perception pipeline
│   ├── configs/
│   │   ├── simulation.yaml
│   │   ├── scripts.yaml
│   │   ├── target_goal.yaml
│   │   └── environments/      # environment*.yaml
│   └── traces/                # step-level log files
│
├── manager/                   # MAPE-K manager process
│   ├── main.py
│   ├── monitor.py
│   ├── analyze.py
│   ├── plan.py
│   ├── execute.py
│   ├── knowledge.py
│   └── configs/
│       ├── adaptation_options.yaml
│       └── plan_options.yaml
│
├── experiments/               # batch experiment runner
│   ├── runner.py              # orchestrator
│   ├── batch.yaml             # list of experiments to run
│   └── results/               # one folder per experiment (config + trace)
│
├── api_test/                  # Jupyter notebooks for API testing
├── requirements.txt
└── run.sh                     # launches both processes (Windows/mintty)
```

---

## Dependencies

| Package | Version | Role |
|---|---|---|
| pybullet | 3.2.7 | Physics engine |
| panda-gym | 3.0.7 | Franka Panda robot model and environment |
| gymnasium | 1.3.0 | RL environment interface |
| fastapi + uvicorn | — | REST API server in the simulator |
| numpy | 2.4.6 | Numerical computation |
| PyYAML | 6.0.3 | YAML config loading |
| scipy | 1.17.1 | Scientific utilities |
