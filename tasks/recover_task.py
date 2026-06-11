from typing import Any, Callable, Dict

import numpy as np
from panda_gym.envs.core import Task
from panda_gym.utils import distance

# Fases do comportamento de recuperação
_PHASE_ESCAPE      = 0  # sobe EE verticalmente para sair da situação atual
_PHASE_ABOVE_BOX   = 1  # posiciona acima do cubo (garra aberta)
_PHASE_GRASP       = 2  # desce até o cubo e fecha a garra
_PHASE_LIFT        = 3  # levanta o cubo
_PHASE_ABOVE_GOAL  = 4  # move horizontalmente acima do target
_PHASE_PLACE       = 5  # desce até o target


class RecoverTask(Task):
    """
    Comportamento de recuperação para situações não previstas.

    Fase 0 (ESCAPE): sobe o EE verticalmente a partir da posição atual,
    saindo de colisões ou de trajetórias bloqueadas antes de retomar.

    Fases 1-5: sequência pick-and-place com lift maior que o normal,
    garantindo passagem sobre obstáculos de altura desconhecida.
    """

    def __init__(
        self,
        sim,
        get_ee_position: Callable[[], np.ndarray],
        get_object_position: Callable[[], np.ndarray],
        goal_position: np.ndarray,
        distance_threshold: float = 0.05,
        escape_height: float = 0.25,
        approach_height: float = 0.18,
        grasp_height_offset: float = 0.01,
        phase_threshold: float = 0.02,
    ) -> None:
        super().__init__(sim)
        self.get_ee_position = get_ee_position
        self.get_object_position = get_object_position
        self.fixed_goal = np.array(goal_position, dtype=np.float32)
        self.distance_threshold = distance_threshold
        self.escape_height = escape_height
        self.approach_height = approach_height
        self.grasp_height_offset = grasp_height_offset
        self.phase_threshold = phase_threshold
        self._phase = _PHASE_ESCAPE
        self._escape_target = None
        self._lift_target = None

    def reset(self) -> None:
        self.goal = self.fixed_goal.copy()
        self.sim.set_base_pose("target", self.goal, np.array([0.0, 0.0, 0.0, 1.0]))
        self._phase = _PHASE_ESCAPE
        self._escape_target = None
        self._lift_target = None

    def get_obs(self) -> np.ndarray:
        return np.array(self.get_object_position(), dtype=np.float32)

    def get_achieved_goal(self) -> np.ndarray:
        return np.array(self.get_object_position(), dtype=np.float32)

    def is_success(self, achieved_goal: np.ndarray, desired_goal: np.ndarray, info: Dict[str, Any] = {}) -> np.ndarray:
        return np.array(distance(achieved_goal, desired_goal) < self.distance_threshold, dtype=bool)

    def compute_reward(self, achieved_goal: np.ndarray, desired_goal: np.ndarray, info: Dict[str, Any] = {}) -> np.ndarray:
        return -distance(achieved_goal, desired_goal).astype(np.float32)

    def compute_action(self) -> np.ndarray:
        ee_pos = np.array(self.get_ee_position())
        box_pos = np.array(self.get_object_position())
        goal_pos = self.get_goal()

        if self._phase == _PHASE_ESCAPE:
            if self._escape_target is None:
                self._escape_target = ee_pos.copy()
                self._escape_target[2] += self.escape_height
            target = self._escape_target
            gripper = np.array([1.0])  # abre garra durante escape
            if np.linalg.norm(ee_pos - target) < self.phase_threshold:
                self._phase = _PHASE_ABOVE_BOX

        elif self._phase == _PHASE_ABOVE_BOX:
            target = box_pos + np.array([0.0, 0.0, self.approach_height])
            gripper = np.array([1.0])
            if np.linalg.norm(ee_pos - target) < self.phase_threshold:
                self._phase = _PHASE_GRASP

        elif self._phase == _PHASE_GRASP:
            target = box_pos + np.array([0.0, 0.0, self.grasp_height_offset])
            if np.linalg.norm(ee_pos - target) < self.phase_threshold:
                gripper = np.array([-1.0])
                self._lift_target = ee_pos + np.array([0.0, 0.0, self.approach_height])
                self._phase = _PHASE_LIFT
            else:
                gripper = np.array([1.0])

        elif self._phase == _PHASE_LIFT:
            target = self._lift_target
            gripper = np.array([-1.0])
            if np.linalg.norm(ee_pos - target) < self.phase_threshold:
                self._phase = _PHASE_ABOVE_GOAL

        elif self._phase == _PHASE_ABOVE_GOAL:
            target = goal_pos + np.array([0.0, 0.0, self.approach_height])
            gripper = np.array([-1.0])
            if np.linalg.norm(ee_pos - target) < self.phase_threshold:
                self._phase = _PHASE_PLACE

        else:  # _PHASE_PLACE
            target = goal_pos
            gripper = np.array([-1.0])

        direction = target - ee_pos
        dist = np.linalg.norm(direction)
        if dist > 0:
            direction = direction / dist

        return np.concatenate([direction, gripper]).astype(np.float32)
