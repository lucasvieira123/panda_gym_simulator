from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

import numpy as np


class Behavior(ABC):
    """
    Interface abstrata para todos os comportamentos de política.

    Cada subclasse implementa um único comportamento (hold, push, etc.)
    e encapsula seu próprio estado interno e lógica de reset.
    """

    def __init__(self, gain: float = 5.0):
        self.gain = gain

    @abstractmethod
    def act(self, env, observation: Dict[str, Any]) -> np.ndarray:
        """Calcula e retorna a ação para o step atual."""
        ...

    def reset(self) -> None:
        """Reinicia o estado interno. Sobrescrever apenas em behaviors com estado."""
        pass
