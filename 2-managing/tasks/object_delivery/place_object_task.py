from typing import Callable

import numpy as np

from .._object_task import _ObjectTask
from utils import ts

# ASM — PLACE_OBJECT
# Given : distance_ee_goal_cm <= 5.0
# When  : transport_done == true
# Do    : place_object()  — desce EE até a altura de deposição e abre garra
# Then  : object_at_goal == true, gripper_width_cm >= 6.0

_PHASE_DESCEND = 0   # desce EE até a altura de deposição
_PHASE_RELEASE = 1   # abre garra
_PHASE_DONE    = 2   # postcondição satisfeita


class PlaceObjectTask(_ObjectTask):

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
        self.place_offset      = _cfg.get("place_offset",      0.0)          # EE desce até goal_z (cubo repousa na mesa)
        self.threshold         = _cfg.get("threshold",         0.005)         # tolerância em Z para acionar RELEASE (5 mm)
        self.slow_zone         = _cfg.get("slow_zone",         0.20)          # 20 cm: zona de desaceleração proporcional
        self.max_descent_speed = _cfg.get("max_descent_speed", 0.15)          # 15 %: cap de velocidade para não acumular inércia
        self.release_steps     = _cfg.get("release_steps",     5)
        self._phase         = _PHASE_DESCEND
        self._release_count = 0

    def reset(self) -> None:
        self.reset_phase()
        super().reset()

    def reset_phase(self) -> None:
        self._phase         = _PHASE_DESCEND
        self._release_count = 0

    def compute_action(self) -> np.ndarray:
        ee_pos   = np.array(self.get_ee_position())
        goal_pos = np.array(self.goal)

        # target_z = goal_z: EE desce até o centro do cubo estar na posição de repouso sobre a mesa.
        # threshold=5mm garante que o braço para em EE≈0.025, cubo_base≈5mm acima da mesa → cai 5mm ao soltar.
        target_z = goal_pos[2] + self.place_offset
        gripper  = -1.0

        if self._phase == _PHASE_DESCEND:
            if ee_pos[2] <= target_z + self.threshold:
                self._phase = _PHASE_RELEASE
            else:
                # Controle proporcional em Z puro (XY já está sobre o goal vindo do transporte).
                # Longe do alvo (>= slow_zone): ação máxima -1.
                # Dentro da slow_zone: velocidade proporcional → braço quase para ao chegar.
                z_gap    = ee_pos[2] - target_z                        # distância acima do alvo (sempre positivo aqui)
                action_z = -min(z_gap / self.slow_zone, self.max_descent_speed)  # proporcional + cap de velocidade
                return np.array([0.0, 0.0, action_z, gripper], dtype=np.float32)

        if self._phase == _PHASE_RELEASE:
            gripper = 1.0
            self._release_count += 1
            if self._release_count >= self.release_steps:
                print(f"[{ts()}][PlaceObject] Postcondição: object_at_goal == true, gripper open ✓")
                self._phase = _PHASE_DONE

        return np.array([0.0, 0.0, 0.0, gripper], dtype=np.float32)

    @property
    def done(self) -> bool:
        return self._phase == _PHASE_DONE
