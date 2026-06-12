import numpy as np

from .analyze import Analyzer
from .execute import Executor
from .knowledge import Knowledge, SystemState
from .monitor import Monitor
from .plan import Planner


class MapeKLoop:
    """
    Coordena o ciclo completo MAPE-K a cada step da simulação.

    Fluxo por step:
      obs → Monitor.collect() → Analyzer.analyze() → Planner.plan() → Executor.execute() → action

    Uso:
        knowledge = Knowledge(obstacle_names=["parede_1"])
        loop = MapeKLoop(sim, robot, goal_position, knowledge)

        obs, info = env.reset()
        loop.reset()

        action = loop.step(obs)
        obs, reward, terminated, truncated, info = env.step(action)
    """

    def __init__(self, sim, robot, goal_position: np.ndarray, knowledge: Knowledge) -> None:
        self.knowledge = knowledge
        self._state = SystemState()
        self._monitor = Monitor(sim, robot, knowledge)
        self._analyzer = Analyzer(knowledge)
        self._planner = Planner(knowledge)
        self._executor = Executor(sim, robot, goal_position, knowledge)

    def step(self, obs: dict) -> np.ndarray:
        self._state = self._monitor.collect(obs, self._state)
        self._state = self._analyzer.analyze(self._state)
        strategy = self._planner.plan(self._state)
        action = self._executor.execute(strategy, self._state)
        return action

    def reset(self) -> None:
        self._state = SystemState()

    @property
    def state(self) -> SystemState:
        return self._state
