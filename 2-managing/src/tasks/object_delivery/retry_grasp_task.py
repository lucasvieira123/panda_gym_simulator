from typing import Callable

import numpy as np

from .._object_task import _ObjectTask
from utils import ts

# ASM — RETRY_GRASP
# Given : finger_contacts < 2 (falha no grasp)
# Do    : abre garra → sobe EE → desce alinhado ao centro do objeto → fecha garra
# Then  : gripper_contact == true  (ou manager decide ABORT se tentativas esgotadas)

_FINGER_LENGTH = 0.025  # distância pulso → ponta dos dedos (Franka Panda)

_PHASE_OPEN    = 0  # abre garra (1 step)
_PHASE_RETRACT = 1  # sobe EE para altura segura acima do objeto
_PHASE_DESCEND = 2  # desce EE até dedos alinhados com centro geométrico do objeto
_PHASE_CLOSE   = 3  # fecha garra
_PHASE_DONE    = 4  # ciclo completo — manager avalia resultado


class RetryGraspTask(_ObjectTask):

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
        self.retract_height = _cfg.get("retract_height", 0.12)
        self.threshold      = _cfg.get("phase_threshold", 0.02)
        self._phase         = _PHASE_OPEN

    def reset(self) -> None:
        self.reset_phase()
        super().reset()

    def reset_phase(self) -> None:
        self._phase = _PHASE_OPEN

    def compute_action(self) -> np.ndarray:
        ee_pos  = np.array(self.get_ee_position())
        obj_pos = np.array(self.get_object_position())

        grasp_z      = obj_pos[2] + _FINGER_LENGTH
        grasp_target = np.array([obj_pos[0], obj_pos[1], grasp_z])
        above_target = np.array([obj_pos[0], obj_pos[1], grasp_z + self.retract_height])

        if self._phase == _PHASE_OPEN:
            gripper = 1.0
            target  = ee_pos  # permanece no lugar enquanto abre
            self._phase = _PHASE_RETRACT
            print(f"[{ts()}][RetryGrasp] Abrindo garra...")

        elif self._phase == _PHASE_RETRACT:
            gripper = 1.0
            target  = above_target
            if np.linalg.norm(ee_pos - above_target) < self.threshold:
                print(f"[{ts()}][RetryGrasp] EE retraído ✓ — descendo para centro do objeto")
                self._phase = _PHASE_DESCEND

        elif self._phase == _PHASE_DESCEND:
            gripper = 1.0
            target  = grasp_target
            if np.linalg.norm(ee_pos - grasp_target) < self.threshold:
                print(f"[{ts()}][RetryGrasp] Dedos alinhados com centro ✓ — fechando garra")
                self._phase = _PHASE_CLOSE

        elif self._phase == _PHASE_CLOSE:
            gripper = -1.0
            target  = ee_pos  # mantém posição enquanto fecha
            self._phase = _PHASE_DONE
            print(f"[{ts()}][RetryGrasp] Ciclo completo — aguardando avaliação do manager")

        else:  # _PHASE_DONE
            gripper = -1.0
            target  = ee_pos

        direction = target - ee_pos
        dist      = np.linalg.norm(direction)
        if dist > 0:
            direction = direction / dist

        return np.array([direction[0], direction[1], direction[2], gripper], dtype=np.float32)

    @property
    def done(self) -> bool:
        return self._phase == _PHASE_DONE
