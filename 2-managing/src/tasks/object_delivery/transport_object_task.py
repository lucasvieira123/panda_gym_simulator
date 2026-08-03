from typing import Callable

import numpy as np

from .._object_task import _ObjectTask
from utils import ts

# ASM — TRANSPORT_OBJECT
# Given : object_height_cm >= lift_height_cm, goal_reachable == true
# When  : lift_done == true
# Do    : transport_object()  — move EE horizontalmente até acima do goal
# Then  : distance_ee_goal_cm <= 5.0

_PHASE_MOVE = 0   # translada XY até acima do goal
_PHASE_DONE = 1   # postcondição satisfeita


class TransportObjectTask(_ObjectTask):

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
        self.threshold    = _cfg.get("threshold", 0.005)  # 5 mm — praticamente exato sobre o goal XY
        self._phase       = _PHASE_MOVE
        self._transport_z: float | None = None

    def reset(self) -> None:
        self.reset_phase()
        super().reset()

    def reset_phase(self) -> None:
        self._phase       = _PHASE_MOVE
        self._transport_z = None

    def compute_action(self) -> np.ndarray:
        ee_pos   = np.array(self.get_ee_position())
        goal_pos = np.array(self.goal)
        gripper  = -1.0  # garra fechada

        if self._transport_z is None:
            self._transport_z = ee_pos[2]  # trava a altura no início do transporte

        # alvo 3D: XY do goal, Z fixo da altura de lift
        target  = np.array([goal_pos[0], goal_pos[1], self._transport_z])
        xy_dist = np.linalg.norm(ee_pos[:2] - goal_pos[:2])

        if self._phase == _PHASE_MOVE:
            if xy_dist < self.threshold:
                print(f"[{ts()}][TransportObject] Postcondição: distance_ee_goal <= 5cm ✓")
                self._phase = _PHASE_DONE

        if self._phase == _PHASE_DONE:
            target = ee_pos  # segura posição

        direction = target - ee_pos
        dist      = np.linalg.norm(direction)
        if dist > 0:
            direction = direction / dist

        return np.array([direction[0], direction[1], direction[2], gripper], dtype=np.float32)

    @property
    def done(self) -> bool:
        return self._phase == _PHASE_DONE
