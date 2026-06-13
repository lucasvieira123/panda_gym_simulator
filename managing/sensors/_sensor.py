from abc import ABC, abstractmethod


class _Sensor(ABC):
    def __init__(self, configs: dict) -> None:
        self.configs = configs

    @abstractmethod
    def sense(self, simulation, robot, environment, obs: dict) -> dict:
        """Recebe simulation, robot, environment e obs e retorna um dict com os parâmetros derivados."""
        ...
