from ._sensor import _Sensor


class InitialObjectsObstaclesSensor(_Sensor):
    """
    Retorna as informações estáticas de objetos e obstáculos definidas no environment config.
    Não consulta a simulação em tempo de execução.
    """

    def sense(self, simulation, robot, environment, obs: dict) -> dict:
        environment_cfg = self.configs["environment"]
        return {
            "objects":   self._read_bodies(environment_cfg.get("objects",   [])),
            "obstacles": self._read_bodies(environment_cfg.get("obstacles", [])),
        }

    def _read_bodies(self, bodies: list) -> dict:
        result = {}
        for body in bodies:
            result[body["name"]] = {
                "type":              body.get("type"),
                "size":              body.get("size"),
                "mass":              body.get("mass"),
                "color":             body.get("color"),
                "lateral_friction":  body.get("lateral_friction"),
                "spinning_friction": body.get("spinning_friction"),
            }
        return result