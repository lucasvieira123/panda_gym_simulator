import atexit
import json
import os
import sys
import traceback
from pathlib import Path
from datetime import datetime

import pandas as pd

import api
from constants import DEJAVU_CONF_PATH, PROJECT_ROOT
from utils import load_config
from manager_ws_client import ManagerWsClient
from antecipated_scenario_dataset_recorder import AntecipatedScenarioDatasetRecorder
from antecipated_scenario_monitor import AntecipatedScenarioMonitor
from unanticipated_scenario_identifier import UnanticipatedScenarioIdentifier
from unanticipated_scenario_diagnoser import UnanticipatedScenarioDiagnoser
from similarity_based_adapter import SimilarityBasedAdapter
from adaptation_evaluator import AdaptationEvaluator
from asm_evolver import AsmEvolver, EvolutionRejected
from trace import TraceWriter
from trace_printer import (
    format_tick,
    format_pipeline_identify,
    format_pipeline_diagnose,
    format_pipeline_when_filter,
    format_pipeline_similarities,
    format_pipeline_adaptation,
    format_pipeline_evaluation,
    format_pipeline_error,
    format_retry_decision,
    format_asm_evolution,
)
from retry_policy import decide_after_attempt
from run_events import RunEventLog
from subtask_events import SubtaskEventMapper

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

