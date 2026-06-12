from typing import Any, Callable, Dict

import numpy as np

from panda_gym.utils import distance

from ._task import _Task


class HoldTask(_Task):
    def __init__(
        self,
        sim,
        get_ee_position: Callable[[], np.ndarray],
        get_object_position: Callable[[], np.ndarray],
        goal_position: np.ndarray,
        distance_threshold: float = 0.05,
    ) -> None:
        super().__init__(sim)
        self.get_ee_position = get_ee_position
        self.get_object_position = get_object_position
        self.fixed_goal = np.array(goal_position, dtype=np.float32)
        self.distance_threshold = distance_threshold

    def reset(self) -> None:
        self.goal = self.fixed_goal.copy()
        self.sim.set_base_pose("target", self.goal, np.array([0.0, 0.0, 0.0, 1.0]))

    def get_obs(self) -> np.ndarray:
        return np.array(self.get_object_position(), dtype=np.float32)

    def get_achieved_goal(self) -> np.ndarray:
        return np.array(self.get_object_position(), dtype=np.float32)

    def is_success(self, achieved_goal: np.ndarray, desired_goal: np.ndarray, info: Dict[str, Any] = {}) -> np.ndarray:
        return np.array(distance(achieved_goal, desired_goal) < self.distance_threshold, dtype=bool)

    def compute_reward(self, achieved_goal: np.ndarray, desired_goal: np.ndarray, info: Dict[str, Any] = {}) -> np.ndarray:
        return -distance(achieved_goal, desired_goal).astype(np.float32)

    def compute_action(self) -> np.ndarray:
        # dx=0, dy=0, dz=0 → sem deslocamento | gripper=0 → mantém abertura atual
        return np.zeros(4, dtype=np.float32)
