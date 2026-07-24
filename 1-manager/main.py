import api
from analyze import Analyzer
from asm_loader import load_asm
from asm_evaluator import AsmEvaluator
from execute import Executor
from knowledge import SystemState
from monitor import Monitor
from plan import Planner
from managing_ws_client import ManagingWsClient
from pathlib import Path


_ASM_PATH = Path(__file__).parent / "configs" / "asm.json"


def main() -> None:
    asm           = load_asm(_ASM_PATH)
    asm_evaluator = AsmEvaluator(asm)

    api.start(port=8001)
    api.wait_for_dashboard()

    import time
    time.sleep(1.5)

    client   = ManagingWsClient()
    monitor  = Monitor()
    analyzer = Analyzer(asm_evaluator)
    planner  = Planner(asm)
    executor = Executor(client)
    state    = SystemState()

    print("[Manager] Aguardando percepcoes do managing...\n")

    while True:
        msg = client.get_perception(timeout=30.0)
        if msg is None:
            print("[Manager] Nenhuma percepcao recebida. Aguardando...")
            continue

        print(f"[Manager] ep={msg.get('episode')} step={msg.get('step')} reward={msg.get('reward', 0):.4f}")

        state = monitor.update(msg, state)      # M
        state = analyzer.analyze(state)         # A

        if state.goal_status == "violated":
            strategy = planner.plan(state)      # P
            executor.execute(strategy)          # E
            print(f"[Manager] Adaptacao executada: {strategy}")

        api.update_state({
            "perception":           msg,
            "step":                 msg.get("step"),
            "episode":              msg.get("episode"),
            "current_asm_scenario": state.current_asm_scenario,
            "goal_status":          state.goal_status,
        })


if __name__ == "__main__":
    main()
