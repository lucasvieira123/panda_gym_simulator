class Executor:
    def __init__(self, client) -> None:
        self._client = client

    def send_continue(self) -> None:
        self._client.send_command({"action": "continue"})

    def send_adapt(self, asm_scenario_name: str) -> None:
        # asm_scenario_name e.g. "retry_grasp" → managing recebe como task name
        managing_task = asm_scenario_name.upper()
        self._client.send_command({"action": "adapt", "to": managing_task})

    def send_transition(self, asm_scenario_name: str) -> None:
        # traduz cenário ASM para estado managing: "lift_object" → "LIFT_OBJECT"
        managing_state = asm_scenario_name.upper()
        self._client.send_command({"action": "transition", "to": managing_state})
