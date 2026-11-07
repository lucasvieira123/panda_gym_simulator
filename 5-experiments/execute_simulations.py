"""
execute_simulations.py
======================
For each built experiment (results/<name>/inputs/ must exist), this script:

  1. Overwrites the real component configs with the experiment's input files.
  2. Launches DejaVu (Flask), Manager, and Managing as subprocesses.
  3. Waits for Managing to finish (it terminates after all episodes).
  4. Collects all outputs into results/<name>/outputs/.
  5. Restores every component config from base/.
  6. Writes results/<name>/outcome.json with the run's explicit result.

Usage:
    python 5-experiments/execute_simulations.py [experiment_name ...]

    # Run all built experiments:
    python 5-experiments/execute_simulations.py

    # Run specific experiments:
    python 5-experiments/execute_simulations.py A_baseline C_low_friction_with_dejavu
"""

import argparse
import json
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

    # The Managing window recording (record_video) sits next to the run's outcome
    for video in sorted((outputs_dir / "managing_traces").glob("video_*.mp4")):
        shutil.move(str(video), str(outputs_dir / "video.mp4"))

    # DejaVu may have evolved the ASM during the run; base/ restores it right after this.
    asm_after_run = COMPONENT_DEST["manager"]["arm/asm.json"]
    outputs_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(asm_after_run, outputs_dir / "asm_after_run.json")

    print(f"  [collect] Outputs saved to {outputs_dir}")


# ---------------------------------------------------------------------------
# Run outcome
# ---------------------------------------------------------------------------

def _read_jsonl(folder: Path, pattern: str) -> list[dict]:
    records = []
    for path in sorted(folder.glob(pattern)):
        with open(path, encoding="utf-8") as f:
            records.extend(json.loads(line) for line in f if line.strip())
    return records


def _adaptation_result(events: list[dict], run: dict) -> dict:
    """Every adaptive action ends with success, failure, timeout or execution_error."""
    if not any(e["event"] == "violation" for e in events):
        return {"status": "not_applicable", "reason": "no_violation"}

    pipeline_error = next((e for e in events if e["event"] == "pipeline_error"), None)
    if pipeline_error:
        return {"status": "execution_error", "reason": f"pipeline_{pipeline_error['stage'].lower()}",
                "message": pipeline_error["message"]}

    selected = next((e for e in events if e["event"] == "adaptation_selected"), None)
    if selected is None or selected["adaptation"] is None:
        return {"status": "not_applicable", "reason": "no_applicable_candidate"}

    terminal = next((e for e in reversed(events) if e["event"] == "evaluation" and e.get("reason")), None)
    if terminal:
        return {"status": terminal["status"], "reason": terminal["reason"], "ticks": terminal["ticks"],
                "run_ticks": terminal["run_ticks"], "then_clauses": terminal["then_clauses"],
                "candidate_then": terminal["candidate_then"]}
    if run["timed_out"]:
        return {"status": "timeout", "reason": "runner_timeout"}
    return {"status": "execution_error", "reason": "run_ended_without_result"}


def _scenario(outcome: dict) -> str:
    """A: sem violação. B e C: objetivo atingido na tentativa 1 ou 2. D: fail-safe. E: falha não detectada."""
    goal = outcome["physical"].get("global_goal_achieved")
    if not outcome["violation"]:
        return "A" if goal else "no_violation_without_goal"
    if outcome["fail_safe"]:
        return "D"
    attempts = outcome["attempts"]
    if not attempts:
        return "no_adaptation"
    if attempts[-1]["status"] != "success":
        return "inconclusive"
    if not goal:
        return "E"
    return "B" if attempts[-1]["attempt"] == 1 else "C"


