import atexit
import sys

import api
from manager_ws_client import ManagerWsClient
from antecipated_scenario_monitor import AntecipatedScenarioMonitor
from unanticipated_scenarios_detector import UnanticipatedScenariosDetector
from unanticipated_scenario_identifier import UnanticipatedScenarioIdentifier
from trace import TraceWriter
from trace_printer import (
    format_tick,
    format_pipeline_detect,
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
}

# active_key → (action_event, THEN_condition)
# active_key = current_subtask (uppercase) when non-empty, else current_task (uppercase).
# The action fires when the THEN condition first transitions False→True within the same key.
# If THEN is already True when the key changes (system outpaced detection), it fires on
# the key-change tick instead — but only if the action hasn't already been fired.
_ACTION_THEN = {
    "APPROACH_OBJECT":  (
        "approach_object() (APPROACH_OBJECT)",
        lambda ctx: ctx["distance_ee_object_cm"] <= 2,
    ),
    "GRASP_OBJECT":     (
        "close_gripper() (GRASP_OBJECT)",
        lambda ctx: ctx["grasp_completed"] == 1,
    ),
    "LIFT_OBJECT":      (
        "lift_object() (LIFT_OBJECT)",
        lambda ctx: ctx["object_lift_height_cm"] >= 10 and ctx["finger_contacts"] >= 2,
    ),
    "TRANSPORT_OBJECT": (
        "transport_to_goal() (TRANSPORT_OBJECT)",
        lambda ctx: (ctx["distance_object_goal_cm"] <= 5
                     and ctx["object_lift_height_cm"] >= 10
                     and ctx["finger_contacts"] >= 2),
    ),
    "PLACE_OBJECT":     (
        "place_object() (PLACE_OBJECT)",
        lambda ctx: ctx["distance_object_goal_cm"] <= 5 and ctx["gripper_width_cm"] >= 6,
    ),
    "RETRY_GRASP":      (
        "retry_grasp() (RETRY_GRASP)",
        lambda ctx: ctx["grasp_completed"] == 1,
    ),
    "SAFE_ABORT":       (
        "abort_grasp() (SAFE_ABORT)",
        lambda ctx: ctx["task_aborted"] == 1,
    ),
    "ABORT":            (
        "abort_grasp() (SAFE_ABORT)",
        lambda ctx: ctx["task_aborted"] == 1,
    ),
}


def _sm_params(
    perception:   dict,
    prev_key:     str | None,
    prev_then:    bool,
    action_fired: bool,
) -> tuple[dict, str | None, bool, bool]:
    subtask      = (perception.get("current_subtask") or "").upper()
    current_task = (perception.get("current_task")    or "").upper()
    active_key   = subtask or current_task or None

    ctx = {
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
    }

    action     = None
    curr_then  = False
    key_changed = active_key != prev_key

    if key_changed:
        # The key changed before we observed THEN going True: if the previous key's
        # THEN is satisfied right now and the action was never fired, fire it here.
        if prev_key and not action_fired and prev_key in _ACTION_THEN:
            _, then_cond = _ACTION_THEN[prev_key]
            if then_cond(ctx):
                action = _ACTION_THEN[prev_key][0]
        # Reset per-key tracking for the incoming key
        prev_then    = False
        action_fired = False
    else:
        # Same key: fire on the first False→True transition of the THEN condition.
        # Reset action_fired when THEN goes back to False so looping scenarios
        # (e.g. RETRY_GRASP cycling multiple times) can re-trigger on the next rise.
        if active_key and active_key in _ACTION_THEN:
            _, then_cond = _ACTION_THEN[active_key]
            curr_then    = then_cond(ctx)
            if curr_then and not prev_then and not action_fired:
                action       = _ACTION_THEN[active_key][0]
                action_fired = True
            elif not curr_then and action_fired:
                action_fired = False

    return {**ctx, "action": action}, active_key, curr_then, action_fired


def _active_state(monitor: AntecipatedScenarioMonitor) -> str:
    config = monitor.state_machine_engine.itp.configuration
    states = [s for s in config if s != "root"]
    return states[0] if states else "—"


def _last_sat(monitor: AntecipatedScenarioMonitor):
    df = monitor.state_machine_engine.monitored_scenarios_df
    sat_vals = df["SAT"].dropna()
    return sat_vals.iloc[-1] if not sat_vals.empty else None


def _log(writer: TraceWriter, msg: str) -> None:
    print(msg)
    writer.write(msg + "\n")


def main() -> None:
    writer = TraceWriter()
    atexit.register(writer.close)

    _log(writer, f"[Trace] Gravando em: {writer.path}")

    api.start(port=8002)

    # Conecta ao Manager imediatamente — não depende da console para começar
    client = ManagerWsClient()

    # Aguarda console em paralelo (opcional — DejaVu funciona sem ela)
    api.wait_for_console(timeout=30.0)

    monitor    = AntecipatedScenarioMonitor(_SM_INITIAL.copy())
    detector   = UnanticipatedScenariosDetector()
    identifier = UnanticipatedScenarioIdentifier()

    prev_key:     str | None  = None
    prev_then:    bool        = False
    action_fired: bool        = False
    identified:   dict | None = None
    prev_episode: int | None  = None

    _log(writer, "[DejaVu] Aguardando new_perception do Manager...")

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
            prev_key     = None
            prev_then    = False
            action_fired = False
            prev_episode = episode

        # ── State machine ─────────────────────────────────────────────────────
        sm_tick, prev_key, prev_then, action_fired = _sm_params(
            perception, prev_key, prev_then, action_fired
        )
        monitor.handle_runtime_data(sm_tick)

        active        = _active_state(monitor)
        sat           = _last_sat(monitor)
        unanticipated = sat is False

        sm_eng = monitor.state_machine_engine

        # ── Trace por tick ────────────────────────────────────────────────────
        _log(writer, format_tick(
            episode       = episode,
            step          = step,
            subtask       = subtask,
            sm_params     = sm_tick,
            active_state  = active,
            sat           = sat,
            transitions   = sm_eng.last_transitions,
            action_queued = sm_eng.last_action_queued,
            unanticipated = unanticipated,
        ))

        # ── Pipeline de diagnóstico (só na 1ª detecção por episódio) ──────────
        if unanticipated and identified is None:
            detected_df = None
            try:
                detected_df = detector.detects()
                _log(writer, format_pipeline_detect(detected_df))

                identified = identifier.identifies(detected_df)
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


if __name__ == "__main__":
    main()
