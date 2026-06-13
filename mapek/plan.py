from .knowledge import Knowledge, Strategy, SystemState


class Planner:
    """
    Mapeia Situation → Strategy usando regras determinísticas.

    Regras:
      NORMAL           → PUSH
      PLANNED_OBSTACLE → PICK_AND_PLACE_OVER
    """

    def __init__(self, knowledge: Knowledge) -> None:
        self.knowledge = knowledge

    def plan(self, state: SystemState) -> Strategy:
        new_strategy = self._select_strategy(state)

        if new_strategy != state.current_strategy:
            print(
                f"\n[MAPE-K | Plan] Situação: '{state.current_situation.value}' "
                f"| Adaptação: {state.current_strategy.value} → {new_strategy.value}\n"
            )
            state.current_strategy = new_strategy

        return new_strategy

    def _select_strategy(self, state: SystemState) -> Strategy:
        return self.knowledge.situation_strategy_map.get(state.current_situation, Strategy.PUSH)
