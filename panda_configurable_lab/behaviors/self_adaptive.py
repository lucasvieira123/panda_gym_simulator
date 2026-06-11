from __future__ import annotations

from .base import Behavior


class SelfAdaptiveBehavior(Behavior):
    """Delega ao MAPEKController — inicializado de forma lazy no primeiro act()."""

    def __init__(self, gain: float = 5.0):
        super().__init__(gain)
        self._mape_k = None

    def act(self, env, observation):
        if self._mape_k is None:
            from ..mape_k import MAPEKController
            self._mape_k = MAPEKController(initial_policy="greedy_push", gain=self.gain)
        return self._mape_k.act(env, observation)

    def reset(self) -> None:
        if self._mape_k is not None:
            self._mape_k.reset()
