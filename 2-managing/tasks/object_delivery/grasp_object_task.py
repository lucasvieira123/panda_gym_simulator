from typing import Callable

import numpy as np

from .._object_task import _ObjectTask

# ASM — GRASP_OBJECT
# Given : distance_ee_object_cm <= 2.0, gripper_width_cm >= 6.0
# When  : approach_done == true
# Do    : grasp_object()  — close gripper around object
# Then  : gripper_contact == true

_PHASE_CLOSE  = 0   # envia comando de fechar garra
_PHASE_VERIFY = 1   # verifica se houve contato no step seguinte
_PHASE_DONE   = 2   # postcondição satisfeita


class GraspObjectTask(_ObjectTask):

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
        self.contact_threshold = _cfg.get("contact_threshold", 0.005)  # m
        self._phase            = _PHASE_CLOSE

    def reset(self) -> None:
        self.reset_phase()
        super().reset()

    def reset_phase(self) -> None:
        self._phase = _PHASE_CLOSE

    def compute_action(self) -> np.ndarray:
        ee_pos  = np.array(self.get_ee_position())
        obj_pos = np.array(self.get_object_position())

        direction = np.zeros(3, dtype=np.float32)

        if self._phase == _PHASE_CLOSE:
            gripper = -1.0          # fecha garra — no próximo step verifica contato
            self._phase = _PHASE_VERIFY

        elif self._phase == _PHASE_VERIFY:
            gripper = -1.0  # mantém fechada
            dist = np.linalg.norm(ee_pos - obj_pos)
            if dist < self.contact_threshold + 0.03:  # objeto dentro da garra
                print("[GraspObject] Postcondição: gripper_contact == true ✓")
                self._phase = _PHASE_DONE
            else:
                print("[GraspObject] Contato não detectado — sinaliza RETRY_GRASP")
                self._phase = _PHASE_DONE  # manager decide retry via ASM

        else:  # _PHASE_DONE
            gripper = -1.0  # segura objeto

        return np.array([direction[0], direction[1], direction[2], gripper], dtype=np.float32)

    @property
    def done(self) -> bool:
        return self._phase == _PHASE_DONE

    @property
    def contact_detected(self) -> bool:
        ee_pos  = np.array(self.get_ee_position())
        obj_pos = np.array(self.get_object_position())
        return np.linalg.norm(ee_pos - obj_pos) < self.contact_threshold + 0.03
