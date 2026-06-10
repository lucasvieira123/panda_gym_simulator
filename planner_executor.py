"""
planner_executor.py
-------------------
Componentes Planner (P) e Executor (E) do loop MAPE-K.

Planner:
  - Recebe a lista de situações detectadas pelo Analyzer
  - Consulta o KB.planned_situations para selecionar planos
  - Prioriza e resolve conflitos entre planos concorrentes
  - Retorna lista de planos ordenada para o Executor

Executor:
  - Aplica cada plano ao managed system (panda-gym)
  - Registra os eventos de adaptação na KB
"""

from __future__ import annotations

import copy
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from knowledge_base import AdaptationEvent, AdaptationPlan, KnowledgeBase

logger = logging.getLogger("mapek.planner_executor")


# ===========================================================================
# PLANNER
# ===========================================================================

# Prioridade de situações: quanto MENOR, mais prioritário
SITUATION_PRIORITY: Dict[str, int] = {
    "invalid_reward":       0,   # crítico — corrupção de estado
    "episode_too_long":     1,   # segurança — evita travamento
    "diverging_trajectory": 2,   # emergente — trajetória divergente
    "reward_stagnation":    3,   # prevista — performance ruim
    "oscillation_near_goal":4,   # emergente — loop dinâmico
    "far_from_goal":        5,   # prevista — ajuste de performance
}


class Planner:
    """
    Seleciona e ordena os planos de adaptação a partir das situações detectadas.
    """

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb

    def plan(self, situations: List[str]) -> List[AdaptationPlan]:
        if not situations:
            return []

        # Remove duplicatas preservando ordem de prioridade
        unique = list(dict.fromkeys(situations))

        # Ordena por prioridade (menor valor = mais urgente)
        sorted_situations = sorted(
            unique,
            key=lambda s: SITUATION_PRIORITY.get(s, 99),
        )

        plans = []
        for sit in sorted_situations:
            plan = self.kb.planned_situations.get(sit)
            if plan is not None:
                plans.append(plan)
                logger.info(f"[Planner] Situação '{sit}' → plano '{plan.name}' selecionado")
            else:
                logger.warning(f"[Planner] Situação '{sit}' sem plano mapeado — ignorando")

        # Resolução de conflito: se há reset + ajuste de parâmetro,
        # mantemos ambos (reset ocorre no Executor após aplicar parâmetros)
        return plans


# ===========================================================================
# EXECUTOR
# ===========================================================================

class Executor:
    """
    Aplica os planos de adaptação ao managed system.

    O panda-gym não tem uma API de "reconfiguração" direta,
    então as adaptações acontecem em dois níveis:
      1. Parâmetros na KB → usados pelo gerador de ações no loop principal
      2. Flags especiais (trigger_reset) → sinalizadas de volta ao loop
    """

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb

    def execute(self, plans: List[AdaptationPlan]) -> Dict[str, Any]:
        """
        Executa a lista de planos e retorna um dict com efeitos colaterais
        que o loop principal deve tratar (ex: trigger_reset=True).
        """
        side_effects: Dict[str, Any] = {}

        for plan in plans:
            params_before = copy.deepcopy(self.kb.config)

            result = plan.action(self.kb)

            params_after = copy.deepcopy(self.kb.config)

            event = AdaptationEvent(
                step=self.kb.current_step,
                situation=plan.name,
                plan_applied=plan.name,
                params_before=params_before,
                params_after=params_after,
            )
            self.kb.log_adaptation(event)

            logger.info(
                f"[Executor] Plano '{plan.name}' aplicado | "
                f"config_delta={_config_delta(params_before, params_after)} | "
                f"side_effects={result}"
            )

            # Merge de side effects (último trigger_reset vence)
            side_effects.update(result or {})

        return side_effects


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _config_delta(before: Dict, after: Dict) -> Dict:
    return {k: (before.get(k), after.get(k)) for k in after if before.get(k) != after.get(k)}
