"""
execute_simulations.py
======================
For each built experiment (results/<name>/inputs/ must exist), this script:

  1. Overwrites the real component configs with the experiment's input files.
  2. Launches DejaVu (Flask), Manager, and Managing as subprocesses.
  3. Waits for Managing to finish (it terminates after all episodes).
  4. Collects all outputs into results/<name>/outputs/.
  5. Restores every component config from base/.

Usage:
    python 5-experiments/execute_simulations.py [experiment_name ...]

    # Run all built experiments:
    python 5-experiments/execute_simulations.py

    # Run specific experiments:
    python 5-experiments/execute_simulations.py A_baseline C_low_friction_with_dejavu
"""

import argparse
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

EXPERIMENTS_DIR = Path(__file__).parent
BASE_DIR        = EXPERIMENTS_DIR / "base"
RESULTS_DIR     = EXPERIMENTS_DIR / "results"
ROOT            = EXPERIMENTS_DIR.parent

MANAGING_DIR = ROOT / "2-managing"
MANAGER_DIR  = ROOT / "1-manager"
DEJAVU_DIR   = ROOT / "3-dejavu"

# ---------------------------------------------------------------------------
# Real component config destinations (paths to overwrite during each run)
# ---------------------------------------------------------------------------

COMPONENT_DEST = {
    "managing": {
        "environment.yaml":       MANAGING_DIR / "configs" / "environments" / "environment.yaml",
        "simulation.yaml":        MANAGING_DIR / "configs" / "simulation.yaml",
        "target_goal.yaml":       MANAGING_DIR / "configs" / "target_goal.yaml",
        "scripts.yaml":           MANAGING_DIR / "configs" / "scripts.yaml",
    },
    "manager": {
        "arm/asm.json":           MANAGER_DIR  / "configs" / "arm" / "asm.json",
    },
    "dejavu": {
        "arm/scenario_catalogue.json":       DEJAVU_DIR / "configs" / "arm" / "scenario_catalogue.json",
        "arm/scenario_state_machine.yaml":   DEJAVU_DIR / "configs" / "arm" / "scenario_state_machine.yaml",
        "dejavu_conf.yaml":                  DEJAVU_DIR / "configs" / "dejavu_conf.yaml",
        "weights_config.yaml":               DEJAVU_DIR / "configs" / "weights_config.yaml",
    },
}

# antecipated_scenario_dataset is not overwritten — DejaVu writes into it during the run.
# We back it up from base before each run and collect it after.
DATASET_REAL = DEJAVU_DIR / "output" / "arm" / "antecipated_scenario_dataset"
DATASET_BASE = BASE_DIR / "dejavu" / "antecipated_scenario_dataset"

# Output source folders (where components write their runtime outputs)
DEJAVU_TRACES_SRC      = DEJAVU_DIR  / "output" / "arm" / "traces"
DEJAVU_SIMILAR_SRC     = DEJAVU_DIR  / "output" / "arm" / "similarities"
MANAGER_TRACES_SRC     = MANAGER_DIR / "traces"
MANAGING_TRACES_SRC    = MANAGING_DIR / "traces"

# ---------------------------------------------------------------------------
# Python interpreter / subprocess environment
# ---------------------------------------------------------------------------

def _python() -> str:
    """Return the active Python interpreter path."""
    return sys.executable


def _env() -> dict:
    """Subprocess environment with UTF-8 I/O to avoid cp1252 encoding errors."""
    return {**os.environ, "PYTHONIOENCODING": "utf-8"}


# ---------------------------------------------------------------------------
# Config apply / restore
# ---------------------------------------------------------------------------

def _apply_inputs(inputs_dir: Path) -> None:
    """Overwrite real component configs with the experiment's generated inputs."""
    for component, files in COMPONENT_DEST.items():
        for rel_path, dest in files.items():
            src = inputs_dir / component / rel_path
            if src.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)

    # Restore antecipated_scenario_dataset from base before each run
    # so the diagnoser has clean training data (or the experiment's own snapshot)
    exp_dataset = inputs_dir / "dejavu" / "antecipated_scenario_dataset"
    src_dataset = exp_dataset if exp_dataset.exists() else DATASET_BASE
    if DATASET_REAL.exists():
        shutil.rmtree(DATASET_REAL)
    shutil.copytree(src_dataset, DATASET_REAL)


def _restore_base() -> None:
    """Restore all real component configs and dataset from the base snapshot."""
    for component, files in COMPONENT_DEST.items():
        for rel_path, dest in files.items():
            src = BASE_DIR / component / rel_path
            if src.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)

    if DATASET_REAL.exists():
        shutil.rmtree(DATASET_REAL)
    shutil.copytree(DATASET_BASE, DATASET_REAL)

    print("  [restore] Base configs and dataset restored.")


def _clear_output_sources() -> None:
    """Delete and recreate runtime output directories before each run."""
    dirs = [
        MANAGER_TRACES_SRC,
        MANAGING_TRACES_SRC,
        DEJAVU_TRACES_SRC,
        DEJAVU_SIMILAR_SRC,
    ]
    for d in dirs:
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)
    print("  [clean]    Output source directories cleared.")


