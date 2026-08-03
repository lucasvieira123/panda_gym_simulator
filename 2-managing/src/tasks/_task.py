from abc import abstractmethod

import numpy as np
from panda_gym.envs.core import Task


class _Task(Task):
    @abstractmethod
    def compute_action(self) -> np.ndarray: ...