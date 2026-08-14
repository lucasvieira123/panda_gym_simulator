import atexit
import sys
from datetime import datetime

import api
from constants import DEJAVU_CONF_PATH, PROJECT_ROOT
from utils import load_config
from manager_ws_client import ManagerWsClient
from antecipated_scenario_dataset_recorder import AntecipatedScenarioDatasetRecorder
from antecipated_scenario_monitor import AntecipatedScenarioMonitor
from unanticipated_scenario_identifier import UnanticipatedScenarioIdentifier
from trace import TraceWriter
from trace_printer import (
    format_tick,
    format_pipeline_identify,
    format_pipeline_diagnose,
    format_pipeline_similarities,
    format_pipeline_adaptation,
)

# Contexto inicial da state machine ARM — valores neutros/seguros
_SM_INITIAL = {
    "task_started":            0,
    "object_available":        0,
    "gripper_width_cm":        0,
    "distance_ee_object_cm":   999,
    "grasp_completed":         0,
    "finger_contacts":         0,
    "grasp_attempts":          0,
    "object_lift_height_cm":   0,
    "distance_object_goal_cm": 999,
    "task_aborted":            0,
    "action":                  None,
    "current_subtask":         "",   # "" = modo adaptativo; non-empty = domínio
}

# current_subtask (uppercase) → evento Sismic da state machine ARM
_SUBTASK_TO_ACTION = {
    "APPROACH_OBJECT": "approach_object() (APPROACH_OBJECT)",
    "GRASP_OBJECT":    "close_gripper() (GRASP_OBJECT)",
    "RETRY_GRASP":     "retry_grasp() (RETRY_GRASP)",
    "SAFE_ABORT":      "abort_grasp() (SAFE_ABORT)",
    "LIFT_OBJECT":     "lift_object() (LIFT_OBJECT)",
    "TRANSPORT_OBJECT":"transport_to_goal() (TRANSPORT_OBJECT)",
    "PLACE_OBJECT":    "place_object() (PLACE_OBJECT)",
}


def _sm_params(perception: dict, prev_subtask: str | None) -> tuple[dict, str | None, bool]:
    subtask = (perception.get("current_subtask") or "").upper()

    # ── ROLLBACK ──────────────────────────────────────────────────────────────
    # Comportamento original: dispara a ação apenas quando current_subtask muda.
    # Problema: quando is_success=True o episódio encerra sem nova mudança de
    # subtask, então place_object() nunca dispara e o SM nunca alcança FINAL.
    # Para reverter: descomenta a linha abaixo e apaga o bloco novo.
    # action = _SUBTASK_TO_ACTION.get(prev_subtask) if (subtask != (prev_subtask or "") and prev_subtask) else None
    # ──────────────────────────────────────────────────────────────────────────

    subtask_changed = subtask != (prev_subtask or "") and prev_subtask
    task_complete   = perception.get("is_success", False) and prev_subtask and not subtask_changed
    action = _SUBTASK_TO_ACTION.get(prev_subtask) if (subtask_changed or task_complete) else None
    # Quando a ação é disparada por task_complete (is_success), o contexto atual já
    # reflete o estado pós-ação — não rebobinar para _prev_tick, pois os guards de
    # pós-condição (ex: PHI_27: gripper_width_cm >= 6) precisam do tick atual.
    skip_rewind = bool(task_complete)
    return {
        "task_started":            perception.get("task_started",            0),
        "object_available":        perception.get("object_available",        0),
        "gripper_width_cm":        perception.get("gripper_width_cm",        0),
        "distance_ee_object_cm":   perception.get("distance_ee_object_cm",   999),
        "grasp_completed":         perception.get("grasp_completed",         0),
        "finger_contacts":         perception.get("finger_contacts",         0),
        "grasp_attempts":          perception.get("grasp_attempts",          0),
        "object_lift_height_cm":   perception.get("object_lift_height_cm",   0),
        "distance_object_goal_cm": perception.get("distance_object_goal_cm", 999),
        "task_aborted":            perception.get("task_aborted",            0),
        "action":                  action,
        "current_subtask":         subtask,  # "" = adaptativo; non-empty = domínio
    }, subtask or None, skip_rewind


