from typing import Any, Callable, Dict

import numpy as np

from panda_gym.envs.core import Task
from panda_gym.utils import distance


class PushTask(Task):
    def __init__(
        self,
        sim,
        get_ee_position: Callable[[], np.ndarray],
        get_object_position: Callable[[], np.ndarray],
        goal_position: np.ndarray,
        reward_type: str = "dense",
        distance_threshold: float = 0.05,
        approach_offset: float = 0.05,
    ) -> None:
        super().__init__(sim)
        self.get_ee_position = get_ee_position
        self.get_object_position = get_object_position
        self.fixed_goal = np.array(goal_position, dtype=np.float32)
        self.reward_type = reward_type
        self.distance_threshold = distance_threshold
        self.approach_offset = approach_offset  # distância atrás do cubo para se posicionar antes de empurrar

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
        d = distance(achieved_goal, desired_goal)
        if self.reward_type == "sparse":
            return -np.array(d > self.distance_threshold, dtype=np.float32)
        else:
            return -d.astype(np.float32)

    def compute_action(self) -> np.ndarray:
        ee_pos  = np.array(self.get_ee_position())
        box_pos = np.array(self.get_object_position())
        goal_pos = self.get_goal()

        push_dir = goal_pos - box_pos
        push_dist = np.linalg.norm(push_dir)

        if push_dist > 0:
            push_dir_normalized = push_dir / push_dist
        else:
            push_dir_normalized = np.zeros(3)

        # posição atrás do cubo, no lado oposto ao goal
        approach_pos = box_pos - push_dir_normalized * self.approach_offset

        ee_to_approach = approach_pos - ee_pos
        dist_to_approach = np.linalg.norm(ee_to_approach)

        if dist_to_approach > 0.02:
            # fase 1: mover EE para atrás do cubo
            direction = ee_to_approach / dist_to_approach
        else:
            # fase 2: empurrar cubo em direção ao goal
            direction = push_dir_normalized

        gripper = np.array([0.0], dtype=np.float32)
        return np.concatenate([direction, gripper]).astype(np.float32)