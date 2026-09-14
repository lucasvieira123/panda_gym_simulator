"""
build_simulations.py
====================
Loads an experiment config from experiment_configs/<name>.json and generates
complete input configuration files inside results/<name>/inputs/.

Usage:
    python 5-experiments/build_simulations.py --config friction_sweep

Each experiment in the JSON declares only what changes relative to the base
snapshot. Everything else is inherited unchanged from base/.

Patch operations (inside a file's patch dict):
  "some.dot.key": value         → set a value (supports list indices)
  "$add_scenario":   {...}      → add/replace an entry in "scenarios"
  "$add_transition": {...}      → append a transition to "transitions"
  "$remove_scenario": "key"     → remove a scenario by key
"""

import argparse
import copy
import json
import shutil
from pathlib import Path
from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

EXPERIMENTS_DIR  = Path(__file__).parent
BASE_DIR         = EXPERIMENTS_DIR / "base"
RESULTS_DIR      = EXPERIMENTS_DIR / "results"
CONFIGS_DIR      = EXPERIMENTS_DIR / "experiment_configs"

# ---------------------------------------------------------------------------
# Core utilities
# ---------------------------------------------------------------------------


def _load(path: Path) -> Any:
    if path.suffix == ".json":
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _save(data: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".json":
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    else:
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _set_dotpath(obj: Any, dotpath: str, value: Any) -> None:
    parts = dotpath.split(".")
    for part in parts[:-1]:
        obj = obj[int(part)] if isinstance(obj, list) else obj[part]
    last = parts[-1]
    if isinstance(obj, list):
        obj[int(last)] = value
    else:
        obj[last] = value


def _apply_patch(data: Any, patch: dict) -> Any:
    result = copy.deepcopy(data)
    for key, value in patch.items():
        if key == "$add_scenario":
            result.setdefault("scenarios", {})[value["key"]] = value["data"]
        elif key == "$add_transition":
            result.setdefault("transitions", []).append(value)
        elif key == "$remove_scenario":
            result.get("scenarios", {}).pop(value, None)
        else:
            _set_dotpath(result, key, value)
    return result


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

COMPONENT_FILES = {
    "managing": [
        "environment.yaml",
        "simulation.yaml",
        "target_goal.yaml",
        "scripts.yaml",
    ],
    "manager": [
        "arm/asm.json",
    ],
    "dejavu": [
        "arm/scenario_catalogue.json",
        "arm/scenario_state_machine.yaml",
        "dejavu_conf.yaml",
        "weights_config.yaml",
    ],
}


def build_experiment(experiment: dict) -> None:
    name    = experiment["name"]
    patches = experiment.get("patches", {})

    inputs_dir = RESULTS_DIR / name / "inputs"
    print(f"  Building '{name}' → {inputs_dir}")

    for component, files in COMPONENT_FILES.items():
        for filename in files:
            src  = BASE_DIR / component / filename
            dest = inputs_dir / component / filename

            data = _load(src)

            file_patches = patches.get(component, {}).get(filename, {})
            if file_patches:
                data = _apply_patch(data, file_patches)

            _save(data, dest)

    src_dataset  = BASE_DIR / "dejavu" / "antecipated_scenario_dataset"
    dest_dataset = inputs_dir / "dejavu" / "antecipated_scenario_dataset"
    if src_dataset.exists():
        if dest_dataset.exists():
            shutil.rmtree(dest_dataset)
        shutil.copytree(src_dataset, dest_dataset)

    meta_path = RESULTS_DIR / name / "experiment.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({
            "name":        name,
            "description": experiment.get("description", ""),
            "patches":     patches,
        }, f, indent=2, ensure_ascii=False)

    print(f"    ✓ {sum(len(v) for v in COMPONENT_FILES.values())} config files generated")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build experiment inputs from a config JSON."
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Name of the experiment config (without .json), e.g. friction_sweep",
    )
    args = parser.parse_args()

    config_path = CONFIGS_DIR / f"{args.config}.json"
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        raise SystemExit(1)

    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)

    experiments = config["experiments"]
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Config: {config['name']}")
    print(f"Building {len(experiments)} experiment(s)...\n")
    for exp in experiments:
        build_experiment(exp)

    print(f"\nDone. Results in: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
