from abc import ABC, abstractmethod

from config_loader import load_config


class _Sensor(ABC):
    def __init__(self) -> None:
        self.configs = load_config()

    @abstractmethod
    def sense(self, simulation, robot, environment, obs: dict) -> dict:
        """Recebe simulation, robot, environment e obs e retorna um dict com os parâmetros derivados."""
        ...