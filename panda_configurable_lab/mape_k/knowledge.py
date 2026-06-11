from __future__ import annotations

from typing import List, Optional


class Knowledge:
    """
    Memória compartilhada do controlador MAPE-K.

    Passada por referência entre Monitor, Analyzer e PlanExecute
    para que cada componente leia e escreva o estado persistente.
    """

    def __init__(self, initial_policy: str = "greedy_push"):
        self.current_policy           : str            = initial_policy
        self.step_count               : int            = 0
        self.prev_desired_goal        : Optional[list] = None   # goal do step anterior (para goal_changed)
        self.cautious_steps_remaining : int            = 0      # steps restantes no modo cauteloso
        self.cautious_factor          : float          = 0.4    # gain factor atual do modo cauteloso
        self.events_log               : List[dict]     = []     # log de situações detectadas
