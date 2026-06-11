from typing import Optional

import numpy as np

from tasks import PickAndPlaceTask, PushTask
from tasks.recover_task import RecoverTask
from .knowledge import Knowledge, Strategy, SystemState


class Executor:
    """
    Gerencia a task ativa e troca de estratégia quando o Planner decide.

    Ao trocar de estratégia, instancia uma nova task e chama reset() para
    garantir estado interno limpo.
    """

    def __init__(self, sim, robot, goal_position: np.ndarray, knowledge: Knowledge) -> None:
        self.sim = sim
        self.robot = robot
        self.goal_position = goal_position.copy()
        self.knowledge = knowledge
        self._active_strategy: Optional[Strategy] = None
        self._active_task = None

    def execute(self, strategy: Strategy, state: SystemState) -> np.ndarray:
        if strategy != self._active_strategy:
            self._switch_task(strategy)
        return self._active_task.compute_action()

    def _switch_task(self, strategy: Strategy) -> None:
        self._active_strategy = strategy
        common = dict(
            sim=self.sim,
            get_ee_position=self.robot.get_ee_position,
            get_object_position=lambda: self.sim.get_base_position("cube_1"),
            goal_position=self.goal_position,
        )
        if strategy == Strategy.PUSH:
            self._active_task = PushTask(**common)
        elif strategy == Strategy.PICK_AND_PLACE_OVER:
            self._active_task = PickAndPlaceTask(**common)
        elif strategy == Strategy.RECOVER:
            self._active_task = RecoverTask(**common)
        else:
            raise ValueError(f"Estratégia desconhecida: {strategy}")

        self._active_task.reset()
        print(f"[MAPE-K | Execute] Task ativada: {strategy.value}")

    @property
    def active_task(self):
        return self._active_task
