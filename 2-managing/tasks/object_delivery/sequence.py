from typing import TYPE_CHECKING, Callable

import numpy as np

from .._object_task import _ObjectTask
from .approach_object_task import ApproachObjectTask
from .grasp_object_task import GraspObjectTask
from .lift_object_task import LiftObjectTask
from .transport_object_task import TransportObjectTask
from .place_object_task import PlaceObjectTask
# RETRY_GRASP e SAFE_ABORT são tasks adaptativas — acionadas pelo manager (MAPE-K),
# não pelo fluxo interno da sequência.
# from .retry_grasp_task import RetryGraspTask
# from .abort_task import AbortTask

if TYPE_CHECKING:
    from panda_gym.envs.robots.panda import Panda
    from panda_gym.pybullet import PyBullet

STATE_APPROACH   = "APPROACH_OBJECT"
STATE_GRASP      = "GRASP_OBJECT"
STATE_LIFT       = "LIFT_OBJECT"
STATE_TRANSPORT  = "TRANSPORT_OBJECT"
STATE_PLACE      = "PLACE_OBJECT"
# STATE_RETRY e STATE_ABORT reservados para adaptação via manager
# STATE_RETRY = "RETRY_GRASP"
# STATE_ABORT = "SAFE_ABORT"

# _MAX_RETRIES removido — política de retry é responsabilidade do manager
# _MAX_RETRIES = 3


class ObjectDeliverySequence(_ObjectTask):
    """Orquestra a sequência ASM de entrega de objetos.

    Estende _ObjectTask para ser compatível com RobotTaskEnv do panda_gym.
    Delega compute_action / get_obs / get_achieved_goal para a sub-task ativa
    e implementa as transições de estado do ASM internamente.
    O manager pode forçar transições via strategy/adaptation no futuro.
    """

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

        _g  = target_goal_cfg
        _o  = object_cfg
        _tc = task_cfg

        self._sub: dict[str, _ObjectTask] = {
            STATE_APPROACH:  ApproachObjectTask(sim, get_ee_position, get_object_position, _g, _o, _tc),
            STATE_GRASP:     GraspObjectTask(sim, get_ee_position, get_object_position, _g, _o, _tc),
            STATE_LIFT:      LiftObjectTask(sim, get_ee_position, get_object_position, _g, _o, _tc),
            STATE_TRANSPORT: TransportObjectTask(sim, get_ee_position, get_object_position, _g, _o, _tc),
            STATE_PLACE:     PlaceObjectTask(sim, get_ee_position, get_object_position, _g, _o, _tc),
            # STATE_RETRY: RetryGraspTask(...)  — instanciado pelo manager ao adaptar
            # STATE_ABORT: AbortTask(...)        — instanciado pelo manager ao adaptar
        }

        self._state    = STATE_APPROACH
        # self._retry_count = 0  # gerenciado pelo manager (MAPE-K) ao acionar RETRY_GRASP
        self._seq_done = False

    # ── panda_gym interface ──────────────────────────────────────────────────

    def reset(self) -> None:
        self._state    = STATE_APPROACH
        # self._retry_count = 0  # gerenciado pelo manager (MAPE-K) ao acionar RETRY_GRASP
        self._seq_done = False
        for task in self._sub.values():
            task.reset()
        super().reset()  # reseta objeto e goal

    def get_obs(self) -> np.ndarray:
        return self._active.get_obs()

    def get_achieved_goal(self) -> np.ndarray:
        return self._active.get_achieved_goal()

    def compute_action(self) -> np.ndarray:
        if self._seq_done:
            return np.zeros(4, dtype=np.float32)

        action = self._active.compute_action()

        if self._active.done:
            self._transition()

        return action

    # ── ASM state ────────────────────────────────────────────────────────────

    @property
    def asm_state(self) -> str:
        return self._state

    @property
    def sequence_done(self) -> bool:
        return self._seq_done

    # ── helpers ──────────────────────────────────────────────────────────────

    @property
    def _active(self) -> _ObjectTask:
        return self._sub[self._state]

    def _transition(self) -> None:
        prev = self._state

        if self._state == STATE_APPROACH:
            self._state = STATE_GRASP

        elif self._state == STATE_GRASP:
            if self._sub[STATE_GRASP].contact_detected:
                self._state = STATE_LIFT
            # else:
            #     self._retry_count += 1
            #     if self._retry_count >= _MAX_RETRIES:
            #         print(f"[ObjectDelivery] Máximo de retries ({_MAX_RETRIES}). SAFE_ABORT.")
            #         self._state = STATE_ABORT
            #     else:
            #         print(f"[ObjectDelivery] Grasp falhou — retry {self._retry_count}/{_MAX_RETRIES}")
            #         self._sub[STATE_RETRY].reset()
            #         self._state = STATE_RETRY

        # elif self._state == STATE_RETRY:   # task adaptativa — acionada pelo manager (MAPE-K)
        #     self._sub[STATE_APPROACH].reset_phase()
        #     self._sub[STATE_GRASP].reset_phase()
        #     self._state = STATE_APPROACH

        elif self._state == STATE_LIFT:
            self._state = STATE_TRANSPORT

        elif self._state == STATE_TRANSPORT:
            self._state = STATE_PLACE

        elif self._state == STATE_PLACE:
            print("[ObjectDelivery] Entrega concluída! ✓")
            self._advance_goal()
            self._seq_done = True
            return

        # elif self._state == STATE_ABORT:   # task adaptativa — acionada pelo manager (MAPE-K)
        #     self._seq_done = True
        #     return

        print(f"[ObjectDelivery] {prev} → {self._state}")
        self._active.reset_phase()
