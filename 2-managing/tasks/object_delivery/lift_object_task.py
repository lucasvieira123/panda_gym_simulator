from typing import Callable

import numpy as np

from .._object_task import _ObjectTask

# ASM — LIFT_OBJECT
# Given : gripper_contact == true
# When  : grasp_done == true
# Do    : lift_object()  — eleva EE (e objeto) até lift_height
# Then  : object_height_cm >= lift_height_cm

_PHASE_LIFT = 0   # sobe até atingir lift_height
_PHASE_DONE = 1   # postcondição satisfeita


class LiftObjectTask(_ObjectTask):

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
        self.lift_height  = _cfg.get("lift_height",  0.15)   # metros acima da posição inicial
        self.threshold    = _cfg.get("threshold",    0.02)
        self._phase       = _PHASE_LIFT
        self._base_z: float | None = None

    def reset(self) -> None:
        self.reset_phase()
        super().reset()

    def reset_phase(self) -> None:
        self._phase  = _PHASE_LIFT
        self._base_z = None

    def compute_action(self) -> np.ndarray:
        ee_pos  = np.array(self.get_ee_position())
        obj_pos = np.array(self.get_object_position())
        gripper = -1.0  # garra fechada durante toda a elevação

        if self._base_z is None:
            self._base_z = obj_pos[2]

        target_z = self._base_z + self.lift_height
        target   = np.array([ee_pos[0], ee_pos[1], target_z])

        if self._phase == _PHASE_LIFT:
            if abs(ee_pos[2] - target_z) < self.threshold:
                print(f"[LiftObject] Postcondição: object_height >= {self.lift_height*100:.0f}cm ✓")
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
