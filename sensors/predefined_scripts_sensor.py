from ._sensor import _Sensor


class PredefinedScriptsSensor(_Sensor):
    """
    Retorna os scripts predefinidos do scripts config.
    Não consulta a simulação em tempo de execução.
    """

    def sense(self, simulation, robot, environment, obs: dict) -> dict:
        return {
            "scripts": self.configs["scripts"]
        }