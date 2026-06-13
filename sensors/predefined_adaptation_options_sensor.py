from ._sensor import _Sensor


class PredefinedAdaptationOptionsSensor(_Sensor):
    """
    Retorna as adaptation options predefinidas do adaptation_options config.
    Não consulta a simulação em tempo de execução.
    """

    def sense(self, simulation, robot, environment, obs: dict) -> dict:
        return {
            "adaptation_options": self.configs["adaptation_options"]
        }