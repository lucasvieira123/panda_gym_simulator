from ._sensor import _Sensor


class LiveRobotSensor(_Sensor):
    """
    Retorna as informações do robô consultando a simulação em tempo de execução.
    base_position é lida do PyBullet — reflete movimentos feitos via API.
    control_type e block_gripper não mudam em runtime e vêm do config.
    """

    def sense(self, simulation, robot, environment, obs: dict) -> dict:
        robot_cfg = self.configs["environment"].get("robot", {})
        return {
            "robot": {
                "control_type":  robot_cfg.get("control_type"),
                "block_gripper": robot_cfg.get("block_gripper"),
                "base_position": simulation.get_base_position("panda").tolist(),
            }
        }