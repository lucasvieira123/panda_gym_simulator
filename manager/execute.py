from managing_bridge import ManagingBridge


class Executor:
    def __init__(self, bridge: ManagingBridge) -> None:
        self._bridge = bridge

    def execute(self, strategy: str) -> None:
        self._bridge.send_command(strategy)
