from ._sensor import _Sensor


class PredefinedTargetGoalSensor(_Sensor):
    """
    Retorna a posição do target goal predefinida no target_goal config.
    Não consulta a simulação em tempo de execução.
    """

    def sense(self, simulation, robot, environment, obs: dict) -> dict:
        return {
            "target_goal": self.configs["target_goal"]
        }