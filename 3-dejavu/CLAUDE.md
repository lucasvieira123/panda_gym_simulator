# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**DejaVuArch** is a research prototype implementing a reference architecture for handling unanticipated scenarios in self-evolving systems. The case study is a drone delivery system. The system monitors anticipated behaviors, detects violations, diagnoses root causes, and finds similar known scenarios for adaptation.

## Running the System

```bash
# Run from the repository root
python src/dejavu.py
```

No build step required. There is no `requirements.txt` — install dependencies manually:

```bash
pip install pandas pyyaml scikit-learn sympy sismic wrapt pyparsing numpy
```

There are no automated tests. Reproduce paper experiments by setting `simulation_replay.enabled: true` in `res/dejavu_conf.yaml` and choosing a trace from `res/runtime_replays/`.

## Architecture

The pipeline in `src/dejavu.py` runs sequentially:

```
[Optional] DroneBehaviorSimulator → TelemetryBus → AntecipatedScenarioMonitor
                                                            ↓
                                         UnanticipatedScenariosDetector (reads CSVs)
                                                            ↓
                                         UnanticipatedScenarioIdentifier (negates conditions)
                                                            ↓
                                         UnanticipatedScenarioDiagnoser (decision tree)
                                                            ↓
                                         SimilarityBasedAdapter → similarities.jsonl
```

### Key Components

| File | Role |
|------|------|
| `src/dejavu.py` | Main orchestrator |
| `src/antecipated_scenario_monitor.py` | Executes a Sismic state machine against runtime telemetry ticks; writes `res/checked_scenarios/*.csv` |
| `src/unanticipated_scenarios_detector.py` | Reads checked_scenarios CSVs, extracts rows where `SAT == False` |
| `src/unanticipated_scenario_identifier.py` | Determines which anticipated scenario was violated and negates its violated conditions |
| `src/unanticipated_scenario_diagnoser.py` | Trains a scikit-learn decision tree on historical data to extract `false_rules` |
| `src/similarity_based_adapter.py` | Computes DejaVu similarity between the diagnosed scenario and candidates in `res/shared_scenarios.json` |
| `src/drone_behavior_simulator.py` | Replays a CSV trace tick-by-tick via `TelemetryBus` |
| `src/drone_telemetry.py` | `TelemetryData` dataclass + pub/sub `TelemetryBus` |
| `src/scenario/` | Data classes: `Scenario`, `AntecipatedScenario`, `DiagnosedScenario`, `CandidateScenario` |
| `src/expression/` | BDD clause model: `Expression`, `ConditionalExpression`, `ActionExpression` |
| `src/similarity/dejavu_similarity.py` | Core similarity metric (parameter Jaccard + conditional Tversky) |

### Configuration (`res/`)

| File | Purpose |
|------|---------|
| `dejavu_conf.yaml` | Paths to all other configs; toggle simulation replay |
| `anticipated_scenarios.yaml` | BDD-style Given/When/Do/Then scenario definitions (6 scenarios: LAND, Shut Down, Safe LAND, Takeoff, CheckStatus, Flying) |
| `scenario_state_machine.yaml` | Sismic state machine generated from the anticipated scenarios |
| `weights_config.yaml` | Similarity weights (Tversky α/β, per-clause weights) |
| `monitored_parameters.json` | Schema + value ranges for 16 monitored variables |
| `shared_scenarios.json` | 3 candidate scenarios used for adaptation matching |

All file paths in `dejavu_conf.yaml` are relative to the project root (resolved via `src/constants.py` using `PROJECT_ROOT`).

## Not Implemented

Per the README, two components are not yet implemented:
- **Adaptation Evaluation** — evaluating whether the adapted behavior meets requirements
- **Evolutionary Adaptation Enactor** — executing the adaptation in the running system
