from typing import Callable

import numpy as np

from ._goal_task import _GoalTask


class ReachTask(_GoalTask):
    """Move o end-effector até um ou mais goals, sem manipular objeto."""

    def __init__(
        self,
        sim,
        get_ee_position: Callable[[], np.ndarray],
        target_goal_cfg: dict,
        task_cfg: dict = None,
        object_cfg: dict = None,
    ) -> None:
        super().__init__(sim, get_ee_position, target_goal_cfg, task_cfg, object_cfg)

    # ── panda_gym interface ──────────────────────────────────────────────────

    def get_obs(self) -> np.ndarray:
        return np.array([], dtype=np.float32)

    def get_achieved_goal(self) -> np.ndarray:
        return np.array(self.get_ee_position(), dtype=np.float32)

    # ── action ───────────────────────────────────────────────────────────────

    def compute_action(self) -> np.ndarray:
        ee_pos    = np.array(self.get_ee_position())
        direction = self.goal - ee_pos
        dist      = np.linalg.norm(direction)
        if dist > 0:
            direction = direction / dist

        if self._goal_mode != "options" and self._goal_reached() and not self._all_done():
            self._advance_goal()

        gripper = np.array([0.0], dtype=np.float32)
        return np.concatenate([direction, gripper]).astype(np.float32)
