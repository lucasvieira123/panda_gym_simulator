from ._sensor import _Sensor


class InitialRobotSensor(_Sensor):
    """
    Retorna as informações estáticas do robô definidas no environment config.
    Não consulta a simulação em tempo de execução.
    """

    def sense(self, simulation, robot, environment, obs: dict) -> dict:
        robot_cfg = self.configs["environment"].get("robot", {})
        return {
            "robot": {
                "control_type":  robot_cfg.get("control_type"),
                "block_gripper": robot_cfg.get("block_gripper"),
                "base_position": robot_cfg.get("base_position"),
            }
        }