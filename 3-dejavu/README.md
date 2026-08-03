# DejaVuArch: A Reference Architecture for Handling Unanticipated Scenarios through Similarity-Based Adaptation

## Table of Contents
- [Overview](#overview)
- [Installation](#installation)
- [Configuration](#configuration)
- [Quick Run](#quick-run)
- [Reproducing the Paper Experiments](#reproducing-the-paper-experiments)
- [Not Implemented](#not-implemented)
- [License](#license)

## Overview
**DejaVuArch** is a reference architecture that enables **self-evolving systems** to **detect**, **identify**, **diagnose**, and **remediate** unanticipated scenarios using **similarity-based adaptation**.

<img width="1389" height="1259" alt="arch" src="https://github.com/user-attachments/assets/e5c60e84-12ae-4208-ab9e-fe4bc222003f" />

In this repository, the pipeline can (optionally) **replay/simulate a target system execution** (e.g., from traces) and then perform scenario monitoring and similarity-based analysis to support unanticipated scenario handling.

## Installation
To run DejaVuArch, you only need a recent version of **Python** and the project dependencies installed from `requirements.txt`.  
We strongly recommend using a **Python virtual environment** to keep dependencies isolated.

### 1) Create and activate a virtual environment

### 2) Install dependencies
```bash
pip install -U pip
pip install -r requirements.txt
```

## Configuration
All configuration files and generated artifacts are located in the `res/` folder.

### Configuration folder (`res/`)
- **`dejavu_conf.yaml`**: main configuration file (paths, flags, thresholds, experiment options).
- **`scenario_state_machine.yaml`**: executable state machine used by the monitor (states, transitions, guards, invariants), generated from the anticipated scenarios.
- **`scenario_state_machine.puml`**: PlantUML version of the state machine (visualization).
- **`anticipated_scenarios.yaml`**: modeled anticipated scenarios (what is expected/monitored).
- **`monitored_parameters.json`**: list of monitored variables/features (i.e., which trace columns are used).
- **`weights_config.yaml`**: similarity configuration (feature weights, factors, thresholds).
- **`shared_scenarios.json`**: shared candidate scenarios used to keep comparisons consistent during the similarity step.
- **`similarities.jsonl`**: similarity results (often precomputed) used by the adaptation strategy.
- **`runtime_replays/`**: traces for replay (execution traces, actions, historical runs) used to simulate a target system execution.
- **`checked_scenarios/`**: outputs produced by the monitoring process (per-execution scenario checks and SAT results).


## Quick Run
After configuring the files in `res/` and deciding whether you will **replay/simulate the target system execution** or **skip directly to the detection, identification, diagnosis, and similarity-based adaptation steps**, you can run DejaVuArch with:

```bash
python dejavu.py
```

## Reproducing the Paper Experiments

The default configuration files included in this repository are already set to match the experimental setup reported in the paper.

The **anticipated scenario model** is specified in `anticipated_scenarios.yaml`:

<img width="1724" height="1189" alt="Anticipated scenario model (anticipated_scenarios.yaml)" src="https://github.com/user-attachments/assets/7ef78c43-b28f-4ae0-8162-1e4a04b7a7de" />

The corresponding **state machine** used to monitor the anticipated scenarios is specified/generated in `scenario_state_machine.yaml`:

<img width="1983" height="1505" alt="Scenario state machine (scenario_state_machine.yaml)" src="https://github.com/user-attachments/assets/b46699db-4dcc-468c-b3bb-eaee7f71795a" />

### Monitored Scenarios

<img width="1366" height="811" alt="Monitored scenarios" src="https://github.com/user-attachments/assets/70131e98-aeb3-4463-9a70-6be12454fdda" />

### Detecting an Unanticipated Situation

<img width="1365" height="273" alt="Detecting an unanticipated situation" src="https://github.com/user-attachments/assets/ee2f15d5-cbc8-4988-b763-fd4bc517a8f3" />

### Identifying an Unanticipated Scenario

<img width="770" height="338" alt="Identifying an unanticipated scenario" src="https://github.com/user-attachments/assets/77009ccd-9def-4738-b2bf-0a13095a811a" />

### Diagnosing an Unanticipated Scenario

Historical data are organized and a **decision tree** is trained to diagnose—based on the monitored parameters—the conditions that explain the unanticipated situation:

<img width="1371" height="561" alt="Decision-tree-based diagnosis from monitored parameters" src="https://github.com/user-attachments/assets/12115637-9e58-4d56-b0fe-23b447f57f40" />

Diagnosed unanticipated scenario:

<img width="753" height="342" alt="Diagnosed unanticipated scenario" src="https://github.com/user-attachments/assets/0880b547-0afc-4833-ba6f-03d3e7cc2c78" />

### Similar Candidate Scenarios

We designed a metric that computes scenario similarity using a **local-to-global progression**, producing a score between **0.0 and 1.0**.  
The process starts with **parameter similarity**, which measures the numeric overlap between conditions of specific variables using the **Jaccard coefficient**. Next, it computes **conditional similarity** for each scenario clause (Given, When, and Then), aggregating parameter-level averages and applying a **structural penalty** via the **Tversky index** to account for missing or extra parameters. Finally, the overall **scenario similarity** is consolidated as a weighted average of these conditional similarities, enabling selection of the highest-scoring candidate to recommend the most suitable adaptation strategy for the system.

<img width="1371" height="850" alt="Similar candidate scenarios ranking" src="https://github.com/user-attachments/assets/23157b68-3d09-4607-b9d3-c33cd2d7d16b" />

### Adapted Scenario

<img width="755" height="318" alt="Adapted scenario" src="https://github.com/user-attachments/assets/9fa91a7a-d9e3-4f32-968a-ac39bf84ab55" />



Therefore, to reproduce the experiments, simply run:

```bash
python dejavu.py
```

After the execution finishes, check the generated results in:
- `res/similarities.jsonl`
## Not Implemented
The **Adaptation Evaluation** and **Evolutionary Adaptation Enactor** components have not been implemented yet. This is because it is first necessary to build a simulation that represents the effects of an adaptation on the _target application_. Then, once a viable adaptation is achieved, the adapted scenario should be merged into the Anticipated Scenario Model, becoming a newly discovered scenario to handle the previously unanticipated situation.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE.txt) file for details.
