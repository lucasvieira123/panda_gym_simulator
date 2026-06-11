from __future__ import annotations

from .base import Behavior


class RandomBehavior(Behavior):
    """Amostra uma ação aleatória do espaço de ações a cada step."""

    def act(self, env, observation):
        return env.action_space.sample()
