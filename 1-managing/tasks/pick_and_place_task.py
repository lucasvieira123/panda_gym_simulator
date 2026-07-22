from typing import Callable

import numpy as np

from ._object_task import _ObjectTask

_PHASE_ABOVE_BOX  = 0
_PHASE_GRASP      = 1
_PHASE_LIFT       = 2
_PHASE_ABOVE_GOAL = 3
_PHASE_PLACE      = 4
_PHASE_RELEASE    = 5


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
        self.grasp_height_offset  = _task.get("grasp_height_offset",  0.01)
        self.approach_height      = _task.get("approach_height",       0.12)
        self.phase_threshold      = _task.get("phase_threshold",       0.02)
        self.slow_radius          = _task.get("slow_radius",           0.10)
        self.min_speed            = _task.get("min_speed",             0.06)
        self.release_early_offset = _task.get("release_early_offset",  0.04)
        self._phase               = _PHASE_ABOVE_BOX
        self._lift_target         = None
        self._retract_target      = None

    def reset(self) -> None:
        self._phase          = _PHASE_ABOVE_BOX
        self._lift_target    = None
        self._retract_target = None
        super().reset()

    def _on_goal_advanced(self) -> None:
        self._phase          = _PHASE_ABOVE_BOX
        self._lift_target    = None
        self._retract_target = None

    # ── helpers ───────────────────────────────────────────────────────────────

    def _ramp(self, dist: float) -> float:
        """Quadratic speed ramp: full speed far away, very slow near target."""
        if dist >= self.slow_radius:
            return 1.0
        ratio = dist / self.slow_radius          # 0..1
        return max(self.min_speed, ratio * ratio) # quadratic → drops fast near zero

    # ── action ───────────────────────────────────────────────────────────────

    def compute_action(self) -> np.ndarray:
        ee_pos  = np.array(self.get_ee_position())
        box_pos = np.array(self.get_object_position())
        goal    = np.array(self.goal)

        # All targets expressed as EE positions in world space
        above_box    = box_pos + np.array([0.0, 0.0, self.approach_height])
        grasp_pos    = box_pos + np.array([0.0, 0.0, self.grasp_height_offset])
        # place_target: EE height that puts box centre exactly at goal height
        place_target = goal    + np.array([0.0, 0.0, self.grasp_height_offset])
        above_goal   = place_target + np.array([0.0, 0.0, self.approach_height])

        target  = ee_pos   # default: hold position
        gripper = 1.0
        speed   = 1.0

        if self._phase == _PHASE_ABOVE_BOX:
            target  = above_box
            gripper = 1.0
            if np.linalg.norm(ee_pos - target) < self.phase_threshold:
                self._phase = _PHASE_GRASP

        elif self._phase == _PHASE_GRASP:
            target  = grasp_pos
            gripper = 1.0
            dist    = np.linalg.norm(ee_pos - target)
            speed   = self._ramp(dist)
            # também exige descida real até a altura de agarramento,
            # pois chegando de cima o braço pode satisfazer o threshold
            # ainda 1-2 cm acima da box e fechar a garra no ar
            at_grasp_height = ee_pos[2] <= grasp_pos[2] + self.phase_threshold / 4
            if dist < self.phase_threshold and at_grasp_height:
                gripper              = -1.0
                self._lift_target    = ee_pos.copy() + np.array([0.0, 0.0, self.approach_height])
                self._phase          = _PHASE_LIFT

        elif self._phase == _PHASE_LIFT:
            target  = self._lift_target
            gripper = -1.0
            if np.linalg.norm(ee_pos - target) < self.phase_threshold:
                self._phase = _PHASE_ABOVE_GOAL

        elif self._phase == _PHASE_ABOVE_GOAL:
            target  = above_goal
            gripper = -1.0
            if np.linalg.norm(ee_pos - target) < self.phase_threshold:
                self._phase = _PHASE_PLACE

        elif self._phase == _PHASE_PLACE:
            target  = place_target
            gripper = -1.0
            dist    = np.linalg.norm(ee_pos - target)
            speed   = self._ramp(dist)
            # open gripper early — box drops the last centimetres under gravity
            if dist < self.release_early_offset:
                self._retract_target = above_goal.copy()
                self._phase          = _PHASE_RELEASE

        else:  # _PHASE_RELEASE
            target  = self._retract_target
            gripper = 1.0   # garra aberta — box já solta
            if np.linalg.norm(ee_pos - target) < self.phase_threshold:
                if self._goal_mode != "options" and not self._all_done():
                    self._advance_goal()

        direction = target - ee_pos
        dist_to_target = np.linalg.norm(direction)
        if dist_to_target > 0:
            direction = direction / dist_to_target * speed

        return np.array([direction[0], direction[1], direction[2], gripper], dtype=np.float32)
