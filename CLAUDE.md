# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**DejaVuArch** is a research prototype implementing a reference architecture for handling unanticipated scenarios in self-evolving systems. The case study is a **robotic arm simulator** (pick-and-place task). The system monitors anticipated behaviors tick-by-tick, detects contract violations, diagnoses root causes via a decision tree, and finds similar known scenarios for adaptation.

DejaVu runs as a **Flask API server** that receives perception ticks from the Manager (`1-manager/`) via `send_to_dejavu()`. It is not run standalone.

## Running the System

```bash
# Run from the 3-dejavu/ directory
python src/dejavu.py
```

No build step required. Install dependencies manually:

```bash
pip install pandas pyyaml scikit-learn sympy sismic wrapt pyparsing numpy flask
```

There are no automated tests.

## Architecture

The pipeline in `src/dejavu.py` runs per episode:

```
Manager (every tick) → api.py → AntecipatedScenarioMonitor
                                         │
                              (on first UNSAT in episode)
                                         ↓
                              UnanticipatedScenarioIdentifier   (negates violated then-clauses)
                                         ↓
                              UnanticipatedScenarioDiagnoser    (decision tree on historical CSVs)
                                         ↓
                              SimilarityBasedAdapter            (ranks catalogue candidates)
```

**Trigger rules:**
- `AntecipatedScenarioMonitor` — runs on every tick
- `UnanticipatedScenarioIdentifier` + `UnanticipatedScenarioDiagnoser` — run once per episode, on the first UNSAT tick
- `SimilarityBasedAdapter` — runs once per episode, after diagnosis (pending wiring in `dejavu.py`)

## Key Components

| File | Role |
|------|------|
| `src/dejavu.py` | Main orchestrator and Flask API server |
| `src/api.py` | API endpoints — receives ticks from Manager, returns DejaVu state |
| `src/antecipated_scenario_monitor.py` | Runs Sismic state machine against each tick; writes dataset CSVs to `output/arm/antecipated_scenario_dataset/` |
| `src/unanticipated_scenario_identifier.py` | Finds which anticipated scenario was violated; negates its violated `then` clauses to build the new `given` |
| `src/unanticipated_scenario_diagnoser.py` | Trains a decision tree (execution-level, static features only) on historical CSV data; extracts `false_rules` as causal conditions |
| `src/similarity_based_adapter.py` | Loads `scenario_catalogue.json`; ranks candidates by DejaVu similarity against the diagnosed scenario |
| `src/trace_printer.py` | Formats trace logs (tick, pipeline stages: DETECT → IDENTIFY → DIAGNOSE → SIMILARITIES) |
| `src/scenario/` | Data classes: `Scenario`, `AntecipatedScenario`, `DiagnosedScenario`, `CandidateScenario` |
| `src/expression/` | BDD clause model: `Expression`, `ConditionalExpression`, `ActionExpression` |
| `src/similarity/dejavu_similarity.py` | Core similarity metric: parameter Jaccard (weighted) + conditional Tversky penalty |
| `src/constants.py` | `PROJECT_ROOT` resolution; `DEJAVU_CONF_PATH` |
| `src/utils.py` | `load_config()` helper |

## Configuration (`configs/`)

| File | Purpose |
|------|---------|
| `configs/dejavu_conf.yaml` | Central config — all paths resolved from here via `PROJECT_ROOT` |
| `configs/arm/scenario_state_machine.yaml` | Sismic state machine for the ARM pick-and-place task |
| `configs/arm/scenario_catalogue.json` | Lift scenarios catalogue with `monitored_parameters` (uses `min_value`/`max_value`) and 3 candidates (HIGH/MEDIUM/LOW similarity) |
| `configs/weights_config.yaml` | Similarity weights: Tversky α/β, per-clause weights (`given`, `when`, `then`) |

Anticipated scenarios (ASM) live in `1-manager/configs/arm/asm.json` — DejaVu reads them via `anticipated_scenarios_path` in `dejavu_conf.yaml`.

All paths in `dejavu_conf.yaml` are relative to `PROJECT_ROOT` (resolved in `src/constants.py`).

## Output (`output/arm/`)

| Path | Content |
|------|---------|
| `output/arm/traces/` | Per-run trace logs with full tick + pipeline detail |
| `output/arm/antecipated_scenario_dataset/` | CSV files written by the monitor; one file per scenario execution; used by the diagnoser for training |
| `output/arm/similarities.jsonl` | Ranked similarity results (written by adapter) |

## Diagnoser — design notes

- **Execution-level**: 1 row per execution (first tick snapshot), label = `any(sat==False)` in that execution
- **Static features only**: columns whose `std==0` within each execution — world properties set before the episode starts (e.g., `lateral_friction`)
- **Dynamic features excluded**: vary tick-to-tick; represent effects, not causes
- **Label name pattern**: `f"{scenario_name}_unanticipated"` — generic, works for any scenario

## Similarity — design notes

- `monitored_parameters` come from `scenario_catalogue.json` (not a separate file)
- Format must use `min_value`/`max_value` keys (not `min`/`max`) — the algorithm reads these directly
- `when` weight = 1.0 (same as `given` and `then`) — with all catalogue candidates sharing the same `when`, it contributes a fixed 1/3 to every score
- Minimum possible score = 0.33 (when `given_sim` and `then_sim` are both 0)
- Tversky α=0.9, β=0.1: penalizes missing parameters in the candidate heavily; tolerates extra parameters lightly

## Not Implemented

- **SimilarityBasedAdapter wiring** — adapter is implemented but not yet called in `dejavu.py` main loop
- **Adaptation Evaluation** — evaluating whether the adapted behavior meets requirements
- **Evolutionary Adaptation Enactor** — executing the chosen adaptation in the running system
