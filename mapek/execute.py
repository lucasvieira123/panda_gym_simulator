from typing import Optional

import numpy as np

from tasks import PickAndPlaceTask, PushTask
from tasks.scripted_task import ScriptedTask
from .knowledge import Knowledge, Strategy, SystemState


class Executor:
    """
    Gerencia a task ativa e troca de estratégia quando o Planner decide.

    Ao trocar de estratégia, instancia uma nova task e chama reset() para
    garantir estado interno limpo.
    """

    def __init__(self, sim, robot, target_goal_cfg: dict, knowledge: Knowledge) -> None:
        self.sim             = sim
        self.robot           = robot
        self.target_goal_cfg = target_goal_cfg
        self.knowledge       = knowledge
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
        )
        if strategy == Strategy.PUSH:
            goal_position = _first_goal(self.target_goal_cfg)
            self._active_task = PushTask(**common, goal_position=goal_position)
        elif strategy == Strategy.PICK_AND_PLACE_OVER:
            self._active_task = PickAndPlaceTask(**common, target_goal_cfg=self.target_goal_cfg)
        elif strategy.value.startswith("SCRIPTED."):
            script_id = strategy.value.split(".")[1]
            waypoints = self.knowledge.scripts.get(script_id, {}).get("waypoints", [])
            goal_position = _first_goal(self.target_goal_cfg)
            self._active_task = ScriptedTask(**common, goal_position=goal_position, waypoints=waypoints)
        else:
            raise ValueError(f"Estratégia desconhecida: {strategy}")

        self._active_task.reset()
        print(f"[MAPE-K | Execute] Task ativada: {strategy.value}")

    @property
    def active_task(self):
        return self._active_task


def _first_goal(target_goal_cfg: dict) -> np.ndarray:
    for key in ("goal_options", "goal_sequence", "goal_set"):
        if key in target_goal_cfg:
            return np.array(target_goal_cfg[key][0], dtype=np.float32)
    raise ValueError("target_goal_cfg must contain goal_options, goal_sequence or goal_set")
