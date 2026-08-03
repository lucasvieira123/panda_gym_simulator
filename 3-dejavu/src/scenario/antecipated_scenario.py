from scenario.scenario import Scenario

class AntecipatedScenario(Scenario):

    """
    Antecipated Scenario: identical to ScenarioBDD, inherits all logic.
    """

    def to_dict(self) -> dict:
        d = super().to_dict()
        d["type"] = self.__class__.__name__ # Ensure correct type
        return d