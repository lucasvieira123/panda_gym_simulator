from typing import Callable

import numpy as np

from ._object_task import _ObjectTask


class HoldTask(_ObjectTask):
    def __init__(
        self,
        sim,
        get_ee_position: Callable[[], np.ndarray],
        get_object_position: Callable[[], np.ndarray],
        target_goal_cfg: dict,
        object_cfg: dict,
        task_cfg: dict = None,
    ) -> None:
        super().__init__(sim, get_ee_position, get_object_position, target_goal_cfg, object_cfg, task_cfg)

    def compute_action(self) -> np.ndarray:
        return np.zeros(4, dtype=np.float32)
