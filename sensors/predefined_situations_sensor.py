from ._sensor import _Sensor


class PredefinedSituationsSensor(_Sensor):
    """
    Retorna as situações predefinidas do situations config.
    Não consulta a simulação em tempo de execução.
    """

    def sense(self, simulation, robot, environment, obs: dict) -> dict:
        return {
            "situations": self.configs["situations"]
        }