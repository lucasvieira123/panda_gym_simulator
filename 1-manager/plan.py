from asm_loader import Asm
from knowledge import SystemState


class Planner:
    def __init__(self, asm: Asm) -> None:
        self._asm = asm

    def plan(self, state: SystemState) -> str:
        scenario = state.matched_scenario
        strategy = scenario.key.upper()
        print(f"[Planner] situacao={scenario.name}  strategy={strategy}")
        return strategy