# ---------------------------------------------------------------------------
# Output collection
# ---------------------------------------------------------------------------

def _collect_outputs(outputs_dir: Path) -> None:
    """Copy runtime outputs into the experiment's outputs/ folder."""

    def _copy_dir(src: Path, dest: Path) -> None:
        if not src.exists():
            return
        dest.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            target = dest / item.name
            if item.is_file():
                shutil.copy2(item, target)
            elif item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)

    _copy_dir(MANAGER_TRACES_SRC,  outputs_dir / "manager_traces")
    _copy_dir(MANAGING_TRACES_SRC, outputs_dir / "managing_traces")
    _copy_dir(DEJAVU_TRACES_SRC,   outputs_dir / "dejavu_traces")
    _copy_dir(DEJAVU_SIMILAR_SRC,  outputs_dir / "similarities")
    _copy_dir(DATASET_REAL,        outputs_dir / "dataset")

    print(f"  [collect] Outputs saved to {outputs_dir}")


# ---------------------------------------------------------------------------
# Process management
# ---------------------------------------------------------------------------

def _stream(stream, label: str) -> None:
    """Read lines from a subprocess stream and print with [label] HH:MM:SS prefix."""
    for line in iter(stream.readline, b""):
        text = line.decode("utf-8", errors="replace").rstrip()
        if text:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{label}] {ts} | {text}", flush=True)


def _start_dejavu() -> subprocess.Popen:
    cmd = [_python(), "src/dejavu.py"]
    proc = subprocess.Popen(cmd, cwd=DEJAVU_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=_env())
    threading.Thread(target=_stream, args=(proc.stdout, "dejavu  "), daemon=True).start()
    threading.Thread(target=_stream, args=(proc.stderr, "dejavu  "), daemon=True).start()
    time.sleep(2.0)   # give Flask time to bind
    print(f"  [dejavu]   PID {proc.pid} started")
    return proc


def _start_manager() -> subprocess.Popen:
    cmd = [_python(), "src/main.py", "--experiment"]
    proc = subprocess.Popen(cmd, cwd=MANAGER_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=_env())
    threading.Thread(target=_stream, args=(proc.stdout, "manager "), daemon=True).start()
    threading.Thread(target=_stream, args=(proc.stderr, "manager "), daemon=True).start()
    time.sleep(1.0)
    print(f"  [manager]  PID {proc.pid} started")
    return proc


def _run_managing(timeout_s: int = 600) -> int:
    """Run Managing synchronously; returns exit code."""
    cmd = [_python(), "src/main.py"]
    print(f"  [managing] running (timeout={timeout_s}s)...")
    proc = subprocess.Popen(cmd, cwd=MANAGING_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=_env())
    threading.Thread(target=_stream, args=(proc.stdout, "managing"), daemon=True).start()
    threading.Thread(target=_stream, args=(proc.stderr, "managing"), daemon=True).start()
    try:
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        print("  [managing] TIMEOUT — killing")
        proc.kill()
    return proc.returncode or 0


def _stop(proc: subprocess.Popen, label: str) -> None:
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    print(f"  [{label}]  PID {proc.pid} stopped")


# ---------------------------------------------------------------------------
# Run one experiment
# ---------------------------------------------------------------------------

def run_experiment(name: str) -> None:
    exp_dir    = RESULTS_DIR / name
    inputs_dir = exp_dir / "inputs"
    outputs_dir = exp_dir / "outputs"

    if not inputs_dir.exists():
        print(f"[SKIP] '{name}' — inputs not found. Run build_simulations.py first.")
        return

    print(f"\n{'='*60}")
    print(f"  Experiment: {name}")
    print(f"{'='*60}")

    dejavu_proc  = None
    manager_proc = None

    try:
        _clear_output_sources()
        _apply_inputs(inputs_dir)
        print("  [config]   Inputs applied to component configs.")

        dejavu_proc  = _start_dejavu()
        manager_proc = _start_manager()

        _run_managing()

    finally:
        if manager_proc:
            _stop(manager_proc, "manager")
        if dejavu_proc:
            _stop(dejavu_proc, "dejavu")
        _restore_base()

    _collect_outputs(outputs_dir)

    print(f"  [done]     '{name}' complete.\n")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _list_built() -> list[str]:
    if not RESULTS_DIR.exists():
        return []
    return sorted(
        d.name for d in RESULTS_DIR.iterdir()
        if d.is_dir() and (d / "inputs").exists()
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Execute one or more built experiments."
    )
    parser.add_argument(
        "experiments",
        nargs="*",
        help="Experiment names to run. Omit to run all built experiments.",
    )
    args = parser.parse_args()

    targets = args.experiments or _list_built()

    if not targets:
        print("No built experiments found. Run build_simulations.py first.")
        sys.exit(1)

    print(f"Experiments to run: {targets}")
    for name in targets:
        run_experiment(name)

    print("All done.")


if __name__ == "__main__":
    main()
