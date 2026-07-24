from typing import Callable

import numpy as np

from .._object_task import _ObjectTask
from utils import ts

# ASM — SAFE_ABORT
# Given : max_retries_exceeded == true  OR  safety_violation == true
# When  : abort_triggered == true
# Do    : safe_abort()  — recua para posição neutra e abre garra
# Then  : robot_at_safe_position == true, gripper_width_cm >= 6.0

_PHASE_RISE   = 0   # sobe para altura segura
_PHASE_CENTER = 1   # move para posição neutra (0, 0, safe_height)
_PHASE_DONE   = 2   # postcondição satisfeita


class AbortTask(_ObjectTask):

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
        _cfg = task_cfg or {}
        self.safe_height  = _cfg.get("safe_height",  0.30)
        self.neutral_pos  = np.array(_cfg.get("neutral_pos", [0.0, 0.0, 0.30]), dtype=np.float32)
        self.threshold    = _cfg.get("threshold",    0.03)
        self._phase       = _PHASE_RISE

    def reset(self) -> None:
        self.reset_phase()
        super().reset()

    def reset_phase(self) -> None:
        self._phase = _PHASE_RISE

    def compute_action(self) -> np.ndarray:
        ee_pos  = np.array(self.get_ee_position())
        gripper = 1.0  # abre garra imediatamente

        if self._phase == _PHASE_RISE:
            target = np.array([ee_pos[0], ee_pos[1], self.safe_height])
            if abs(ee_pos[2] - self.safe_height) < self.threshold:
                self._phase = _PHASE_CENTER

        elif self._phase == _PHASE_CENTER:
            target = self.neutral_pos
            if np.linalg.norm(ee_pos - self.neutral_pos) < self.threshold:
                print(f"[{ts()}][SafeAbort] Postcondição: robot_at_safe_position == true ✓")
                self._phase = _PHASE_DONE

        else:
            target = ee_pos

        direction = target - ee_pos
        dist      = np.linalg.norm(direction)
        if dist > 0:
            direction = direction / dist

        return np.array([direction[0], direction[1], direction[2], gripper], dtype=np.float32)

    @property
    def done(self) -> bool:
        return self._phase == _PHASE_DONE
