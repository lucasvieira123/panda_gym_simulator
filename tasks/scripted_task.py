from typing import Callable, List

import numpy as np

from ._object_task import _ObjectTask


class ScriptedTask(_ObjectTask):
    """Executa uma sequência de waypoints pré-definidos.

    Cada waypoint é [x, y, z, gripper] onde gripper: 1.0=aberta, -1.0=fechada.
    """

    def __init__(
        self,
        sim,
        get_ee_position: Callable[[], np.ndarray],
        get_object_position: Callable[[], np.ndarray],
        target_goal_cfg: dict,
        object_cfg: dict,
        waypoints: List[List[float]],
        task_cfg: dict = None,
    ) -> None:
        super().__init__(sim, get_ee_position, get_object_position, target_goal_cfg, object_cfg, task_cfg)
        _task = task_cfg or {}
        self.step_threshold    = _task.get("phase_threshold", 0.02)
        self._waypoints        = [np.array(w, dtype=np.float32) for w in waypoints]
        self._current_waypoint = 0

    def reset(self) -> None:
        self._current_waypoint = 0
        super().reset()

    # ── action ───────────────────────────────────────────────────────────────

    def compute_action(self) -> np.ndarray:
        if self._current_waypoint >= len(self._waypoints):
            return np.zeros(4, dtype=np.float32)

        ee_pos     = np.array(self.get_ee_position())
        target     = self._waypoints[self._current_waypoint]
        target_pos = target[:3]
        gripper    = target[3]

        direction = target_pos - ee_pos
        dist      = np.linalg.norm(direction)

        if dist < self.step_threshold:
            print(f"[Script] Waypoint {self._current_waypoint + 1}/{len(self._waypoints)} concluído")
            self._current_waypoint += 1
            if self._current_waypoint >= len(self._waypoints):
                return np.zeros(4, dtype=np.float32)
            target     = self._waypoints[self._current_waypoint]
            target_pos = target[:3]
            gripper    = target[3]
            direction  = target_pos - ee_pos
            dist       = np.linalg.norm(direction)

        if dist > 0:
            direction = direction / dist

        return np.array([direction[0], direction[1], direction[2], gripper], dtype=np.float32)
