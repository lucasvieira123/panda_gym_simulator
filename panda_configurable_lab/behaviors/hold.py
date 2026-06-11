from __future__ import annotations

import numpy as np

from .base import Behavior


class HoldBehavior(Behavior):
    """Mantém o robô parado — ação zero em todos os eixos."""

    def act(self, env, observation):
        return np.zeros(env.action_space.shape, dtype=np.float32)
