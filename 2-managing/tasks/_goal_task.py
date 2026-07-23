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

        self._goal_mode, self._goal_names, self._goals = _parse_goals(target_goal_cfg)
        self._current_idx = 0
        self._completed: set = set()

        _obj = object_cfg or {}
        self._object_name = _obj.get("name")
        self._object_initial_position = (
            np.array(_obj["initial_position"], dtype=np.float32)
            if "initial_position" in _obj else None
        )

    # ── reset / refresh ──────────────────────────────────────────────────────

    def refresh_goal(self) -> None:
        """Recalcula o goal ativo a partir das posições atuais do sim.
        Chamar após mover um target via API."""
        self.goal = self._active_goal()
        self._refresh_sphere_colors()

    def set_goal_mode(self, mode: str) -> None:
        """Troca o modo de seleção de goal em tempo de execução.
        mode: 'options' | 'sequence' | 'set'  (sem prefixo 'goal_')
        """
        self._goal_mode   = mode.replace("goal_", "")
        self._current_idx = 0
        self._completed   = set()
        self.goal         = self._active_goal()
        self._refresh_sphere_colors()

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

    def _live_positions(self) -> list:
        return [np.array(self.sim.get_base_position(n), dtype=np.float32) for n in self._goal_names]

    def _active_goal(self) -> np.ndarray:
        live = self._live_positions()
        if self._goal_mode == "options":
            pos = np.array(self.get_achieved_goal())
            return min(live, key=lambda g: np.linalg.norm(g - pos))
        if self._goal_mode == "sequence":
            idx = min(self._current_idx, len(live) - 1)
            return live[idx]
        # set
        unvisited = [g for i, g in enumerate(live) if i not in self._completed]
        if not unvisited:
            return live[-1]
        pos = np.array(self.get_achieved_goal())
        return min(unvisited, key=lambda g: np.linalg.norm(g - pos))

    def _goal_reached(self) -> bool:
        return float(np.linalg.norm(np.array(self.get_achieved_goal()) - self.goal)) < self.distance_threshold

    def _advance_goal(self) -> None:
        if self._goal_mode == "sequence":
            self._current_idx += 1
        elif self._goal_mode == "set":
            pos  = np.array(self.get_achieved_goal())
            live = self._live_positions()
            for i, g in enumerate(live):
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
        if self._goal_mode == "sequence":
            return min(self._current_idx, len(self._goal_names) - 1)
        live = self._live_positions()
        best_i, best_d = 0, float("inf")
        for i, g in enumerate(live):
            d = float(np.linalg.norm(g - self.goal))
            if d < best_d:
                best_d, best_i = d, i
        return best_i

    def active_goal_name(self) -> str:
        return self._goal_names[self._active_goal_idx()]

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
            if self._is_completed(i):
                self._set_sphere_rgba(name, _COLOR_DONE)
            elif i == active_idx:
                self._set_sphere_rgba(name, _COLOR_ACTIVE)
            else:
                self._set_sphere_rgba(name, _COLOR_PENDING)

    # ── panda_gym interface ──────────────────────────────────────────────────

    @abstractmethod
    def get_achieved_goal(self) -> np.ndarray: ...

    def is_success(self, achieved_goal: np.ndarray, desired_goal: np.ndarray, info: Dict[str, Any] = {}) -> np.ndarray:
        if self._goal_mode == "options":
            return np.array(
                any(float(distance(achieved_goal, g)) < self.distance_threshold for g in self._live_positions()),
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
    raw_type = target_goal_cfg.get("mode", "goal_options")
    mode     = raw_type.replace("goal_", "")
    targets  = target_goal_cfg["targets"]
    names    = [t["name"]                              for t in targets]
    goals    = [np.array(t["position"], dtype=np.float32) for t in targets]
    return mode, names, goals
