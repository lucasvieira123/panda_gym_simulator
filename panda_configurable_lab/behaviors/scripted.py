from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np

from .base import Behavior


class ScriptedBehavior(Behavior):
    """
    Executa uma sequência de ações primitivas carregada via load().

    Cada entrada do script define um vetor [dx, dy, dz, gripper] e
    quantos steps mantê-lo. Quando o script termina, next_policy
    retorna o nome da política seguinte para que SimplePolicy possa
    trocar o behavior automaticamente.
    """

    def __init__(self, gain: float = 5.0):
        super().__init__(gain)
        self._steps       : List[Tuple[np.ndarray, int]] = []
        self._step_idx    : int = 0
        self._step_counter: int = 0
        self._policy_after: str = "hold"
        self._done        : bool = False

    def load(self, script: list, policy_after: str = "hold") -> None:
        self._steps = [
            (np.array(entry["action"], dtype=np.float32), int(entry.get("steps", 1)))
            for entry in script
        ]
        self._step_idx     = 0
        self._step_counter = 0
        self._policy_after = policy_after
        self._done         = False

    @property
    def next_policy(self) -> Optional[str]:
        """Retorna o nome da próxima política quando o script termina, None enquanto roda."""
        return self._policy_after if self._done else None

    def reset(self) -> None:
        self._steps        = []
        self._step_idx     = 0
        self._step_counter = 0
        self._done         = False

    def act(self, env, observation):
        action = np.zeros(env.action_space.shape, dtype=np.float32)

        if not self._steps or self._step_idx >= len(self._steps):
            self._done = True
            return action

        action_template, n_steps = self._steps[self._step_idx]

        flat = action.reshape(-1)
        n    = min(len(action_template), flat.size)
        flat[:n] = action_template[:n]

        try:
            flat[:] = np.clip(flat, env.action_space.low.reshape(-1), env.action_space.high.reshape(-1))
        except Exception:
            flat[:] = np.clip(flat, -1.0, 1.0)

        self._step_counter += 1
        if self._step_counter >= n_steps:
            self._step_idx    += 1
            self._step_counter = 0

        return action
