from typing import Callable

import numpy as np

from .._object_task import _ObjectTask

# ASM — RETRY_GRASP
# Given : gripper_contact == false (falha no grasp)
# When  : grasp_failed == true
# Do    : retry_grasp()  — recua EE para posição acima e tenta novamente
# Then  : gripper_contact == true  (se max_retries não esgotado)

_PHASE_RETRACT = 0   # sobe EE para fora do objeto
_PHASE_DONE    = 1   # retracted — manager decide se reentra GRASP ou ABORT


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
        self.threshold      = _cfg.get("threshold",      0.02)
        self._phase         = _PHASE_RETRACT

    def reset(self) -> None:
        self.reset_phase()
        super().reset()

    def reset_phase(self) -> None:
        self._phase = _PHASE_RETRACT

    def compute_action(self) -> np.ndarray:
        ee_pos  = np.array(self.get_ee_position())
        obj_pos = np.array(self.get_object_position())
        gripper = 1.0  # abre garra para reposicionar

        target = obj_pos + np.array([0.0, 0.0, self.retract_height])

        if self._phase == _PHASE_RETRACT:
            if np.linalg.norm(ee_pos - target) < self.threshold:
                print("[RetryGrasp] EE retraído — aguardando manager re-iniciar GRASP ✓")
                self._phase = _PHASE_DONE
        else:
            target = ee_pos  # segura posição

        direction = target - ee_pos
        dist      = np.linalg.norm(direction)
        if dist > 0:
            direction = direction / dist

        return np.array([direction[0], direction[1], direction[2], gripper], dtype=np.float32)

    @property
    def done(self) -> bool:
        return self._phase == _PHASE_DONE
