from typing import Any, Callable, Dict

import numpy as np

from panda_gym.envs.core import Task
from panda_gym.utils import distance

# Fases do controlador
_PHASE_ABOVE_BOX   = 0  # move EE acima do cubo (garra aberta)
_PHASE_GRASP       = 1  # desce até o cubo e fecha a garra
_PHASE_LIFT        = 2  # sobe com o cubo
_PHASE_ABOVE_GOAL  = 3  # move horizontalmente até acima do goal
_PHASE_PLACE       = 4  # desce até o goal


class PickAndPlaceTask(Task):
    def __init__(
        self,
        sim,
        get_ee_position: Callable[[], np.ndarray],
        get_object_position: Callable[[], np.ndarray],
        goal_position: np.ndarray,
        reward_type: str = "dense",
        distance_threshold: float = 0.05,
        grasp_height_offset: float = 0.01,
        approach_height: float = 0.1,
        phase_threshold: float = 0.02,
    ) -> None:
        super().__init__(sim)
        self.get_ee_position = get_ee_position
        self.get_object_position = get_object_position
        self.fixed_goal = np.array(goal_position, dtype=np.float32)
        self.reward_type = reward_type
        self.distance_threshold = distance_threshold
        self.grasp_height_offset = grasp_height_offset
        self.approach_height = approach_height
        self.phase_threshold = phase_threshold
        self._phase = _PHASE_ABOVE_BOX
        self._lift_target = None

    def reset(self) -> None:
        self.goal = self.fixed_goal.copy()
        self.sim.set_base_pose("target", self.goal, np.array([0.0, 0.0, 0.0, 1.0]))
        self._phase = _PHASE_ABOVE_BOX
        self._lift_target = None

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

        above_box  = box_pos  + np.array([0.0, 0.0, self.approach_height])
        grasp_pos  = box_pos  + np.array([0.0, 0.0, self.grasp_height_offset])
        lift_pos   = ee_pos   + np.array([0.0, 0.0, self.approach_height])
        above_goal = goal_pos + np.array([0.0, 0.0, self.approach_height])

        if self._phase == _PHASE_ABOVE_BOX:
            target = above_box
            gripper = np.array([1.0])   # garra aberta
            if np.linalg.norm(ee_pos - target) < self.phase_threshold:
                self._phase = _PHASE_GRASP

        elif self._phase == _PHASE_GRASP:
            target = grasp_pos
            if np.linalg.norm(ee_pos - target) < self.phase_threshold:
                gripper = np.array([-1.0])  # fecha garra só ao chegar no cubo
                self._lift_target = ee_pos + np.array([0.0, 0.0, self.approach_height])
                self._phase = _PHASE_LIFT
            else:
                gripper = np.array([1.0])   # mantém aberta enquanto desce

        elif self._phase == _PHASE_LIFT:
            target = self._lift_target
            gripper = np.array([-1.0])  # mantém fechada
            if np.linalg.norm(ee_pos - target) < self.phase_threshold:
                self._phase = _PHASE_ABOVE_GOAL

        elif self._phase == _PHASE_ABOVE_GOAL:
            target = above_goal
            gripper = np.array([-1.0])  # mantém fechada
            if np.linalg.norm(ee_pos - target) < self.phase_threshold:
                self._phase = _PHASE_PLACE

        else:  # _PHASE_PLACE
            target = goal_pos
            gripper = np.array([-1.0])  # mantém fechada

        direction = target - ee_pos
        dist = np.linalg.norm(direction)
        if dist > 0:
            direction = direction / dist

        return np.concatenate([direction, gripper]).astype(np.float32)
