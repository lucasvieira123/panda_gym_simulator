from ._sensor import _Sensor


class InitialSceneSensor(_Sensor):
    """
    Retorna as informações estáticas da cena definidas no environment config.
    Não consulta a simulação em tempo de execução.
    """

    def sense(self, simulation, robot, environment, obs: dict) -> dict:
        table = self.configs["environment"].get("scene", {}).get("table", {})
        return {
            "scene": {
                "table": {
                    "length":            table.get("length"),
                    "width":             table.get("width"),
                    "height":            table.get("height"),
                    "x_offset":          table.get("x_offset"),
                    "lateral_friction":  table.get("lateral_friction"),
                    "spinning_friction": table.get("spinning_friction"),
                }
            }
        }