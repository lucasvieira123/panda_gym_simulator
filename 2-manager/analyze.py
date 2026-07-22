from knowledge import Knowledge, SystemState


class Analyzer:
    def __init__(self, knowledge: Knowledge) -> None:
        self.knowledge = knowledge

    def analyze(self, state: SystemState) -> SystemState:
        state.current_situation = self._classify_situation(state)
        return state

    def _classify_situation(self, state: SystemState) -> str:
        context = state.to_eval_dict()
        for situation, expression in self.knowledge.adaptation_options.items():
            try:
                if eval(expression, {"__builtins__": {}}, context):
                    return situation
            except Exception:
                pass
        return "unanticipated"
