from .obstacles_in_path_sensor import ObstaclesInPathSensor
from .predefined_adaptation_options_sensor import PredefinedAdaptationOptionsSensor
from .predefined_objects_obstacles_sensor import InitialObjectsObstaclesSensor
from .predefined_robot_sensor import InitialRobotSensor
from .predefined_scene_sensor import InitialSceneSensor
from .predefined_scripts_sensor import PredefinedScriptsSensor
from .predefined_situations_sensor import PredefinedSituationsSensor
from .predefined_target_goal_sensor import PredefinedTargetGoalSensor


class SensorPipeline:
    """
    Gerencia dois grupos de sensores:

    - Estáticos: leem apenas config, rodam uma vez no __init__ e ficam em cache.
    - Runtime:   precisam de obs/simulação, rodam a cada chamada de sense().

    Uso:
        pipeline = SensorPipeline(configs)

        # dentro do loop de steps
        perception = pipeline.sense(simulation, robot, environment, obs)
        # perception contém dados estáticos + runtime mesclados
    """

    def __init__(self, configs: dict) -> None:
        self._static_data: dict = {}
        for sensor in [
            InitialObjectsObstaclesSensor(configs),
            InitialSceneSensor(configs),
            InitialRobotSensor(configs),
            PredefinedSituationsSensor(configs),
            PredefinedAdaptationOptionsSensor(configs),
            PredefinedTargetGoalSensor(configs),
            PredefinedScriptsSensor(configs),
        ]:
            self._static_data.update(sensor.sense(None, None, None, {}))

        self._runtime_sensors = [
            ObstaclesInPathSensor(configs),
        ]

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
