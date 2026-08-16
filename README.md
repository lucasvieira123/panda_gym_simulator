# Self-Adaptive Arm Simulator

> Research prototype of a self-adaptive system built around a Franka Panda robotic arm simulation. Implements a full MAPE-K feedback loop coupled with the **DejaVu** reference architecture for detecting, identifying, diagnosing, and adapting to unanticipated scenarios.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![PyBullet](https://img.shields.io/badge/PyBullet-3.2.7-green)
![panda--gym](https://img.shields.io/badge/panda--gym-3.0.7-green)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-red)
![Sismic](https://img.shields.io/badge/StateMachine-Sismic-purple)

---

## Overview

The system simulates a Franka Panda robot performing a pick-and-place task. Five processes cooperate at runtime: a physics simulator, a MAPE-K manager, a DejaVu monitor, and two Streamlit consoles.

```
┌──────────────────────────────────────────────────────────────────────┐
│                          0-console  (Streamlit :8501)                │
│              ASM Editor — design scenarios, start the system         │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │ launches
          ┌────────────────────────┼────────────────────────┐
          ▼                        ▼                        │
┌──────────────────┐    WebSocket  ┌──────────────────┐    │
│   2-managing     │◄─────────────►│   1-manager      │    │
│  PyBullet +      │   :8000/:8001 │  MAPE-K loop     │    │
│  panda-gym       │               │  Monitor→Analyze │    │
│  FastAPI :8000   │               │  →Plan→Execute   │    │
└──────────────────┘               └────────┬─────────┘    │
                                            │ WebSocket     │
                                            ▼              │
                                   ┌──────────────────┐    │
                                   │   3-dejavu       │◄───┘
                                   │  State Machine   │
                                   │  Monitor +       │
                                   │  Pipeline        │
                                   │  Flask WS :8002  │
                                   └────────┬─────────┘
                                            │ WebSocket
                                            ▼
                              ┌──────────────────────────┐
                              │  4-dejavu-console        │
                              │  Streamlit :8502         │
                              │  Live state + catalogue  │
                              └──────────────────────────┘
```

---

## Components

| # | Folder | Role | Port |
|---|--------|------|------|
| 0 | `0-console/` | Streamlit app to design the ASM model and launch the system | 8501 |
| 1 | `1-manager/` | MAPE-K manager — reads perception, evaluates ASM contracts, plans and sends adaptations | 8001 |
| 2 | `2-managing/` | Physics simulator — PyBullet + panda-gym, exposes perception via FastAPI | 8000 |
| 3 | `3-dejavu/` | DejaVu monitor — Sismic state machine, unanticipated scenario pipeline | 8002 |
| 4 | `4-dejavu-console/` | Streamlit console for DejaVu live state, similarity results and catalogue | 8502 |
| 5 | `5-experiments/` | Batch experiment builder and runner | — |

---

## Architecture

### MAPE-K Loop (1-manager)

Each perception tick flows through four stages. Scenarios and their contracts are defined in `1-manager/configs/arm/asm.json` — no code changes needed to add new adaptive behaviors.

| Stage | Responsibility |
|-------|---------------|
| **Monitor** | Reads raw perception from Managing and populates `SystemState` |
| **Analyze** | Evaluates ASM scenario guards against current state |
| **Plan** | Maps the current ASM scenario to a task strategy |
| **Execute** | Sends `adapt` / `continue` / `transition` commands to Managing |

### DejaVu Pipeline (3-dejavu)

Runs on every tick from the Manager. When the state machine detects a contract violation, the full pipeline fires **once per episode**:

```
AntecipatedScenarioMonitor   (every tick — Sismic state machine)
          │
          │ first UNSAT in episode
          ▼
UnanticipatedScenarioIdentifier   (negates violated then-clauses → new given)
          ▼
UnanticipatedScenarioDiagnoser    (decision tree on historical CSVs → causal conditions)
          ▼
SimilarityBasedAdapter            (ranks catalogue candidates by DejaVu similarity)  ← pending wiring
```

### Blocking checkpoints

Every tick is synchronous end-to-end:
1. **Managing** publishes perception and blocks waiting for the Manager's command.
2. **Manager** sends the perception to DejaVu and blocks waiting for its response before answering Managing.
3. **DejaVu** processes the tick (and runs the pipeline on UNSAT) then replies synchronously.

---

## Installation

**Prerequisites:** Python 3.11+, Windows (the launcher uses `cmd`; processes can also be started manually on any OS).

```bash
git clone <repo-url>
cd self-adaptive-arm-simulator

python -m venv .venv
.venv\Scripts\activate

# Core simulator
pip install pybullet panda-gym gymnasium fastapi uvicorn numpy scipy pyyaml

# Manager + DejaVu
pip install pandas scikit-learn sympy sismic wrapt pyparsing flask websockets

# Consoles
pip install streamlit streamlit-agraph graphviz
```

---

## Running

### Option A — via ASM Console (recommended)

```bash
# Terminal 1: ASM Editor console
cd 0-console
streamlit run app.py --server.port 8501
```

Open `http://localhost:8501`, load the ARM sample model, then click **▶ Start System**. This launches Managing and Manager in separate terminal windows.

```bash
# Terminal 2: DejaVu
cd 3-dejavu
python src/dejavu.py

# Terminal 3: DejaVu Console (optional)
cd 4-dejavu-console
streamlit run app.py --server.port 8502
```

### Option B — manual

```bash
# Terminal 1 — physics simulator
cd 2-managing
python src/main.py

# Terminal 2 — MAPE-K manager
cd 1-manager
python src/main.py

# Terminal 3 — DejaVu
cd 3-dejavu
python src/dejavu.py
```

> **Start order:** Managing → Manager → DejaVu. Managing must be up before Manager connects.

---

## Configuration

### Simulator (`2-managing/configs/`)

| File | Controls |
|------|---------|
| `simulation.yaml` | Episodes, seed, step delay, render mode, task parameters |
| `environment.yaml` | Robot, table, objects, obstacles — size, mass, friction, color |
| `target_goal.yaml` | Goal positions and sequence mode |
| `scripts.yaml` | Waypoint sequences for `SCRIPTED_TASK` strategies |

### Manager (`1-manager/configs/arm/`)

| File | Controls |
|------|---------|
| `asm.json` | Anticipated Scenario Model — Given/When/Do/Then contracts for each task phase |

### DejaVu (`3-dejavu/configs/`)

| File | Controls |
|------|---------|
| `dejavu_conf.yaml` | Central config — all paths resolved from here |
| `arm/scenario_state_machine.yaml` | Sismic state machine for the pick-and-place task |
| `arm/scenario_catalogue.json` | Candidate lift scenarios for similarity ranking; includes `monitored_parameters` |
| `weights_config.yaml` | Similarity weights: Tversky α/β, per-clause weights (given/when/then) |

### Task strategies

| Strategy | Description |
|----------|-------------|
| `PICK_AND_PLACE` | 6-phase autonomous pick-and-place |
| `OBJECT_DELIVERY` | Full delivery sequence (approach → grasp → lift → transport → place) |
| `PUSH` | Pushes the object toward the target |
| `REACH` | Moves end-effector to a position |
| `HOLD` | Keeps end-effector stationary |
| `RETRY_GRASP` | Reopens gripper and retries grasp |
| `SAFE_ABORT` | Aborts the grasp and opens gripper safely |
| `SCRIPTED_TASK.<name>` | Executes a named waypoint sequence from `scripts.yaml` |
| `API_TASK` | Receives waypoints via `PUT /waypoints` at runtime |
| `MANUAL` | Interactive keyboard control |

---

## Batch Experiments (`5-experiments/`)

```bash
# 1. Define and build simulation configs
cd 5-experiments
python build_simulations.py
# Creates experiments/simulations/ with one folder per parameter set

# 2. Run all simulations sequentially
python execute_simulations.py
```

`build_simulations.py` generates self-contained config folders (one per experiment). `execute_simulations.py` launches `2-managing` once per folder, blocking until completion.

### Friction tuning reference

PyBullet computes effective friction as the **product** of the two contacting bodies. Keep table friction high (`lateral_friction: 3.0`) and tune the object:

| Object `lateral_friction` | Behavior |
|--------------------------|---------|
| ≥ 0.126 | Firm grip — no slip |
| 0.124 – 0.125 | Partial lateral slip (~16 mm) |
| ≤ 0.120 | Vertical slip during lift |
| ≤ 0.10 | Object falls from gripper |

---

## Managing REST API

The simulator exposes a FastAPI server on `http://localhost:8000`.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/perception` | GET | Full state snapshot: EE pose/velocity, cube pose, distances, joints |
| `/environment/obstacles` | GET | Obstacles with config and current position |
| `/environment/objects` | GET | Manipulable objects with config and current position |
| `/task` | PUT | Switch task strategy |
| `/waypoints` | PUT | Push a waypoint list for `API_TASK` |
| `/environment` | PUT | Mutate scene: `move_obstacle`, `add_obstacle`, `remove_obstacle`, `move_object` |
| `/goal` | PUT | Reposition a target or change goal mode at runtime |

---

## Project Structure

```
self-adaptive-arm-simulator/
│
├── 0-console/                      # ASM Editor + System Launcher (Streamlit)
│   ├── app.py                      # Main Streamlit app
│   └── system_launcher.py          # Launches managing + manager as subprocesses
│
├── 1-manager/                      # MAPE-K Manager
│   ├── src/
│   │   ├── main.py                 # Entry point
│   │   ├── monitor_arm.py          # Monitor stage
│   │   ├── analyze.py              # Analyze stage (ASM evaluation)
│   │   ├── plan.py                 # Plan stage
│   │   ├── execute.py              # Execute stage
│   │   ├── knowledge.py            # SystemState dataclass
│   │   └── api.py                  # WebSocket API (:8001) + DejaVu bridge
│   └── configs/arm/
│       └── asm.json                # Anticipated Scenario Model
│
├── 2-managing/                     # Physics Simulator
│   ├── src/
│   │   ├── main.py                 # Entry point
│   │   ├── api.py                  # FastAPI server (:8000)
│   │   ├── environment_manager.py  # Scene setup (robot, objects, obstacles)
│   │   ├── config_loader.py        # YAML config loader (supports --config-dir)
│   │   └── tasks/                  # Task implementations (PICK_AND_PLACE, PUSH, …)
│   └── configs/
│       ├── simulation.yaml
│       ├── environment.yaml
│       ├── target_goal.yaml
│       └── scripts.yaml
│
├── 3-dejavu/                       # DejaVu Monitor
│   ├── src/
│   │   ├── dejavu.py               # Entry point + main loop
│   │   ├── api.py                  # Flask WebSocket API (:8002)
│   │   ├── antecipated_scenario_monitor.py       # Sismic state machine runner
│   │   ├── antecipated_scenario_dataset_recorder.py  # CSV dataset writer
│   │   ├── unanticipated_scenario_identifier.py  # Negates violated then-clauses
│   │   ├── unanticipated_scenario_diagnoser.py   # Decision tree diagnosis
│   │   ├── similarity_based_adapter.py           # Catalogue similarity ranking
│   │   ├── trace_printer.py        # Structured trace formatting
│   │   ├── scenario/               # Scenario data classes
│   │   ├── expression/             # Conditional expression model
│   │   └── similarity/             # DejaVu similarity metric (Jaccard + Tversky)
│   ├── configs/
│   │   ├── dejavu_conf.yaml
│   │   ├── weights_config.yaml
│   │   └── arm/
│   │       ├── scenario_state_machine.yaml
│   │       └── scenario_catalogue.json
│   └── output/arm/
│       ├── traces/                 # Per-run trace logs
│       └── antecipated_scenario_dataset/   # CSV files used by the diagnoser
│
├── 4-dejavu-console/               # DejaVu Console (Streamlit)
│   ├── app.py                      # Main Streamlit app
│   ├── views/                      # catalogue, similarities, state_machine, checked
│   └── sidebar/                    # Catalogue editor and SM setup panels
│
└── 5-experiments/                  # Batch Experiment Runner
    ├── build_simulations.py        # Defines and creates experiment config folders
    └── execute_simulations.py      # Runs managing once per experiment folder
```

---

## Not Implemented

| Component | Status |
|-----------|--------|
| `SimilarityBasedAdapter` wiring in `dejavu.py` | Implemented but not yet called in the main loop |
| Adaptation Evaluation | Not implemented — requires simulating adaptation effects |
| Evolutionary Adaptation Enactor | Not implemented — executes the chosen adaptation in the running system |

Once a viable adaptation is confirmed, the adapted scenario should be merged back into the Anticipated Scenario Model, becoming a newly anticipated scenario for future monitoring.

---

## DejaVu Similarity — quick reference

The similarity between a diagnosed scenario and a catalogue candidate is computed as a weighted average of three block similarities (Given, When, Then):

```
score = (given_sim × w_given + when_sim × w_when + then_sim × w_then)
        / (w_given + w_when + w_then)
```

Each block similarity uses **parameter Jaccard** (numeric interval overlap per shared variable) minus a **Tversky structural penalty** (α=0.9 penalizes missing parameters; β=0.1 tolerates extra ones). Weights are configured in `3-dejavu/configs/weights_config.yaml`. The `monitored_parameters` schema (with `min_value`/`max_value` keys) lives in `scenario_catalogue.json`.

---

## License

MIT — see [LICENSE](LICENSE) for details.
