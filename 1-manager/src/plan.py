import re

from asm_loader import Asm
from knowledge import SystemState
from ts import ts


class Planner:
    def __init__(self, asm: Asm) -> None:
        self._asm = asm

    def plan(self, state: SystemState) -> str:
        scenario = state.matched_scenario
        if scenario.type == "evolutionary":
            # The managed system knows the candidate's action (e.g. APPLY_VACUUM_ASSIST),
            # not the name of a scenario created by DejaVu
            strategy = re.sub(r"\(.*?\)", "", scenario.do).strip().upper()
        else:
            # Adaptive scenarios are managed tasks with the scenario's name (RETRY_GRASP, SAFE_ABORT)
            strategy = scenario.key.upper()
        print(f"[{ts()}][Planner] situacao={scenario.name}  strategy={strategy}")
        return strategy
