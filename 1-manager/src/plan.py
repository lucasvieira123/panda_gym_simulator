from asm_loader import Asm
from knowledge import SystemState
from ts import ts


class Planner:
    def __init__(self, asm: Asm) -> None:
        self._asm = asm

    def plan(self, state: SystemState) -> str:
        scenario = state.matched_scenario
        strategy = scenario.key.upper()
        print(f"[{ts()}][Planner] situacao={scenario.name}  strategy={strategy}")
        return strategy
