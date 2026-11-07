from typing import Callable

import numpy as np

from .._object_task import _ObjectTask
from utils import ts

# Adaptações de preensão acionadas pelo DejaVu. Todas seguem a mesma rotina de nova pegada
# e diferem só no atrito efetivo dos dedos, que simula o efeito de cada ação:
#   apply_vacuum_assist()    → sucção
#   adjust_grip_force()      → ajuste de força da garra, durante o lift
#   increase_grip_pressure() → aumento de pressão da garra, durante o transporte
# Depois de terminar, a sequência é retomada em TRANSPORT_OBJECT.

_HOVER_HEIGHT    = 0.12   # altura de alinhamento acima do centro do cubo (m)
_POSITION_TOL    = 0.005  # tolerância para fechar sobre o cubo (m)
_CLEARANCE_TOL   = 0.02   # tolerância das etapas de subida (m)
_DESCENT_SPEED   = 0.5    # fração da velocidade máxima
_SLOWDOWN_RANGE  = 0.05   # abaixo desta distância, a velocidade é proporcional (m)
_CLOSE_TICKS     = 3
_LIFT_HEIGHT     = 0.15

_PHASE_BOOST   = 0  # define o atrito dos dedos
_PHASE_RISE    = 1  # abre a garra e sobe, sem arrastar o cubo
_PHASE_ALIGN   = 2  # posiciona a garra sobre o cubo
_PHASE_DESCEND = 3  # desce até o centro do cubo
_PHASE_CLOSE   = 4  # fecha a garra
_PHASE_LIFT    = 5  # sobe com o objeto
_PHASE_DONE    = 6


class _GripRecoveryTask(_ObjectTask):

    return_to       = "TRANSPORT_OBJECT"
    current_subtask = ""
    grip_friction   = 1.0

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
        self._fingers_indices = fingers_indices
        self.reset_phase()

    def reset(self) -> None:
        self.reset_phase()
        super().reset()  # inicializa self.goal (exigido pelo panda_gym)

    def _reset_object(self) -> None:
        pass  # usa a posição atual do objeto; nunca o teleporta para a posição inicial

    def reset_phase(self) -> None:
        self._phase       = _PHASE_BOOST
        self._close_ticks = 0
        self._base_z: float | None = None

    def compute_action(self) -> np.ndarray:
        ee_pos  = np.array(self.get_ee_position())
        obj_pos = np.array(self.get_object_position())

        if self._phase == _PHASE_BOOST:
            for link in self._fingers_indices:
                self.sim.set_lateral_friction("panda", int(link), self.grip_friction)
            print(f"[{ts()}][{self.current_subtask}] lateralFriction → {self.grip_friction} ✓")
            self._phase = _PHASE_RISE

        if self._phase == _PHASE_RISE:
            target = np.array([ee_pos[0], ee_pos[1], obj_pos[2] + _HOVER_HEIGHT])
            if abs(ee_pos[2] - target[2]) < _CLEARANCE_TOL:
                self._phase = _PHASE_ALIGN
            return self._move_toward(ee_pos, target, gripper=1.0)

        if self._phase == _PHASE_ALIGN:
            target = np.array([obj_pos[0], obj_pos[1], obj_pos[2] + _HOVER_HEIGHT])
            if np.linalg.norm(ee_pos - target) < _POSITION_TOL * 2:
                self._phase = _PHASE_DESCEND
            return self._move_toward(ee_pos, target, gripper=1.0)

        if self._phase == _PHASE_DESCEND:
            if np.linalg.norm(ee_pos - obj_pos) < _POSITION_TOL:
                self._phase = _PHASE_CLOSE
            return self._move_toward(ee_pos, obj_pos, gripper=1.0, speed=_DESCENT_SPEED)

        if self._phase == _PHASE_CLOSE:
            self._close_ticks += 1
            if self._close_ticks >= _CLOSE_TICKS:
                self._base_z = obj_pos[2]
                self._phase  = _PHASE_LIFT
            return np.array([0.0, 0.0, 0.0, -1.0], dtype=np.float32)

        if self._phase == _PHASE_LIFT:
            target = np.array([ee_pos[0], ee_pos[1], self._base_z + _LIFT_HEIGHT])
            if abs(ee_pos[2] - target[2]) < _CLEARANCE_TOL:
                print(f"[{ts()}][{self.current_subtask}] Lift concluído — retomando TRANSPORT")
                self._phase = _PHASE_DONE
            return self._move_toward(ee_pos, target, gripper=-1.0)

        return np.array([0.0, 0.0, 0.0, -1.0], dtype=np.float32)

    @staticmethod
    def _move_toward(ee_pos: np.ndarray, target: np.ndarray, gripper: float, speed: float = 1.0) -> np.ndarray:
        delta    = target - ee_pos
        distance = np.linalg.norm(delta)
        if distance > 0:
            delta = delta / distance * min(distance / _SLOWDOWN_RANGE, 1.0) * speed
        return np.array([delta[0], delta[1], delta[2], gripper], dtype=np.float32)

    @property
    def done(self) -> bool:
        return self._phase == _PHASE_DONE


class VacuumAssistTask(_GripRecoveryTask):
    current_subtask = "APPLY_VACUUM_ASSIST"
    grip_friction   = 3.0


class AdjustGripForceTask(_GripRecoveryTask):
    current_subtask = "ADJUST_GRIP_FORCE"
    grip_friction   = 7.0


class IncreaseGripPressureTask(_GripRecoveryTask):
    current_subtask = "INCREASE_GRIP_PRESSURE"
    grip_friction   = 7.0
