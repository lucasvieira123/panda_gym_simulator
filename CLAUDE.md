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

Tests for the measurement infrastructure, from `3-dejavu/`:

```bash
python -m unittest discover -s tests
```

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
                              SimilarityBasedAdapter            (filters by When, ranks by similarity)
                                         ↓
                              AdaptationEvaluator               (explicit result of the adaptation)
```

**Trigger rules:**
- `AntecipatedScenarioMonitor` — runs on every tick
- `UnanticipatedScenarioIdentifier` + `UnanticipatedScenarioDiagnoser` — run once per episode, on the first UNSAT tick
- `SimilarityBasedAdapter` — runs once per episode, after diagnosis; recommends the Top-1 candidate
- `AdaptationEvaluator` — runs on every tick once an adaptation starts
- `AsmEvolver` — runs at the end of the episode, only if the adaptation succeeded and the global goal was achieved

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
| `src/similarity/when_filter.py` | Applicability filter: only candidates with a matching When reach the similarity calculation |
| `src/adaptation_evaluator.py` | Ends each adaptation in `success`, `failure`, `timeout` or `execution_error` |
| `src/asm_evolver.py` | Adds a validated adaptation to the ASM |
| `src/run_events.py` | Writes the run's pipeline events (`events_*.jsonl`) |
| `src/retry_policy.py` | After a failed attempt, chooses the next ranked candidate or the fail-safe (at most 2 attempts) |
| `src/constants.py` | `PROJECT_ROOT` resolution; `DEJAVU_CONF_PATH` |
| `src/utils.py` | `load_config()` helper |

## Configuration (`configs/`)

| File | Purpose |
|------|---------|
| `configs/dejavu_conf.yaml` | Central config — all paths resolved from here via `PROJECT_ROOT` |
| `configs/arm/scenario_state_machine.yaml` | Sismic state machine for the ARM pick-and-place task |
| `configs/arm/scenario_catalogue.json` | Candidates C1–C5 (lift) and C6–C8 (transport), with `monitored_parameters` (uses `min_value`/`max_value`). `apply_vacuum_assist()`, `adjust_grip_force()` and `increase_grip_pressure()` have a physical implementation |
| `configs/weights_config.yaml` | Similarity weights: Tversky α/β, per-clause weights (`given`, `when`, `then`) |

Anticipated scenarios (ASM) live in `1-manager/configs/arm/asm.json` — DejaVu reads them via `anticipated_scenarios_path` in `dejavu_conf.yaml`.

All paths in `dejavu_conf.yaml` are relative to `PROJECT_ROOT` (resolved in `src/constants.py`).

## Output (`output/arm/`)

| Path | Content |
|------|---------|
| `output/arm/traces/` | Per-run trace logs with full tick + pipeline detail, and `events_*.jsonl` |
| `output/arm/antecipated_scenario_dataset/` | CSV files written by the monitor; one file per scenario execution; used by the diagnoser for training |
| `output/arm/similarities/` | Ranked similarity results per run |

## Diagnoser — design notes

- **Execution-level**: 1 row per execution (first tick snapshot), label = `any(sat==False)` in that execution
- **Static features only**: columns whose `std==0` across each whole execution, not only within the scenario's rows — world properties set before the episode starts (e.g., `lateral_friction`)
- **Dynamic features excluded**: vary tick-to-tick; represent effects, not causes
- **Label name pattern**: `f"{scenario_name}_unanticipated"` — generic, works for any scenario

## Similarity — design notes

- `monitored_parameters` come from `scenario_catalogue.json` (not a separate file)
- Format must use `min_value`/`max_value` keys (not `min`/`max`) — the algorithm reads these directly
- Candidates are filtered by When before the calculation (`when_filter.py`): lift compares with C1–C5, transport with C6–C8, and other scenarios have no candidates
- `when` weight = 1.0 (same as `given` and `then`) — after the filter, it contributes a fixed 1/3 to every score
- Minimum possible score = 0.33 (when `given_sim` and `then_sim` are both 0)
- Tversky α=0.9, β=0.1: penalizes missing parameters in the candidate heavily; tolerates extra parameters lightly

## Adaptation results — design notes

Three independent levels, reported in `outcome.json`:

- **Sequence completed** (`is_success`): the action sequence ended, even without the object
- **Adaptation result**: based on the diagnosed Then, which needs only one tick to succeed
- **Global goal**: object within 5 cm of the target and gripper open; this is the result that counts

## Retry and fail-safe — design notes

- DejaVu decides and the Manager executes, keeping the priority of the internal ASM
- The candidates' recovery tasks are in `2-managing/src/tasks/object_delivery/grip_recovery_tasks.py`: same grasp routine, different simulated finger friction
- The fail-safe holds the arm and gripper still (it does not open the gripper), records the reason, notifies the console and ends the run; `SAFE_ABORT` is a different, anticipated scenario

## Not Implemented

- **Physical actions of C3, C4, C5 and C8**: they only take part in the ranking

Decisions for the RQ1.1 evaluation are in `5-experiments/RQ1.1/decisions.md`.
