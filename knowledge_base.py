"""
knowledge_base.py
-----------------
Knowledge Base (K) do loop MAPE-K.

Armazena:
  - Histórico de observações/métricas
  - Situações previstas (Symptom → AdaptationPlan)
  - Situações não previstas detectadas em runtime
  - Configurações adaptáveis do managed system
"""

from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import time


# ---------------------------------------------------------------------------
# Estruturas de dados
# ---------------------------------------------------------------------------

@dataclass
class Observation:
    step: int
    reward: float
    distance_to_goal: float
    achieved_goal: Any
    desired_goal: Any
    timestamp: float = field(default_factory=time.time)


@dataclass
class AdaptationPlan:
    name: str
    description: str
    # Callable que recebe a KB e retorna dict com parâmetros novos
    action: Callable[["KnowledgeBase"], Dict[str, Any]]


@dataclass
class AdaptationEvent:
    step: int
    situation: str          # nome da situação detectada
    plan_applied: str       # nome do plano executado
    params_before: Dict
    params_after: Dict
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Knowledge Base
# ---------------------------------------------------------------------------

class KnowledgeBase:
    """
    Repositório central compartilhado por todos os componentes MAPE-K.
    """

    def __init__(self, history_window: int = 30):
        # --- Histórico de observações (janela deslizante) ---
        self.history: deque[Observation] = deque(maxlen=history_window)

        # --- Configurações adaptáveis do managed system ---
        self.config: Dict[str, Any] = {
            "step_size": 0.05,          # magnitude das ações
            "stagnation_threshold": 15, # steps sem melhora → adapta
            "distance_threshold": 0.10, # distância "longe" do goal
            "max_steps_per_episode": 80,
            "oscillation_window": 10,   # janela p/ detectar oscilação
            "oscillation_variance_threshold": 1e-4,
        }

        # --- Histórico de eventos de adaptação ---
        self.adaptation_log: List[AdaptationEvent] = []

        # --- Situações previstas: nome → AdaptationPlan ---
        self.planned_situations: Dict[str, AdaptationPlan] = {}
        self._register_planned_situations()

        # --- Situações não previstas detectadas em runtime ---
        self.unplanned_detections: List[Dict] = []

        # Contadores internos usados pelo Analyzer
        self.stagnation_counter: int = 0
        self.best_reward_seen: float = float("-inf")
        self.episode_step_count: int = 0
        self.current_step: int = 0

    # -----------------------------------------------------------------------
    # Registro de situações previstas
    # -----------------------------------------------------------------------

    def _register_planned_situations(self):
        """
        Define todas as situações previstas e seus planos de adaptação.
        Cada plano é uma função que modifica self.config e retorna
        o novo valor dos parâmetros alterados.
        """

        # ------------------------------------------------------------------
        # Situação 1 — Robô muito longe do alvo: aumentar step_size
        # ------------------------------------------------------------------
        def plan_far_from_goal(kb: "KnowledgeBase") -> Dict[str, Any]:
            new_step = min(kb.config["step_size"] * 1.5, 0.30)
            kb.config["step_size"] = new_step
            return {"step_size": new_step}

        self.planned_situations["far_from_goal"] = AdaptationPlan(
            name="far_from_goal",
            description="Distância ao goal > threshold: aumentar step_size para movimentos mais agressivos.",
            action=plan_far_from_goal,
        )

        # ------------------------------------------------------------------
        # Situação 2 — Reward estagnado: resetar episódio
        # ------------------------------------------------------------------
        def plan_reward_stagnation(kb: "KnowledgeBase") -> Dict[str, Any]:
            kb.config["step_size"] = max(kb.config["step_size"] * 0.8, 0.01)
            return {"step_size": kb.config["step_size"], "trigger_reset": True}

        self.planned_situations["reward_stagnation"] = AdaptationPlan(
            name="reward_stagnation",
            description="Reward sem melhora por N steps: reduzir step_size e forçar reset do episódio.",
            action=plan_reward_stagnation,
        )

        # ------------------------------------------------------------------
        # Situação 3 — Episódio muito longo: forçar reset
        # ------------------------------------------------------------------
        def plan_episode_too_long(kb: "KnowledgeBase") -> Dict[str, Any]:
            return {"trigger_reset": True}

        self.planned_situations["episode_too_long"] = AdaptationPlan(
            name="episode_too_long",
            description="Episódio excede max_steps_per_episode: forçar reset para evitar travamento.",
            action=plan_episode_too_long,
        )

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def push_observation(self, obs: Observation):
        self.history.append(obs)
        self.current_step = obs.step

    def log_adaptation(self, event: AdaptationEvent):
        self.adaptation_log.append(event)

    def log_unplanned(self, info: Dict):
        self.unplanned_detections.append(info)

    def last_rewards(self, n: int = 10) -> List[float]:
        window = list(self.history)[-n:]
        return [o.reward for o in window]

    def last_distances(self, n: int = 10) -> List[float]:
        window = list(self.history)[-n:]
        return [o.distance_to_goal for o in window]

    def summary(self) -> str:
        lines = [
            f"  step={self.current_step}",
            f"  config={self.config}",
            f"  adaptações aplicadas={len(self.adaptation_log)}",
            f"  situações não previstas={len(self.unplanned_detections)}",
        ]
        return "\n".join(lines)
