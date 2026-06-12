from typing import Any, Callable, Dict, List

import numpy as np

from panda_gym.utils import distance

from ._task import _Task


class ScriptedTask(_Task):
    def __init__(
        self,
        sim,
        get_ee_position: Callable[[], np.ndarray],
        get_object_position: Callable[[], np.ndarray],
        goal_position: np.ndarray,
        waypoints: List[List[float]],
        distance_threshold: float = 0.05,
        step_threshold: float = 0.02,
    ) -> None:
        super().__init__(sim)
        self.get_ee_position = get_ee_position
        self.get_object_position = get_object_position
        self.fixed_goal = np.array(goal_position, dtype=np.float32)
        self.distance_threshold = distance_threshold
        self.step_threshold = step_threshold
        self._waypoints = [np.array(w, dtype=np.float32) for w in waypoints]
        self._current_waypoint = 0

    def reset(self) -> None:
        self.goal = self.fixed_goal.copy()
        self.sim.set_base_pose("target", self.goal, np.array([0.0, 0.0, 0.0, 1.0]))
        self._current_waypoint = 0

    def get_obs(self) -> np.ndarray:
        return np.array(self.get_object_position(), dtype=np.float32)

    def get_achieved_goal(self) -> np.ndarray:
        return np.array(self.get_object_position(), dtype=np.float32)

    def is_success(self, achieved_goal: np.ndarray, desired_goal: np.ndarray, info: Dict[str, Any] = {}) -> np.ndarray:
        return np.array(distance(achieved_goal, desired_goal) < self.distance_threshold, dtype=bool)

    def compute_reward(self, achieved_goal: np.ndarray, desired_goal: np.ndarray, info: Dict[str, Any] = {}) -> np.ndarray:
        return -distance(achieved_goal, desired_goal).astype(np.float32)

    def compute_action(self) -> np.ndarray:
        if self._current_waypoint >= len(self._waypoints):
            return np.zeros(4, dtype=np.float32)  # todos os waypoints concluídos: hold

        target = self._waypoints[self._current_waypoint]
        target_pos = target[:3]
        gripper = target[3]

        ee_pos = np.array(self.get_ee_position())
        direction = target_pos - ee_pos
        dist = np.linalg.norm(direction)

        if dist < self.step_threshold:
            print(f"[Script] Waypoint {self._current_waypoint + 1}/{len(self._waypoints)} concluído")
            self._current_waypoint += 1
            if self._current_waypoint >= len(self._waypoints):
                return np.zeros(4, dtype=np.float32)
            target = self._waypoints[self._current_waypoint]
            target_pos = target[:3]
            gripper = target[3]
            direction = target_pos - ee_pos
            dist = np.linalg.norm(direction)

        if dist > 0:
            direction = direction / dist

        return np.array([direction[0], direction[1], direction[2], gripper], dtype=np.float32)