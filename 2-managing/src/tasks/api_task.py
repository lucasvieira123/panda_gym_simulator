from typing import Callable, List

import numpy as np

import api
from ._object_task import _ObjectTask


class APITask(_ObjectTask):
    """Executa waypoints recebidos via PUT /waypoints.

    Waypoint único:   {"waypoints": [x, y, z, gripper]}
    Sequência:        {"waypoints": [[x, y, z, g], [x, y, z, g], ...]}

    gripper: 1.0 = aberta, -1.0 = fechada.
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
        super().__init__(sim, get_ee_position, get_object_position, target_goal_cfg, object_cfg, task_cfg)
        _task = task_cfg or {}
        self.step_threshold = _task.get("phase_threshold", 0.02)
        self._waypoints: List[np.ndarray] = []
        self._current = 0

    def reset(self) -> None:
        self._waypoints = []
        self._current = 0
        super().reset()

    def compute_action(self) -> np.ndarray:
        if self._current >= len(self._waypoints):
            raw = api.get_waypoints()
            if raw is None:
                return np.zeros(4, dtype=np.float32)
            waypoints = raw["waypoints"]
            if isinstance(waypoints[0], (int, float)):
                waypoints = [waypoints]
            self._waypoints = [np.array(w, dtype=np.float32) for w in waypoints]
            self._current = 0
            print(f"[APITask] {len(self._waypoints)} waypoint(s) recebido(s)")

        ee_pos     = np.array(self.get_ee_position())
        target     = self._waypoints[self._current]
        target_pos = target[:3]
        gripper    = target[3]
        direction  = target_pos - ee_pos
        dist       = np.linalg.norm(direction)

        if dist < self.step_threshold:
            print(f"[APITask] Waypoint {self._current + 1}/{len(self._waypoints)} concluído")
            self._current += 1
            if self._current >= len(self._waypoints):
                print("[APITask] Sequência concluída. Aguardando próximo comando...")
                return np.zeros(4, dtype=np.float32)
            target     = self._waypoints[self._current]
            target_pos = target[:3]
            gripper    = target[3]
            direction  = target_pos - ee_pos
            dist       = np.linalg.norm(direction)

        if dist > 0:
            direction = direction / dist

        return np.array([direction[0], direction[1], direction[2], gripper], dtype=np.float32)
