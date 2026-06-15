from ._sensor import _Sensor


class LiveTargetGoalSensor(_Sensor):
    """
    Retorna tipo e targets com nome e posição atual do sim.
    Reflete movimentos feitos via API em tempo de execução.
    """

    def __init__(self, configs: dict, env) -> None:
        super().__init__(configs)
        self._env = env

    def sense(self, simulation, robot, environment, obs: dict) -> dict:
        goal_type = self.configs["target_goal"]["mode"]
        targets = [
            {
                "name":     name,
                "position": self._env.sim.get_base_position(name).tolist(),
            }
            for name in self._env._target_names
        ]
        return {
            "target_goal": {"type": goal_type, "targets": targets}
        }