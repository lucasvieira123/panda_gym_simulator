from knowledge import Knowledge, SystemState


class Planner:
    def __init__(self, knowledge: Knowledge) -> None:
        self.knowledge = knowledge

    def plan(self, state: SystemState) -> str:
        new_strategy = self._select_strategy(state)

        if new_strategy != state.current_strategy:
            print(
                f"\n[MAPE-K | Plan] Situacao: '{state.current_situation}' "
                f"| Adaptacao: {state.current_strategy} -> {new_strategy}\n"
            )
            state.current_strategy = new_strategy

        return new_strategy

    def _select_strategy(self, state: SystemState) -> str:
        return self.knowledge.situation_strategy_map.get(state.current_situation, "PUSH")
