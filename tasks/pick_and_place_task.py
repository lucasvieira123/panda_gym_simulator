from typing import Callable

import numpy as np

from ._object_task import _ObjectTask

_PHASE_ABOVE_BOX  = 0
_PHASE_GRASP      = 1
_PHASE_LIFT       = 2
_PHASE_ABOVE_GOAL = 3
_PHASE_PLACE      = 4


class PickAndPlaceTask(_ObjectTask):
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
        _task = task_cfg or {}
        self.grasp_height_offset = _task.get("grasp_height_offset", 0.01)
        self.approach_height     = _task.get("approach_height", 0.1)
        self.phase_threshold     = _task.get("phase_threshold", 0.02)
        self._phase              = _PHASE_ABOVE_BOX
        self._lift_target        = None

    def reset(self) -> None:
        self._phase       = _PHASE_ABOVE_BOX
        self._lift_target = None
        super().reset()

    def _on_goal_advanced(self) -> None:
        self._phase       = _PHASE_ABOVE_BOX
        self._lift_target = None

    # ── action ───────────────────────────────────────────────────────────────

    def compute_action(self) -> np.ndarray:
        ee_pos   = np.array(self.get_ee_position())
        box_pos  = np.array(self.get_object_position())
        goal_pos = self.goal

        above_box  = box_pos  + np.array([0.0, 0.0, self.approach_height])
        grasp_pos  = box_pos  + np.array([0.0, 0.0, self.grasp_height_offset])
        above_goal = goal_pos + np.array([0.0, 0.0, self.approach_height])

        if self._phase == _PHASE_ABOVE_BOX:
            target  = above_box
            gripper = np.array([1.0])
            if np.linalg.norm(ee_pos - target) < self.phase_threshold:
                self._phase = _PHASE_GRASP

        elif self._phase == _PHASE_GRASP:
            target = grasp_pos
            if np.linalg.norm(ee_pos - target) < self.phase_threshold:
                gripper = np.array([-1.0])
                self._lift_target = ee_pos + np.array([0.0, 0.0, self.approach_height])
                self._phase = _PHASE_LIFT
            else:
                gripper = np.array([1.0])

        elif self._phase == _PHASE_LIFT:
            target  = self._lift_target
            gripper = np.array([-1.0])
            if np.linalg.norm(ee_pos - target) < self.phase_threshold:
                self._phase = _PHASE_ABOVE_GOAL

        elif self._phase == _PHASE_ABOVE_GOAL:
            target  = above_goal
            gripper = np.array([-1.0])
            if np.linalg.norm(ee_pos - target) < self.phase_threshold:
                self._phase = _PHASE_PLACE

        else:  # _PHASE_PLACE
            target  = goal_pos
            gripper = np.array([-1.0])
            if self._goal_mode != "options" and self._goal_reached() and not self._all_done():
                self._advance_goal()

        direction = target - ee_pos
        dist = np.linalg.norm(direction)
        if dist > 0:
            direction = direction / dist

        return np.concatenate([direction, gripper]).astype(np.float32)
