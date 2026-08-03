from expression.action_expression import ActionExpression
from expression.conditional_expression import ConditionalExpression
from typing import Optional

from scenario.scenario import Scenario

class DiagnosedScenario(Scenario):
    """
    Diagnosed Scenario: identical to Scenario, inherits all logic.
    """

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["type"] = self.__class__.__name__ # Ensure correct type
        return d
