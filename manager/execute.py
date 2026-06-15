class Executor:
    def __init__(self, client) -> None:
        self._client = client

    def execute(self, strategy: str) -> None:
        self._client.send_command(strategy)
