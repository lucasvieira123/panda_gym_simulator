from typing import Callable

import numpy as np

from ._goal_task import _GoalTask


class _ObjectTask(_GoalTask):
    """Base para tasks que manipulam um objeto físico.

    Estende _GoalTask adicionando:
    - Rastreamento de posição do objeto
    - get_obs / get_achieved_goal baseados no objeto
    """

    def __init__(
        self,
        sim,
        get_ee_position: Callable[[], np.ndarray],
        get_object_position: Callable[[], np.ndarray],
        target_goal_cfg: dict,
        object_cfg: dict,
        task_cfg: dict = None,
    ) -> None:
        super().__init__(sim, get_ee_position, target_goal_cfg, task_cfg, object_cfg)
        self.get_object_position = get_object_position

    # ── panda_gym interface ──────────────────────────────────────────────────

    def get_obs(self) -> np.ndarray:
        return np.array(self.get_object_position(), dtype=np.float32)

    def get_achieved_goal(self) -> np.ndarray:
        return np.array(self.get_object_position(), dtype=np.float32)
