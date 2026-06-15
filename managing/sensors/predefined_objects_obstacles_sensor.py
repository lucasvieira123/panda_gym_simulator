from ._sensor import _Sensor


class LiveObjectsObstaclesSensor(_Sensor):
    """
    Retorna objetos e obstáculos presentes na cena com suas posições atuais.
    Consulta o EnvironmentManager em tempo de execução — reflete adições,
    remoções e movimentos feitos via API.
    """

    def __init__(self, configs: dict, env) -> None:
        super().__init__(configs)
        self._env = env

    def sense(self, simulation, robot, environment, obs: dict) -> dict:
        return {
            "objects":   self._env.get_objects(),
            "obstacles": self._env.get_obstacles(),
        }
