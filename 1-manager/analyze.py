from asm_evaluator import AsmEvaluator
from knowledge import SystemState


class Analyzer:
    def __init__(self, asm_evaluator: AsmEvaluator) -> None:
        self._evaluator = asm_evaluator

    def analyze(self, state: SystemState) -> SystemState:
        context = state.to_eval_dict()

        # Passo 1 — identifica em que cenário ASM o managed está agora
        matched = self._evaluator.evaluate(context)
        state.current_asm_scenario = self._evaluator.current_node

        print(f"[Analyzer] ASM node={state.current_asm_scenario}  goal_status=", end="")

        if matched is None:
            state.goal_status = "not_applicable"
            state.matched_scenario = None
            print("not_applicable")
            return state

        if matched.type == "predefined":
            state.goal_status = "ok"
            state.matched_scenario = None
            print(f"ok  (scenario={matched.name})")
            return state

        # Passo 2 — cenário adaptativo correspondeu → violação de adaptation goal
        state.goal_status = "violated"
        state.matched_scenario = matched
        print(f"VIOLATED  → adaptation={matched.name}")
        return state
