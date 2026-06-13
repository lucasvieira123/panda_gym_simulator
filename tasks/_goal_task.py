from abc import abstractmethod
from typing import Any, Callable, Dict

import numpy as np
from panda_gym.utils import distance

from ._task import _Task

_COLOR_ACTIVE  = [0.1, 0.9, 0.1, 0.8]
_COLOR_PENDING = [0.9, 0.5, 0.1, 0.5]
_COLOR_DONE    = [0.5, 0.5, 0.5, 0.3]


class _GoalTask(_Task):
    """Base para tasks orientadas a goals.

    Responsabilidades:
    - Gerenciamento de goals (options / sequence / set)
    - Cores das spheres visuais
    - Interface panda_gym (is_success, compute_reward)

    Subclasses devem implementar:
    - get_achieved_goal() → posição atual relevante (objeto ou EE)
    - get_obs()
    - compute_action()
    """

    def __init__(
        self,
        sim,
        get_ee_position: Callable[[], np.ndarray],
        target_goal_cfg: dict,
        task_cfg: dict = None,
        object_cfg: dict = None,
    ) -> None:
        super().__init__(sim)
        self.get_ee_position    = get_ee_position
        _task                   = task_cfg or {}
        self.reward_type        = _task.get("reward_type", "dense")
        self.distance_threshold = _task.get("distance_threshold", 0.05)

        self._goal_mode, self._goals = _parse_goals(target_goal_cfg)
        self._current_idx = 0
        self._completed: set = set()

        _obj = object_cfg or {}
        self._object_name = _obj.get("name")
        self._object_initial_position = (
            np.array(_obj["initial_position"], dtype=np.float32)
            if "initial_position" in _obj else None
        )

    # ── reset ────────────────────────────────────────────────────────────────

    def reset(self) -> None:
        self._current_idx = 0
        self._completed   = set()
        self._reset_object()
        self.goal = self._active_goal()
        self._refresh_sphere_colors()

    def _reset_object(self) -> None:
        if not self._object_name or self._object_initial_position is None:
            return
        self.sim.set_base_pose(
            self._object_name,
            self._object_initial_position,
            np.array([0.0, 0.0, 0.0, 1.0]),
        )
        body_id = self.sim._bodies_idx.get(self._object_name)
        if body_id is not None:
            self.sim.physics_client.resetBaseVelocity(
                body_id, [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
            )

    # ── goal management ──────────────────────────────────────────────────────

    def _active_goal(self) -> np.ndarray:
        if self._goal_mode == "options":
            pos = np.array(self.get_achieved_goal())
            return min(self._goals, key=lambda g: np.linalg.norm(g - pos))
        if self._goal_mode == "sequence":
            idx = min(self._current_idx, len(self._goals) - 1)
            return self._goals[idx]
        # set
        unvisited = [g for i, g in enumerate(self._goals) if i not in self._completed]
        if not unvisited:
            return self._goals[-1]
        pos = np.array(self.get_achieved_goal())
        return min(unvisited, key=lambda g: np.linalg.norm(g - pos))

    def _goal_reached(self) -> bool:
        return float(np.linalg.norm(np.array(self.get_achieved_goal()) - self.goal)) < self.distance_threshold

    def _advance_goal(self) -> None:
        if self._goal_mode == "sequence":
            self._current_idx += 1
        elif self._goal_mode == "set":
            pos = np.array(self.get_achieved_goal())
            for i, g in enumerate(self._goals):
                if i not in self._completed and np.linalg.norm(pos - g) < self.distance_threshold:
                    self._completed.add(i)
                    break

        self.goal = self._active_goal()
        self._on_goal_advanced()
        self._refresh_sphere_colors()

    def _on_goal_advanced(self) -> None:
        pass

    def _all_done(self) -> bool:
        if self._goal_mode == "sequence":
            return self._current_idx >= len(self._goals)
        if self._goal_mode == "set":
            return len(self._completed) == len(self._goals)
        return False

    # ── sphere colors ────────────────────────────────────────────────────────

    def _active_goal_idx(self) -> int:
        for i, g in enumerate(self._goals):
            if np.array_equal(g, self.goal):
                return i
        return 0

    def _is_completed(self, i: int) -> bool:
        if self._goal_mode == "sequence":
            return i < self._current_idx
        if self._goal_mode == "set":
            return i in self._completed
        return False

    def _set_sphere_rgba(self, name: str, color: list) -> None:
        body_id = self.sim._bodies_idx.get(name)
        if body_id is not None:
            self.sim.physics_client.changeVisualShape(body_id, -1, rgbaColor=color)

    def _refresh_sphere_colors(self) -> None:
        active_idx = self._active_goal_idx()
        for i in range(len(self._goals)):
            name = "target" if i == 0 else f"target_{i}"
            if i == active_idx:
                self._set_sphere_rgba(name, _COLOR_ACTIVE)
            elif self._is_completed(i):
                self._set_sphere_rgba(name, _COLOR_DONE)
            else:
                self._set_sphere_rgba(name, _COLOR_PENDING)

    # ── panda_gym interface ──────────────────────────────────────────────────

    @abstractmethod
    def get_achieved_goal(self) -> np.ndarray: ...

    def is_success(self, achieved_goal: np.ndarray, desired_goal: np.ndarray, info: Dict[str, Any] = {}) -> np.ndarray:
        if self._goal_mode == "options":
            return np.array(
                any(float(distance(achieved_goal, g)) < self.distance_threshold for g in self._goals),
                dtype=bool,
            )
        return np.array(self._all_done(), dtype=bool)

    def compute_reward(self, achieved_goal: np.ndarray, desired_goal: np.ndarray, info: Dict[str, Any] = {}) -> np.ndarray:
        d = distance(achieved_goal, self.goal)
        if self.reward_type == "sparse":
            return -np.array(d > self.distance_threshold, dtype=np.float32)
        return -d.astype(np.float32)


# ── helpers ───────────────────────────────────────────────────────────────────

def _parse_goals(target_goal_cfg: dict):
    for mode in ("goal_options", "goal_sequence", "goal_set"):
        if mode in target_goal_cfg:
            key = mode.replace("goal_", "")
            goals = [np.array(p, dtype=np.float32) for p in target_goal_cfg[mode]]
            return key, goals
    raise ValueError("target_goal_cfg deve conter goal_options, goal_sequence ou goal_set")
