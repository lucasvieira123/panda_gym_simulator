from typing import Callable

import numpy as np

from ._object_task import _ObjectTask

_PHASE_LIFT           = 0  # sobe acima da box
_PHASE_ABOVE_APPROACH = 1  # move horizontal para cima do approach (altura segura)
_PHASE_APPROACH       = 2  # desce reto até a posição de empurrão
_PHASE_PUSH           = 3  # empurra em direção ao goal


class PushTask(_ObjectTask):
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
        self.approach_offset = _task.get("approach_offset", 0.05)
        self.approach_height = _task.get("approach_height", 0.1)
        self.phase_threshold = _task.get("phase_threshold", 0.02)
        self.push_speed      = _task.get("push_speed", 0.3)
        self._phase       = _PHASE_ABOVE_APPROACH  # primeiro goal não precisa de lift
        self._lift_target = None

    def reset(self) -> None:
        self._phase       = _PHASE_ABOVE_APPROACH
        self._lift_target = None
        super().reset()

    def _on_goal_advanced(self) -> None:
        self._phase       = _PHASE_LIFT
        self._lift_target = None

    # ── action ───────────────────────────────────────────────────────────────

    def compute_action(self) -> np.ndarray:
        ee_pos  = np.array(self.get_ee_position())
        box_pos = np.array(self.get_object_position())

        # captura speed antes de qualquer transição de fase
        speed = self.push_speed if self._phase in (_PHASE_APPROACH, _PHASE_PUSH) else 1.0

        push_dir_normalized = _normalized(self.goal - box_pos)
        approach_pos        = box_pos - push_dir_normalized * self.approach_offset
        above_approach      = np.array([approach_pos[0], approach_pos[1], box_pos[2] + self.approach_height])

        if self._phase == _PHASE_LIFT:
            if self._lift_target is None:
                self._lift_target = np.array([ee_pos[0], ee_pos[1], box_pos[2] + self.approach_height])
            target = self._lift_target
            if np.linalg.norm(ee_pos - target) < self.phase_threshold:
                self._phase       = _PHASE_ABOVE_APPROACH
                self._lift_target = None

        elif self._phase == _PHASE_ABOVE_APPROACH:
            target = above_approach
            if np.linalg.norm(ee_pos - target) < self.phase_threshold:
                self._phase = _PHASE_APPROACH

        elif self._phase == _PHASE_APPROACH:
            target = approach_pos
            if np.linalg.norm(ee_pos - target) < self.phase_threshold:
                self._phase = _PHASE_PUSH

        else:  # _PHASE_PUSH
            target = self.goal
            if self._goal_mode != "options" and self._goal_reached() and not self._all_done():
                self._advance_goal()  # → _on_goal_advanced → _PHASE_LIFT

        direction = _normalized(target - ee_pos) * speed
        gripper   = np.array([0.0], dtype=np.float32)
        return np.concatenate([direction, gripper]).astype(np.float32)


def _normalized(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 0 else np.zeros_like(v)