def _write_outcome(name: str, exp_dir: Path, outputs_dir: Path, run: dict) -> dict:
    ticks  = _read_jsonl(outputs_dir / "managing_traces", "ticks_*.jsonl")
    events = _read_jsonl(outputs_dir / "dejavu_traces", "events_*.jsonl")

    last_tick   = next((t for t in reversed(ticks) if t["event"] == "tick"), {})
    episode_end = next((t for t in reversed(ticks) if t["event"] == "episode_end"), None)
    first = lambda kind: next((e for e in events if e["event"] == kind), None)
    selected = first("adaptation_selected")

    outcome = {
        "experiment": name,
        "lateral_friction": last_tick.get("object_lateral_friction"),
        "run": run,
        "sequence": {
            "completed": bool(last_tick.get("is_success")),
            "episode_end": episode_end["reason"] if episode_end else "not_reached",
            "last_step": last_tick.get("step"),
            "last_subtask": last_tick.get("current_subtask"),
            "last_phase": last_tick.get("task_phase"),
        },
        "violation": first("violation"),
        "diagnosis": first("diagnosis"),
        "ranking": first("ranking"),
        "adaptation_selected": selected["adaptation"] if selected else None,
        "adaptation_result": _adaptation_result(events, run),
        "attempts": [
            {key: e.get(key) for key in ("attempt", "candidate", "status", "reason", "ticks", "run_ticks", "step")}
            for e in events if e["event"] == "evaluation" and e.get("reason")
        ],
        "retry_decisions": [
            {key: e.get(key) for key in ("attempt", "action", "reason", "step")}
            for e in events if e["event"] == "retry_decision"
        ],
        "fail_safe": (episode_end or {}).get("detail") if (episode_end or {}).get("reason") == "fail_safe" else None,
        "asm_evolved": first("asm_evolution") is not None,
        "physical": {
            **(last_tick.get("physical_outcome") or {}),
            "dist_cube_to_target_m": last_tick.get("dist_cube_to_target"),
            "fingers_width_m": last_tick.get("fingers_width"),
            "finger_contacts": last_tick.get("finger_contacts"),
            "cube_position": last_tick.get("cube_position"),
            "cube_rotation": last_tick.get("cube_rotation"),
        },
    }
    outcome["scenario"] = _scenario(outcome)
    with open(exp_dir / "outcome.json", "w", encoding="utf-8") as f:
        json.dump(outcome, f, indent=2, ensure_ascii=False)
    return outcome


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


def _run_managing(timeout_s: int) -> dict:
    """Run Managing synchronously; returns how the run ended."""
    cmd = [_python(), "src/main.py"]
    print(f"  [managing] running (timeout={timeout_s}s)...")
    started = time.monotonic()
    proc = subprocess.Popen(cmd, cwd=MANAGING_DIR, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=_env())
    threading.Thread(target=_stream, args=(proc.stdout, "managing"), daemon=True).start()
    threading.Thread(target=_stream, args=(proc.stderr, "managing"), daemon=True).start()
    timed_out = False
    try:
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        print("  [managing] TIMEOUT — killing")
        timed_out = True
        proc.kill()
        proc.wait()
    return {
        "timeout_s": timeout_s,
        "timed_out": timed_out,
        "managing_exit_code": proc.returncode,
        "duration_s": round(time.monotonic() - started, 1),
    }


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

def run_experiment(name: str, managing_timeout_s: int) -> None:
    exp_dir    = RESULTS_DIR / name
    inputs_dir = exp_dir / "inputs"
    outputs_dir = exp_dir / "outputs"

    if not inputs_dir.exists():
        print(f"[SKIP] '{name}' — inputs not found. Run build_simulations.py first.")
        return

    print(f"\n{'='*60}")
    print(f"  Experiment: {name}")
    print(f"{'='*60}")

    # A rerun must not mix its outputs with the previous run's.
    if outputs_dir.exists():
        previous = exp_dir / f"outputs_previous_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        outputs_dir.rename(previous)
        print(f"  [keep]     Previous outputs moved to {previous.name}")

    dejavu_proc  = None
    manager_proc = None
    run: dict    = {"timeout_s": managing_timeout_s, "timed_out": False, "managing_exit_code": None, "duration_s": None}

    try:
        _clear_output_sources()
        _apply_inputs(inputs_dir)
        print("  [config]   Inputs applied to component configs.")

        dejavu_proc  = _start_dejavu()
        manager_proc = _start_manager()

        run = _run_managing(managing_timeout_s)
        run["dejavu_alive_at_end"]  = dejavu_proc.poll() is None
        run["manager_alive_at_end"] = manager_proc.poll() is None

    finally:
        if manager_proc:
            _stop(manager_proc, "manager")
        if dejavu_proc:
            _stop(dejavu_proc, "dejavu")
        # Collect before restoring: _restore_base() replaces the dataset with base/ and
        # would discard the CSV recorded in this run.
        _collect_outputs(outputs_dir)
        _restore_base()

    outcome = _write_outcome(name, exp_dir, outputs_dir, run)
    result  = outcome["adaptation_result"]
    print(f"  [outcome]  scenario={outcome['scenario']}  fail_safe={outcome['fail_safe']}  "
          f"adaptation={result['status']} ({result['reason']})  "
          f"sequence_completed={outcome['sequence']['completed']}  "
          f"global_goal={outcome['physical'].get('global_goal_achieved')}  "
          f"timed_out={run['timed_out']}")
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
    parser.add_argument(
        "--managing-timeout",
        type=int,
        default=600,
        help="Seconds before a run is stopped; recorded in outcome.json (default: 600).",
    )
    args = parser.parse_args()

    targets = args.experiments or _list_built()

    if not targets:
        print("No built experiments found. Run build_simulations.py first.")
        sys.exit(1)

    print(f"Experiments to run: {targets}")
    for name in targets:
        run_experiment(name, args.managing_timeout)

    print("All done.")


if __name__ == "__main__":
    main()
