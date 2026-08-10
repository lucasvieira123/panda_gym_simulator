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

    _post_adaptation = False  # True após enviar "adapt", até próximo "ok" do ASM

    while client.alive:
        msg = client.get_perception()
        if msg is None:
            continue

        set_step(msg.get("step", 0))
        print(f"[{ts()}][Manager] ep={msg.get('episode')} subtask={msg.get('current_subtask','')} reward={msg.get('reward', 0):.4f}")

        state = monitor.update(msg, state)      # M

        print_perception(msg, state)

        state = analyzer.analyze(state)         # A

        dj = api.send_to_dejavu(state.to_new_perception())  # DejaVu checkpoint
        print(f"[{ts()}][DejaVu] {dj}")

        # E — sempre responde ao checkpoint do managing
        if state.goal_status == "not_applicable":
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
            strategy = planner.plan(state)      # P
            executor.send_adapt(strategy)       # E
            _post_adaptation = True
            print(f"[{ts()}][Manager] Adaptacao iniciada: {strategy}")

        api.update_state({
            "perception":           msg,
            "step":                 msg.get("step"),
            "episode":              msg.get("episode"),
            "current_asm_scenario": state.current_asm_scenario,
            "goal_status":          state.goal_status,
        })


if __name__ == "__main__":
    main()