def _sm_params(perception: dict, prev_subtask: str | None, mapper: SubtaskEventMapper,
               awaited_events: set[str]) -> tuple[dict, str | None, bool]:
    subtask = (perception.get("current_subtask") or "").upper()

    # Dispara a ação quando current_subtask muda ou quando is_success encerra o episódio sem
    # nova mudança (senão place_object() nunca dispara e o SM nunca alcança FINAL). O evento de
    # um cenário evoluído só dispara ao sair da sua fase (ver subtask_events.py).
    subtask_changed = subtask != (prev_subtask or "") and prev_subtask
    task_complete   = bool(perception.get("is_success", False) and prev_subtask and not subtask_changed)
    action = mapper.action(prev_subtask, subtask, task_complete, awaited_events)
    # Quando a ação é disparada por task_complete (is_success), o contexto atual já
    # reflete o estado pós-ação — não rebobinar para _prev_tick, pois os guards de
    # pós-condição (ex: PHI_27: gripper_width_cm >= 6) precisam do tick atual.
    skip_rewind = task_complete
    # Variáveis do ASM fora do contexto fixo (ex.: lateral_friction no Given de um cenário evoluído)
    asm_variables = {v: perception[v] for v in mapper.variables
                     if v not in _SM_INITIAL and perception.get(v) is not None}
    return {
        **asm_variables,
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


def _active_scenario(monitor: AntecipatedScenarioMonitor) -> dict:
    return monitor.state_machine_engine.itp.context.get(
        "active_scenario", {"name": "", "type": None}
    )


def _last_sat(monitor: AntecipatedScenarioMonitor):
    return monitor.state_machine_engine._last_sat


def _log(writer: TraceWriter, msg: str) -> None:
    print(msg)
    writer.write(msg + "\n")


def _physical_snapshot(perception: dict, sm_tick: dict) -> dict:
    """Relevant sensor values at this tick, for the run's event log."""
    snapshot = {k: v for k, v in sm_tick.items() if k != "action"}
    for key in ("lateral_friction", "fingers_width", "dist_cube_to_target", "is_success", "global_goal_achieved",
                "cube_x", "cube_y", "cube_z", "cube_roll", "cube_pitch", "cube_yaw",
                "ee_x", "ee_y", "ee_z"):
        snapshot[key] = perception.get(key)
    return snapshot


def _adaptation_awaiting_evolution(evaluation: dict | None, perception: dict) -> bool:
    """A successful adaptation is only judged for evolution when the action sequence ends."""
    return bool(evaluation and evaluation.get("status") == "success" and perception.get("is_success"))


def _write_similarities(path: str, results: list, run_id: str, episode: int) -> None:
    with open(path, "a", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps({"run_id": run_id, "episode": episode, **r}, default=str) + "\n")


def main() -> None:
    cfg              = load_config(DEJAVU_CONF_PATH)
    ts               = datetime.now().strftime("%Y%m%d_%H%M%S")
    traces_dir       = str(PROJECT_ROOT / cfg.get("traces_folder", "output/arm/traces"))
    similarities_dir = str(PROJECT_ROOT / cfg.get("similarities_folder", "output/arm/similarities"))
    os.makedirs(similarities_dir, exist_ok=True)
    similarities_path = os.path.join(similarities_dir, f"similarities_{ts}.jsonl")
    writer           = TraceWriter(traces_dir, ts=ts)
    atexit.register(writer.close)
    events = RunEventLog(os.path.join(traces_dir, f"events_{ts}.jsonl"))
    atexit.register(events.close)

    dataset_dir = str(PROJECT_ROOT / cfg.get("antecipated_scenario_dataset_folder", "output/arm/antecipated_scenario_dataset"))
    recorder    = AntecipatedScenarioDatasetRecorder(dataset_dir, ts=ts)
    atexit.register(recorder.save)

    _log(writer, f"[Trace] Gravando em: {writer.path}")

    api.start(port=8002)

    # Conecta ao Manager imediatamente — não depende da console para começar
    client = ManagerWsClient()

    # Aguarda console em paralelo (opcional — DejaVu funciona sem ela)
    api.wait_for_console(timeout=30.0)

    asm_path = str(PROJECT_ROOT / cfg["anticipated_scenarios_path"])

    monitor    = AntecipatedScenarioMonitor(_SM_INITIAL.copy())
    identifier = UnanticipatedScenarioIdentifier()
    diagnoser  = UnanticipatedScenarioDiagnoser()
    adapter    = SimilarityBasedAdapter()
    evaluator  = AdaptationEvaluator(max_eval_ticks=30)
    evolver    = AsmEvolver(asm_path)
    with open(asm_path, encoding="utf-8") as f:
        subtask_events = SubtaskEventMapper(json.load(f))  # ASM do início do run, o mesmo do monitor

    prev_subtask:  str | None   = None
    identified:    dict | None  = None
    diagnosed:     dict | None  = None
    similarities:  list | None  = None
    adaptation:    dict | None  = None
    evaluation:    dict | None  = None
    asm_evolution: dict | None  = None
    evolved:       bool         = False
    prev_episode:  int | None   = None
    pipeline_error: dict | None = None
    fail_safe:      dict | None = None
    prev_evaluation_status: str | None = None

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
            diagnosed    = None
            similarities = None
            adaptation   = None
            evaluation   = None
            asm_evolution = None
            evolved      = False
            prev_subtask = None
            prev_episode = episode
            pipeline_error = None
            fail_safe = None
            prev_evaluation_status = None
            evaluator.reset()

        # ── State machine ─────────────────────────────────────────────────────
        sm_tick, prev_subtask, skip_rewind = _sm_params(
            perception, prev_subtask, subtask_events, monitor.state_machine_engine.awaited_events())
        monitor.handle_runtime_data(sm_tick, skip_rewind=skip_rewind)

        # ── Avaliação pós-adaptação ────────────────────────────────────────────
        # Chamado antes do pipeline para usar os parâmetros deste tick.
        # start() só é chamado dentro do pipeline (1ª detecção), portanto
        # evaluate() vê sempre o tick corrente — sem confusão de timing.
        evaluation = evaluator.evaluate(sm_tick, sequence_done=bool(perception.get("is_success")))
        if evaluation and evaluation["status"] != prev_evaluation_status:
            prev_evaluation_status = evaluation["status"]
            events.write("evaluation", episode=episode, step=step, **evaluation,
                         observed=_physical_snapshot(perception, sm_tick))
            if evaluation.get("reason"):
                observed = _physical_snapshot(perception, sm_tick)
                attempt  = adaptation["attempt"]
                decision = decide_after_attempt(evaluation, attempt, len(similarities), observed)
                if decision:
                    _log(writer, format_retry_decision(decision, attempt))
                    events.write("retry_decision", episode=episode, step=step, attempt=attempt, **decision, observed=observed)
                if decision and decision["action"] == "retry":
                    adaptation = {**adapter.recommend(similarities[attempt:]), "attempt": attempt + 1}
                    events.write("adaptation_selected", episode=episode, step=step, adaptation=adaptation)
                    evaluator.start(diagnosed, adaptation)
                    prev_evaluation_status = None
                elif decision:
                    fail_safe = {"reason": decision["reason"], "attempt": attempt}

        active        = _active_state(monitor)
        scenario      = _active_scenario(monitor)
        sat           = _last_sat(monitor)
        unanticipated = sat is False

        # ── Dataset ───────────────────────────────────────────────────────────
        recorder.record(perception, active_state=active, sat=sat,
                        active_scenario_name=scenario["name"],
                        active_scenario_type=scenario["type"])

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
            stage = "IDENTIFY"
            where = {"episode": episode, "step": step, "active_scenario": scenario["name"], "active_state": active}
            events.write("violation", **where, observed=_physical_snapshot(perception, sm_tick))
            try:
                ctx = {"anticipated_scenario": scenario["name"], **sm_tick}
                unanticipated_df = pd.DataFrame([ctx, ctx])
                identified = identifier.identifies(unanticipated_df)
                _log(writer, format_pipeline_identify(identified))

                stage = "DIAGNOSE"
                diagnosed = diagnoser.diagnosis(identified, current_execution=Path(recorder.path).stem)
                _log(writer, format_pipeline_diagnose(diagnosed))
                events.write("diagnosis", **where, given=diagnosed["given"], when=diagnosed["when"],
                             then=diagnosed["then"], diagnostic_conditions=diagnosed["diagnostic_conditions"])

                stage = "RETRIEVE"
                similarities = adapter.calculate_similarity(diagnosed)
                _log(writer, format_pipeline_when_filter(adapter.last_when_filter))
                similarities.sort(
                    key=lambda s: s["similarity_result"],
                    reverse=True,
                )
                _log(writer, format_pipeline_similarities(similarities))
                _write_similarities(similarities_path, similarities, run_id=ts, episode=episode)
                events.write("ranking", **where, when_filter=adapter.last_when_filter, ranking=[
                    {"candidate": s["candidate"]["name"], "do": s["candidate"]["do"], "score": s["similarity_result"]}
                    for s in similarities
                ])

                adaptation = adapter.recommend(similarities)
                if adaptation:
                    adaptation["attempt"] = 1
                _log(writer, format_pipeline_adaptation(adaptation["do"] if adaptation else None))
                events.write("adaptation_selected", **where, adaptation=adaptation)

                if adaptation:
                    evaluator.start(diagnosed, adaptation)
            except Exception as e:
                pipeline_error = {"stage": stage, "type": type(e).__name__, "message": str(e)}
                _log(writer, format_pipeline_error(pipeline_error))
                events.write("pipeline_error", **where, **pipeline_error, traceback=traceback.format_exc())
                # identified guards the pipeline: it runs only once per episode, even after an error
                identified = identified or {"name": scenario["name"], "error": pipeline_error}

        # ── Log da avaliação (só quando activa) ──────────────────────────────
        if evaluation:
            _log(writer, format_pipeline_evaluation(evaluation))

        # ── Evolução do ASM (no fim do episódio, só com recuperação validada de ponta a ponta) ──
        if (_adaptation_awaiting_evolution(evaluation, perception)
                and not evolved and identified and diagnosed and adaptation):
            evolved = True
            if perception.get("global_goal_achieved"):
                try:
                    asm_evolution = evolver.evolve(identified, diagnosed, adaptation, context=perception)
                    _log(writer, format_asm_evolution(asm_evolution))
                    events.write("asm_evolution", episode=episode, step=step, **asm_evolution)
                except EvolutionRejected as e:
                    _log(writer, f"  [ASM_EVOLVE] Evolução recusada: {e}")
                    events.write("evolution_rejected", episode=episode, step=step, reason=e.reason, detail=e.detail)
                except Exception as e:
                    _log(writer, f"  [ASM_EVOLVE] Erro: {e}")
                    events.write("asm_evolution_error", episode=episode, step=step, type=type(e).__name__, message=str(e))
            else:
                _log(writer, "  [ASM_EVOLVE] Não evoluído: objetivo global não atingido")
                events.write("asm_evolution_skipped", episode=episode, step=step, reason="global_goal_not_achieved",
                             observed=_physical_snapshot(perception, sm_tick))

        # ── Responde ao Manager ───────────────────────────────────────────────
        client.send_result({
            "status":        "ok",
            "unanticipated": unanticipated,
            "adaptation":    adaptation,
            "evaluation":    evaluation,
            "pipeline_error": pipeline_error,
            "fail_safe":     fail_safe,
        })

        # ── Pusha estado para o DejaVu Console ───────────────────────────────
        api.update_state({
            "episode":              episode,
            "step":                 step,
            "current_subtask":      subtask,
            "active_sm_state":      active,
            "active_scenario_name": scenario["name"],
            "active_scenario_type": scenario["type"],
            "sm_status":            "UNSAT" if unanticipated else "SAT",
            "unanticipated":        unanticipated,
            "new_perception":       perception,
            "identified":           identified,
            "diagnosed":            diagnosed,
            "similarities":         similarities,
            "adaptation":           adaptation,
            "evaluation":           evaluation,
            "asm_evolution":        asm_evolution,
            "fail_safe":            fail_safe,
        })
    finally:
        recorder.save()


if __name__ == "__main__":
    main()
