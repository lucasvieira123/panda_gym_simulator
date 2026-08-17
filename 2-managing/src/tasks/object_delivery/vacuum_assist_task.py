from typing import Callable

import numpy as np

from .._object_task import _ObjectTask
from utils import ts

# DejaVu adaptation — APPLY_VACUUM_ASSIST
# Triggered when: lift failed due to low surface friction (object slipped)
# Strategy: increase finger lateral friction to simulate vacuum assist,
#           re-descend to object, re-grasp, re-lift
# After done: managing returns to TRANSPORT_OBJECT in the main sequence

_FINGER_LENGTH = 0.025  # wrist → fingertip (Franka Panda)

_PHASE_BOOST   = 0  # increase lateralFriction on both fingers — immediate, no motion
_PHASE_DESCEND = 1  # lower EE to grasp position above current object location
_PHASE_CLOSE   = 2  # close gripper with new friction
_PHASE_LIFT    = 3  # lift object to target height
_PHASE_DONE    = 4


class VacuumAssistTask(_ObjectTask):

    return_to        = "TRANSPORT_OBJECT"
    current_subtask  = "APPLY_VACUUM_ASSIST"

    def __init__(
        self,
        sim,
        fingers_indices,
        get_ee_position: Callable[[], np.ndarray],
        get_object_position: Callable[[], np.ndarray],
        target_goal_cfg: dict,
        object_cfg: dict,
        task_cfg: dict = None,
    ) -> None:
        super().__init__(sim, get_ee_position, get_object_position, target_goal_cfg, object_cfg, task_cfg)
        _cfg = task_cfg or {}
        self._fingers_indices  = fingers_indices
        self.boosted_friction  = _cfg.get("vacuum_friction",  3.0)
        self.lift_height       = _cfg.get("lift_height",      0.15)
        self.threshold         = _cfg.get("phase_threshold",  0.02)
        self._phase            = _PHASE_BOOST
        self._base_z: float | None = None

    def reset(self) -> None:
        self.reset_phase()
        super().reset()

    def reset_phase(self) -> None:
        self._phase  = _PHASE_BOOST
        self._base_z = None

    def compute_action(self) -> np.ndarray:
        ee_pos  = np.array(self.get_ee_position())
        obj_pos = np.array(self.get_object_position())

        grasp_target = np.array([obj_pos[0], obj_pos[1], obj_pos[2] + _FINGER_LENGTH])

        if self._phase == _PHASE_BOOST:
            for link in self._fingers_indices:
                self.sim.set_lateral_friction("panda", int(link), self.boosted_friction)
            print(f"[{ts()}][VacuumAssist] lateralFriction → {self.boosted_friction} ✓ — descendo para objeto")
            self._phase = _PHASE_DESCEND
            gripper = 1.0
            target  = ee_pos  # sem movimento neste step

        elif self._phase == _PHASE_DESCEND:
            gripper = 1.0
            target  = grasp_target
            if np.linalg.norm(ee_pos - grasp_target) < self.threshold:
                print(f"[{ts()}][VacuumAssist] EE alinhado com objeto ✓ — fechando gripper")
                self._phase = _PHASE_CLOSE

        elif self._phase == _PHASE_CLOSE:
            gripper = -1.0
            target  = ee_pos
            if self._base_z is None:
                self._base_z = obj_pos[2]
            self._phase = _PHASE_LIFT
            print(f"[{ts()}][VacuumAssist] Gripper fechado ✓ — iniciando lift")

        elif self._phase == _PHASE_LIFT:
            gripper  = -1.0
            target_z = self._base_z + self.lift_height
            target   = np.array([ee_pos[0], ee_pos[1], target_z])
            if abs(ee_pos[2] - target_z) < self.threshold:
                print(f"[{ts()}][VacuumAssist] Lift concluído ✓ — retomando TRANSPORT")
                self._phase = _PHASE_DONE

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