def _active_state(monitor: AntecipatedScenarioMonitor) -> str:
    config = monitor.state_machine_engine.itp.configuration
    states = [s for s in config if s != "root"]
    return states[0] if states else "—"


def _last_sat(monitor: AntecipatedScenarioMonitor):
    return monitor.state_machine_engine._last_sat


def _log(writer: TraceWriter, msg: str) -> None:
    print(msg)
    writer.write(msg + "\n")


def main() -> None:
    cfg        = load_config(DEJAVU_CONF_PATH)
    ts         = datetime.now().strftime("%Y%m%d_%H%M%S")
    traces_dir = str(PROJECT_ROOT / cfg.get("traces_folder", "output/arm/traces"))
    writer     = TraceWriter(traces_dir, ts=ts)
    atexit.register(writer.close)

    dataset_dir = str(PROJECT_ROOT / cfg.get("antecipated_scenario_dataset_folder", "output/arm/antecipated_scenario_dataset"))
    recorder    = AntecipatedScenarioDatasetRecorder(dataset_dir, ts=ts)
    atexit.register(recorder.save)

    _log(writer, f"[Trace] Gravando em: {writer.path}")

    api.start(port=8002)

    # Conecta ao Manager imediatamente — não depende da console para começar
    client = ManagerWsClient()

    # Aguarda console em paralelo (opcional — DejaVu funciona sem ela)
    api.wait_for_console(timeout=30.0)

    monitor    = AntecipatedScenarioMonitor(_SM_INITIAL.copy())
    identifier = UnanticipatedScenarioIdentifier()

    prev_subtask:  str | None  = None
    identified:    dict | None = None
    prev_episode:  int | None  = None

    _log(writer, "[DejaVu] Aguardando new_perception do Manager...")

    try:
      while client.alive:
        perception = client.get_new_perception(timeout=30.0)
        if perception is None:
            continue

        episode = perception.get("episode")
        step    = perception.get("step", 0)
        subtask = perception.get("current_subtask", "—")

        # Novo episódio → reseta estado do pipeline
        if episode != prev_episode:
            identified   = None
            prev_subtask = None
            prev_episode = episode

        # ── State machine ─────────────────────────────────────────────────────
        sm_tick, prev_subtask, skip_rewind = _sm_params(perception, prev_subtask)
        monitor.handle_runtime_data(sm_tick, skip_rewind=skip_rewind)

        active        = _active_state(monitor)
        sat           = _last_sat(monitor)
        unanticipated = sat is False

        # ── Dataset ───────────────────────────────────────────────────────────
        recorder.record(perception, active_state=active, sat=sat)

        sm_eng = monitor.state_machine_engine

        # ── Trace por tick ────────────────────────────────────────────────────
        _log(writer, format_tick(
            episode        = episode,
            step           = step,
            subtask        = subtask,
            sm_params      = sm_tick,
            active_state   = active,
            sat            = sat,
            transitions    = sm_eng.last_transitions,
            action_queued  = sm_eng.last_action_queued,
            unanticipated  = unanticipated,
            context_params = perception,
        ))

        # ── Pipeline de diagnóstico (só na 1ª detecção por episódio) ──────────
        if unanticipated and identified is None:
            try:
                identified = identifier.identifies(None)
                _log(writer, format_pipeline_identify(identified))
            except Exception as e:
                _log(writer, f"  [PIPELINE] Erro: {e}")

        # ── Responde ao Manager ───────────────────────────────────────────────
        client.send_result({"status": "ok", "unanticipated": unanticipated})

        # ── Pusha estado para o DejaVu Console ───────────────────────────────
        api.update_state({
            "episode":         episode,
            "step":            step,
            "current_subtask": subtask,
            "active_sm_state": active,
            "sm_status":       "UNSAT" if unanticipated else "SAT",
            "unanticipated":   unanticipated,
            "new_perception":  perception,
            "identified":      identified,
        })
    finally:
        recorder.save()


if __name__ == "__main__":
    main()
