import api
from manager_config import load_manager_config
from analyze import Analyzer
from execute import Executor
from knowledge import Knowledge, SystemState
from monitor import Monitor
from plan import Planner
# from managing_bridge import ManagingBridge  # TCP bridge (desativado)
# from managing_client import ManagingClient  # HTTP polling (desativado)
from managing_ws_client import ManagingWsClient


def main() -> None:
    manager_cfg = load_manager_config()

    knowledge = Knowledge(
        adaptation_options=manager_cfg["adaptation_options"],
        situation_strategy_map=dict(manager_cfg["plan_options"]) or None,
    )

    api.start(port=8001)
    api.wait_for_dashboard()        # espera GUI conectar antes de tudo

    import time
    time.sleep(1.5)                 # dá tempo ao browser iniciar o fragment polling

    # bridge  = ManagingBridge()             # TCP bridge (desativado)
    # client  = ManagingClient()             # HTTP polling (desativado)
    client          = ManagingWsClient()    # só agora conecta ao managing
    monitor         = Monitor()
    analyzer        = Analyzer(knowledge)
    planner         = Planner(knowledge)
    executor        = Executor(client)
    state           = SystemState()
    active_strategy: str | None = None

    print("[Manager] Aguardando percepcoes do managing...\n")

    while True:
        msg = client.get_perception(timeout=30.0)
        if msg is None:
            print("[Manager] Nenhuma percepcao recebida. Aguardando...")
            continue

        print(f"[Manager] Perception recebida — ep={msg.get('episode')} step={msg.get('step')} reward={msg.get('reward', 0):.4f}")

        # state    = monitor.update(msg, state)    # M
        # state    = analyzer.analyze(state)       # A
        # strategy = planner.plan(state)           # P

        # if strategy != active_strategy:
        #     print(f"[Manager] Enviando comando: {strategy}")
        #     executor.execute(strategy)           # E
        #     active_strategy = strategy

        api.update_state({
            "perception": msg,
            "step":       msg.get("step"),
            "episode":    msg.get("episode"),
        })


if __name__ == "__main__":
    main()
