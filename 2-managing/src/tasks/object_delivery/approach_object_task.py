from typing import Callable

import numpy as np

from .._object_task import _ObjectTask
from utils import ts

# ASM — APPROACH_OBJECT
# Given : gripper_width_cm >= 6.0
# When  : object_available >= 1
# Do    : approach_object()
# Then  : distance_ee_object_cm <= 2.0

# Distância do pulso (ee_link 11) até a ponta dos dedos no Franka Panda
_FINGER_LENGTH = 0.025 

_PHASE_ABOVE = 0   # move para acima do objeto
_PHASE_CLOSE = 1   # desce até pulso ficar alinhado com o centro geométrico
_PHASE_DONE  = 2   # postcondição satisfeita — aguarda transição do manager


class ApproachObjectTask(_ObjectTask):

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
        _cfg = task_cfg or {}
        self.approach_height = _cfg.get("approach_height", 0.10)
        self.phase_threshold = _cfg.get("phase_threshold", 0.02)

        # dimensões do objeto para calcular o target correto
        _obj = object_cfg or {}
        self.object_size = np.array(_obj.get("size", [0.04, 0.04, 0.04]))

        self._phase       = _PHASE_ABOVE
        self._grasp_target: np.ndarray | None = None

    def reset(self) -> None:
        self.reset_phase()
        super().reset()

    def reset_phase(self) -> None:
        self._phase        = _PHASE_ABOVE
        self._grasp_target = None

    def compute_action(self) -> np.ndarray:
        ee_pos  = np.array(self.get_ee_position())
        obj_pos = np.array(self.get_object_position())
        gripper = 1.0  # garra aberta durante toda a aproximação

        # pulso deve ficar finger_length acima do centro geométrico do objeto
        # assim os dedos ficam alinhados com o meio do cubo em Z
        grasp_z      = obj_pos[2] + _FINGER_LENGTH
        grasp_target = np.array([obj_pos[0], obj_pos[1], grasp_z])
        above_target = np.array([obj_pos[0], obj_pos[1], grasp_z + self.approach_height])

        if self._phase == _PHASE_ABOVE:
            target = above_target
            if np.linalg.norm(ee_pos - target) < self.phase_threshold:
                self._phase = _PHASE_CLOSE

        elif self._phase == _PHASE_CLOSE:
            target = grasp_target
            if np.linalg.norm(ee_pos - grasp_target) < self.phase_threshold:
                print(f"[{ts()}][ApproachObject] Postcondição: dedos alinhados com centro geométrico ✓")
                self._phase = _PHASE_DONE

        else:  # _PHASE_DONE — segura posição
            target = ee_pos

        direction = target - ee_pos
        dist      = np.linalg.norm(direction)
        if dist > 0:
            direction = direction / dist

        return np.array([direction[0], direction[1], direction[2], gripper], dtype=np.float32)

    @property
    def done(self) -> bool:
        return self._phase == _PHASE_DONE
