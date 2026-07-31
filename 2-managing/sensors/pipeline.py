from .finger_contact_sensor import FingerContactSensor
from .obstacles_in_path_sensor import ObstaclesInPathSensor
from .predefined_objects_obstacles_sensor import LiveObjectsObstaclesSensor
from .predefined_robot_sensor import LiveRobotSensor
from .predefined_scene_sensor import InitialSceneSensor
from .predefined_scripts_sensor import PredefinedScriptsSensor
from .predefined_target_goal_sensor import LiveTargetGoalSensor


class SensorPipeline:
    """
    Gerencia dois grupos de sensores:

    - Estáticos: leem apenas config, rodam uma vez no __init__ e ficam em cache.
    - Runtime:   precisam de obs/simulação, rodam a cada chamada de sense().

    Uso:
        pipeline = SensorPipeline(configs, env)

        # dentro do loop de steps
        perception = pipeline.sense(simulation, robot, environment, obs)
        # perception contém dados estáticos + runtime mesclados
    """

    def __init__(self, configs: dict, env, sim=None) -> None:
        self._static_data: dict = {}
        for sensor in [
            InitialSceneSensor(configs),
            PredefinedScriptsSensor(configs),
        ]:
            self._static_data.update(sensor.sense(None, None, None, {}))

        self._runtime_sensors = [
            ObstaclesInPathSensor(configs, env),
            LiveObjectsObstaclesSensor(configs, env),
            LiveTargetGoalSensor(configs, env),
            LiveRobotSensor(configs),
        ]

        if sim is not None:
            self._runtime_sensors.append(FingerContactSensor(configs, sim))

    @property
    def static(self) -> dict:
        """Dados estáticos pré-computados (sem depender de obs)."""
        return self._static_data

    def sense(self, simulation, robot, environment, obs: dict) -> dict:
        """Roda sensores runtime e retorna percepção completa (estático + runtime)."""
        runtime_data: dict = {}
        for sensor in self._runtime_sensors:
            runtime_data.update(sensor.sense(simulation, robot, environment, obs))
        return {**self._static_data, **runtime_data}
