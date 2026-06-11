from typing import Any, Callable, Dict

import numpy as np
import pybullet

from panda_gym.envs.core import Task
from panda_gym.utils import distance


class ManualTask(Task):
    def __init__(
        self,
        sim,
        get_ee_position: Callable[[], np.ndarray],
        get_object_position: Callable[[], np.ndarray],
        goal_position: np.ndarray,
        distance_threshold: float = 0.05,
        move_speed: float = 0.5,
    ) -> None:
        super().__init__(sim)
        self.get_ee_position = get_ee_position
        self.get_object_position = get_object_position
        self.fixed_goal = np.array(goal_position, dtype=np.float32)
        self.distance_threshold = distance_threshold
        self.move_speed = move_speed
        self._gripper_open = True

    def reset(self) -> None:
        self.goal = self.fixed_goal.copy()
        self.sim.set_base_pose("target", self.goal, np.array([0.0, 0.0, 0.0, 1.0]))
        self._gripper_open = True

    def get_obs(self) -> np.ndarray:
        return np.array(self.get_object_position(), dtype=np.float32)

    def get_achieved_goal(self) -> np.ndarray:
        return np.array(self.get_object_position(), dtype=np.float32)

    def is_success(self, achieved_goal: np.ndarray, desired_goal: np.ndarray, info: Dict[str, Any] = {}) -> np.ndarray:
        return np.array(distance(achieved_goal, desired_goal) < self.distance_threshold, dtype=bool)

    def compute_reward(self, achieved_goal: np.ndarray, desired_goal: np.ndarray, info: Dict[str, Any] = {}) -> np.ndarray:
        return -distance(achieved_goal, desired_goal).astype(np.float32)

    def compute_action(self) -> np.ndarray:
        dx, dy, dz = 0.0, 0.0, 0.0
        s = self.move_speed

        # --- Teclado ---
        keys = pybullet.getKeyboardEvents()

        # Espaço: toggle garra
        if ord(' ') in keys and keys[ord(' ')] & pybullet.KEY_WAS_TRIGGERED:
            self._gripper_open = not self._gripper_open
            state = "ABERTA" if self._gripper_open else "FECHADA"
            print(f"[Garra] {state}")

        # Setas: X/Y
        if pybullet.B3G_UP_ARROW in keys and keys[pybullet.B3G_UP_ARROW] & pybullet.KEY_IS_DOWN:
            dx += s
        if pybullet.B3G_DOWN_ARROW in keys and keys[pybullet.B3G_DOWN_ARROW] & pybullet.KEY_IS_DOWN:
            dx -= s
        if pybullet.B3G_LEFT_ARROW in keys and keys[pybullet.B3G_LEFT_ARROW] & pybullet.KEY_IS_DOWN:
            dy += s
        if pybullet.B3G_RIGHT_ARROW in keys and keys[pybullet.B3G_RIGHT_ARROW] & pybullet.KEY_IS_DOWN:
            dy -= s

        # Q/E: Z (cima/baixo)
        if ord('q') in keys and keys[ord('q')] & pybullet.KEY_IS_DOWN:
            dz += s
        if ord('e') in keys and keys[ord('e')] & pybullet.KEY_IS_DOWN:
            dz -= s

        gripper = 1.0 if self._gripper_open else -1.0
        return np.array([dx, dy, dz, gripper], dtype=np.float32)
