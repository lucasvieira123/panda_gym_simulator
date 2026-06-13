from manager_config import load_manager_config
from analyze import Analyzer
from execute import Executor
from knowledge import Knowledge, SystemState
from monitor import Monitor
from plan import Planner
from managing_bridge import ManagingBridge


def main() -> None:
    manager_cfg = load_manager_config()

    knowledge = Knowledge(
        adaptation_options=manager_cfg["adaptation_options"],
        situation_strategy_map=dict(manager_cfg["plan_options"]) or None,
    )

    bridge          = ManagingBridge()
    monitor         = Monitor()
    analyzer        = Analyzer(knowledge)
    planner         = Planner(knowledge)
    executor        = Executor(bridge)
    state           = SystemState()
    active_strategy: str | None = None

    print("[Manager] Aguardando percepcoes do managing...\n")

    while True:
        msg = bridge.get_perception(timeout=10.0)
        if msg is None:
            print("[Manager] Nenhuma percepcao recebida. Aguardando...")
            continue

        state    = monitor.update(msg, state)    # M
        state    = analyzer.analyze(state)       # A
        strategy = planner.plan(state)           # P

        if strategy != active_strategy:
            print(f"[Manager] Enviando comando: {strategy}")
            executor.execute(strategy)           # E
            active_strategy = strategy


if __name__ == "__main__":
    main()
