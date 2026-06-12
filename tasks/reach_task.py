from typing import Any, Callable, Dict

import numpy as np

from panda_gym.utils import distance

from ._task import _Task


class ReachTask(_Task):
    def __init__(
        self,
        sim,
        get_ee_position: Callable[[], np.ndarray],
        goal_position: np.ndarray,
        reward_type: str = "dense",
        distance_threshold: float = 0.01,
    ) -> None:
        super().__init__(sim)
        self.get_ee_position = get_ee_position
        self.fixed_goal = np.array(goal_position, dtype=np.float32)
        self.reward_type = reward_type
        self.distance_threshold = distance_threshold

    def reset(self) -> None:
        self.goal = self.fixed_goal.copy()
        self.sim.set_base_pose("target", self.goal, np.array([0.0, 0.0, 0.0, 1.0]))

    def get_obs(self) -> np.ndarray:
        return np.array([])

    def get_achieved_goal(self) -> np.ndarray:
        return np.array(self.get_ee_position())

    def is_success(self, achieved_goal: np.ndarray, desired_goal: np.ndarray, info: Dict[str, Any] = {}) -> np.ndarray:
        return np.array(distance(achieved_goal, desired_goal) < self.distance_threshold, dtype=bool)

    def compute_reward(self, achieved_goal: np.ndarray, desired_goal: np.ndarray, info: Dict[str, Any] = {}) -> np.ndarray:
        d = distance(achieved_goal, desired_goal)
        if self.reward_type == "sparse":
            return -np.array(d > self.distance_threshold, dtype=np.float32)
        else:
            return -d.astype(np.float32)

    def compute_action(self) -> np.ndarray:
        ee_position = np.array(self.get_ee_position())
        goal_position = self.get_goal()
        direction = goal_position - ee_position
        dist = np.linalg.norm(direction)
        if dist > 0:
            direction = direction / dist
        gripper = np.array([0.0], dtype=np.float32)
        return np.concatenate([direction, gripper]).astype(np.float32)