from .knowledge import Knowledge, Situation, Strategy, SystemState


class Planner:
    """
    Mapeia Situation → Strategy usando regras determinísticas.

    Regras:
      NORMAL              → mantém estratégia atual (se válida) ou volta para PUSH
      PLANNED_OBSTACLE    → PICK_AND_PLACE_OVER
      UNPLANNED_*         → RECOVER
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
        situation = state.current_situation
        current = state.current_strategy

        if situation == Situation.PLANNED_OBSTACLE:
            return Strategy.PICK_AND_PLACE_OVER

        if situation in (Situation.UNPLANNED_STAGNATION, Situation.UNPLANNED_COLLISION):
            return Strategy.RECOVER

        # NORMAL: se veio de RECOVER, volta para PUSH para recomeçar limpo
        if situation == Situation.NORMAL:
            if current == Strategy.RECOVER:
                return Strategy.PUSH
            # mantém PUSH ou PICK_OVER se já estava neles e está normal
            if current in (Strategy.PUSH, Strategy.PICK_AND_PLACE_OVER):
                return current
            return Strategy.PUSH

        return current
