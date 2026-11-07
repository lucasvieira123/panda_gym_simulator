import argparse
import atexit
import sys
from pathlib import Path

import api
from analyze import Analyzer
from perception_printer import print_perception
from trace import TraceWriter
from asm_loader import load_asm
from asm_evaluator import AsmEvaluator
from execute import Executor
from knowledge import SystemState
from monitor_arm import MonitorARM
from plan import Planner
from managing_ws_client import ManagingWsClient
from ts import ts, set_step


_ASM_PATH = Path(__file__).parent.parent / "configs" / "arm" / "asm.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment", action="store_true",
                        help="Skip wait_for_dashboard (used by automated experiment runs)")
    args = parser.parse_args()

    _writer      = TraceWriter()
    _real_stdout = sys.stdout

    class _Tee:
        def write(self, text):
            _real_stdout.write(text)
            _writer._file.write(text)
            _writer._file.flush()
        def flush(self):
            _real_stdout.flush()
        def isatty(self):
            return _real_stdout.isatty()

    sys.stdout = _Tee()
    atexit.register(_writer.close)
    atexit.register(lambda: setattr(sys, "stdout", _real_stdout))

    print(f"[Trace] Gravando em: {_writer.path}")

    asm           = load_asm(_ASM_PATH)
    asm_evaluator = AsmEvaluator(asm)

    api.start(port=8001)
    if not args.experiment:
        api.wait_for_dashboard()

    import time
    time.sleep(1.5)

    client   = ManagingWsClient()
    monitor  = MonitorARM()
    analyzer = Analyzer(asm_evaluator)
    planner  = Planner(asm)
    executor = Executor(client)
    state    = SystemState()

    print(f"[{ts()}][Manager] Aguardando percepcoes do managing...\n")

    _post_adaptation     = False       # True após enviar "adapt", até próximo "ok" do ASM
    _dj_dispatched: set = set()             # tentativas do DejaVu já enviadas: (episódio, tentativa)
    _dj_reported: set = set()               # resultados do DejaVu já registrados: (episódio, tipo)

    while client.alive:
        msg = client.get_perception()
        if msg is None:
            continue

        set_step(msg.get("step", 0))
        episode = msg.get("episode")
        print(f"[{ts()}][Manager] ep={episode} subtask={msg.get('current_subtask','')} reward={msg.get('reward', 0):.4f}")

        state = monitor.update(msg, state)      # M

        print_perception(msg, state)

        state = analyzer.analyze(state)         # A

        dj = api.send_to_dejavu(state.to_new_perception())  # DejaVu checkpoint
        print(f"[{ts()}][DejaVu] {dj}")

        dj_unanticipated = bool(dj.get("unanticipated")) if dj else False
        dj_adaptation    = dj.get("adaptation")          if dj else None

        # O DejaVu decide o próximo candidato ou o fail-safe; o Manager executa.
        dj_evaluation = dj.get("evaluation") if dj else None
        if (dj_evaluation and dj_evaluation.get("reason")
                and (episode, "evaluation", dj_evaluation.get("attempt")) not in _dj_reported):
            _dj_reported.add((episode, "evaluation", dj_evaluation.get("attempt")))
            print(f"[{ts()}][Manager][DejaVu] Resultado da adaptação: {dj_evaluation['status']} "
                  f"(razão: {dj_evaluation['reason']}, candidato: {dj_evaluation.get('candidate')})")
        dj_error = dj.get("pipeline_error") if dj else None
        if dj_error and (episode, "error") not in _dj_reported:
            _dj_reported.add((episode, "error"))
            print(f"[{ts()}][Manager][DejaVu] Sem recomendação: falha em {dj_error['stage']} "
                  f"({dj_error['type']}: {dj_error['message']})")

        dj_fail_safe = dj.get("fail_safe") if dj else None
        if dj_fail_safe:
            if (episode, "fail_safe") not in _dj_reported:
                _dj_reported.add((episode, "fail_safe"))
                executor.send_fail_safe(dj_fail_safe["reason"])
                print(f"[{ts()}][Manager][DejaVu] FAIL-SAFE: {dj_fail_safe['reason']} — operador notificado")
                api.update_state({
                    "perception": msg, "step": msg.get("step"), "episode": msg.get("episode"),
                    "current_asm_scenario": state.current_asm_scenario,
                    "goal_status": state.goal_status, "fail_safe": dj_fail_safe,
                })
            continue

        # E — prioridade: DejaVu age apenas quando o ASM interno não reconhece a violação.
        # Se goal_status == "violated", o ASM interno já sabe tratar → planner interno ganha.
        pending_domain = asm_evaluator.pending_scenario_key

        dj_attempt = dj_adaptation.get("attempt", 1) if dj_adaptation else 1

        if (dj_adaptation and (dj_unanticipated or dj_attempt > 1)
                and state.goal_status != "violated"
                and (episode, dj_attempt) not in _dj_dispatched
                and (not _post_adaptation or dj_attempt > 1)):
            # DejaVu detectou algo que o ASM interno não capturou.
            # Tratamos como cenário adaptativo: send_adapt com o "do" do candidato top-1.
            executor.send_adapt(dj_adaptation["do"])
            _post_adaptation    = True
            _dj_dispatched.add((episode, dj_attempt))
            print(f"[{ts()}][Manager][DejaVu] Adaptação {dj_attempt}: {dj_adaptation['candidate_name']} (score={dj_adaptation['score']:.3f}) → {dj_adaptation['do']}")

        elif _post_adaptation and state.goal_status == "not_applicable" and pending_domain:
            # O ASM validou uma transição pendente (ex: transport→place a 5cm).
            # Não forçamos: deixamos o managing avançar naturalmente via advance_if_done()
            # quando a task atingir o seu próprio threshold (5mm). Assim o transporte
            # completa corretamente em vez de ser cortado pelo threshold do ASM (5cm).
            executor.send_continue()
            _post_adaptation = False

        elif state.goal_status == "not_applicable":
            executor.send_continue()

        elif state.goal_status == "ok":
            if _post_adaptation:
                # manager dirige o que vem depois da adaptação (ASM tem a visão)
                executor.send_transition(state.current_asm_scenario)
                _post_adaptation = False
                print(f"[{ts()}][Manager] Pós-adaptação → transition para {state.current_asm_scenario}")
            else:
                executor.send_continue()

        elif state.goal_status == "violated":
            strategy = planner.plan(state)      # P — ASM interno conhece o cenário
            executor.send_adapt(strategy)       # E
            _post_adaptation = True
            print(f"[{ts()}][Manager] Adaptação interna: {strategy}")

        api.update_state({
            "perception":           msg,
            "step":                 msg.get("step"),
            "episode":              msg.get("episode"),
            "current_asm_scenario": state.current_asm_scenario,
            "goal_status":          state.goal_status,
        })


if __name__ == "__main__":
    main()
