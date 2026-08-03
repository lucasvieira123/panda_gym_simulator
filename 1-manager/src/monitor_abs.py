from abc import ABC, abstractmethod

from knowledge import SystemState


class MonitorAbs(ABC):
    @abstractmethod
    def update(self, msg: dict, state: SystemState) -> SystemState: ...
