"""
monitor_analyzer.py
-------------------
Componentes Monitor (M) e Analyzer (A) do loop MAPE-K.

Monitor:
  - Coleta dados brutos do panda-gym a cada step
  - Converte para Observation e grava na KB

Analyzer:
  - Examina o histórico na KB
  - Detecta situações PREVISTAS (codadas) e NÃO PREVISTAS (heurísticas)
  - Retorna lista de situações ativas para o Planner
"""

from __future__ import annotations

import math
import numpy as np
from typing import Any, Dict, List, Optional, Tuple

from knowledge_base import KnowledgeBase, Observation


# ===========================================================================
# MONITOR
# ===========================================================================

class Monitor:
    """
    Observa o managed system (panda-gym) e popula a Knowledge Base.
    """

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb

    def observe(
        self,
        step: int,
        gym_observation: Dict[str, Any],
        reward: float,
    ) -> Observation:
        """
        Extrai dados relevantes da observação do gymnasium e salva na KB.

        O panda-gym retorna um dict com:
            observation  → estado do robô (joint positions etc.)
            achieved_goal → posição atual do end-effector
            desired_goal  → posição alvo
        """
        achieved = gym_observation["achieved_goal"]
        desired  = gym_observation["desired_goal"]

        distance = float(np.linalg.norm(
            np.array(achieved) - np.array(desired)
        ))

        obs = Observation(
            step=step,
            reward=reward,
            distance_to_goal=distance,
            achieved_goal=achieved,
            desired_goal=desired,
        )

        self.kb.push_observation(obs)
        self.kb.episode_step_count += 1

        return obs


# ===========================================================================
# ANALYZER
# ===========================================================================

class Analyzer:
    """
    Analisa a Knowledge Base e identifica situações que requerem adaptação.

    Retorna lista de strings com os nomes das situações detectadas.
    Situações previstas → mapeadas no KB.planned_situations
    Situações não previstas → detectadas por heurísticas e logadas separadamente
    """

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb

    def analyze(self) -> List[str]:
        situations: List[str] = []

        situations += self._check_planned_situations()
        self._check_unplanned_situations()

        return situations

    # -----------------------------------------------------------------------
    # Situações PREVISTAS
    # -----------------------------------------------------------------------

    def _check_planned_situations(self) -> List[str]:
        detected = []

        if len(self.kb.history) < 3:
            return detected

        # --- SP-1: Robô longe do goal ---
        last_dist = self.kb.last_distances(n=5)
        avg_dist  = sum(last_dist) / len(last_dist)
        if avg_dist > self.kb.config["distance_threshold"]:
            detected.append("far_from_goal")

        # --- SP-2: Reward estagnado ---
        rewards = self.kb.last_rewards(n=self.kb.config["stagnation_threshold"])
        if len(rewards) == self.kb.config["stagnation_threshold"]:
            current_best = max(rewards)
            if current_best <= self.kb.best_reward_seen:
                self.kb.stagnation_counter += 1
                if self.kb.stagnation_counter >= self.kb.config["stagnation_threshold"]:
                    detected.append("reward_stagnation")
                    self.kb.stagnation_counter = 0
            else:
                self.kb.best_reward_seen = current_best
                self.kb.stagnation_counter = 0

        # --- SP-3: Episódio muito longo ---
        if self.kb.episode_step_count >= self.kb.config["max_steps_per_episode"]:
            detected.append("episode_too_long")

        return detected

    # -----------------------------------------------------------------------
    # Situações NÃO PREVISTAS (heurísticas emergentes)
    # -----------------------------------------------------------------------

    def _check_unplanned_situations(self):
        """
        Detecta anomalias que não foram antecipadas no design original.
        Loga na KB e opcionalmente injeta situações para o Planner tratar.
        """
        if not self.kb.history:
            return

        last_obs = self.kb.history[-1]

        # --- SNP-1: Reward inválido (NaN / Inf) ---
        if not math.isfinite(last_obs.reward):
            info = {
                "type": "invalid_reward",
                "step": last_obs.step,
                "value": last_obs.reward,
                "description": "Reward com valor NaN ou Inf — possível corrupção de estado do simulador.",
            }
            self.kb.log_unplanned(info)
            # Injeta como situação tratável pelo Planner de emergência
            self.kb.planned_situations.setdefault(
                "invalid_reward",
                _make_emergency_reset_plan("invalid_reward"),
            )

        # --- SNP-2: Oscilação sem convergência ---
        w = self.kb.config["oscillation_window"]
        dists = self.kb.last_distances(n=w)
        if len(dists) == w:
            variance = float(np.var(dists))
            mean_d   = float(np.mean(dists))
            # Oscilando perto do alvo mas sem chegar (baixa variância, distância média baixa mas > 0)
            if (variance < self.kb.config["oscillation_variance_threshold"]
                    and 0.01 < mean_d < 0.08):
                info = {
                    "type": "oscillation_near_goal",
                    "step": last_obs.step,
                    "mean_distance": mean_d,
                    "variance": variance,
                    "description": "Robô oscilando perto do goal sem convergir — provável loop dinâmico.",
                }
                self.kb.log_unplanned(info)
                self.kb.planned_situations.setdefault(
                    "oscillation_near_goal",
                    _make_micro_step_plan(),
                )

        # --- SNP-3: Distância aumentando monotonicamente (divergência) ---
        dists_long = self.kb.last_distances(n=8)
        if len(dists_long) == 8:
            diffs = [dists_long[i+1] - dists_long[i] for i in range(len(dists_long)-1)]
            if all(d > 0 for d in diffs):
                info = {
                    "type": "diverging_trajectory",
                    "step": last_obs.step,
                    "distances": dists_long,
                    "description": "Distância ao goal aumentando monotonicamente — trajetória divergente.",
                }
                self.kb.log_unplanned(info)
                self.kb.planned_situations.setdefault(
                    "diverging_trajectory",
                    _make_reset_and_shrink_plan(),
                )


# ---------------------------------------------------------------------------
# Factories para planos de emergência (usados pelas situações não previstas)
# ---------------------------------------------------------------------------

def _make_emergency_reset_plan(name: str):
    from knowledge_base import AdaptationPlan

    def action(kb: KnowledgeBase):
        kb.config["step_size"] = 0.03  # step conservador após corrupção
        return {"step_size": kb.config["step_size"], "trigger_reset": True}

    return AdaptationPlan(
        name=name,
        description=f"Plano de emergência criado dinamicamente para '{name}'.",
        action=action,
    )


def _make_micro_step_plan():
    from knowledge_base import AdaptationPlan

    def action(kb: KnowledgeBase):
        new_step = max(kb.config["step_size"] * 0.4, 0.005)
        kb.config["step_size"] = new_step
        return {"step_size": new_step}

    return AdaptationPlan(
        name="oscillation_near_goal",
        description="Oscilação detectada: reduzir drasticamente step_size para convergir.",
        action=action,
    )


def _make_reset_and_shrink_plan():
    from knowledge_base import AdaptationPlan

    def action(kb: KnowledgeBase):
        new_step = max(kb.config["step_size"] * 0.5, 0.01)
        kb.config["step_size"] = new_step
        return {"step_size": new_step, "trigger_reset": True}

    return AdaptationPlan(
        name="diverging_trajectory",
        description="Trajetória divergente: encolher step_size e resetar episódio.",
        action=action,
    )
