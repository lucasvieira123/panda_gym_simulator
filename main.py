"""
main.py
-------
Loop principal do sistema autoadaptativo MAPE-K usando panda-gym.

Managed System  → panda-gym (PandaReachDense-v3)
Managing System → Monitor → Analyzer → Planner → Executor + KnowledgeBase

Uso:
    python main.py                # roda sem render (headless)
    python main.py --render       # roda com GUI PyBullet
    python main.py --inject-faults # injeta falhas não previstas artificialmente
"""

from __future__ import annotations

import argparse
import logging
import math
import random
import sys
import time
from typing import Any, Dict

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("mapek.main")


# ===========================================================================
# Importações do sistema MAPE-K
# ===========================================================================
from knowledge_base import KnowledgeBase
from monitor_analyzer import Monitor, Analyzer
from planner_executor import Planner, Executor


# ===========================================================================
# Gerador de Ação Adaptativa
# ===========================================================================

def generate_action(obs: Dict[str, Any], kb: KnowledgeBase) -> np.ndarray:
    """
    Gera uma ação orientada ao goal com magnitude controlada pelo step_size da KB.

    A ação é um vetor 4D no PandaReach:
        [dx, dy, dz, gripper_control]
    onde dx/dy/dz é o deslocamento do end-effector.
    """
    achieved = np.array(obs["achieved_goal"])
    desired  = np.array(obs["desired_goal"])

    direction = desired - achieved
    norm = np.linalg.norm(direction)

    step_size = kb.config["step_size"]

    if norm > 1e-6:
        unit = direction / norm
        displacement = unit * min(step_size, norm)
    else:
        displacement = np.zeros(3)

    # Gripper: fixo em 0 (aberto) para a tarefa Reach
    action = np.append(displacement, 0.0)

    # Clipa para o espaço de ação ([-1, 1]^4 no PandaReach)
    return np.clip(action, -1.0, 1.0)


# ===========================================================================
# Injetor de Falhas (para testar situações não previstas)
# ===========================================================================

class FaultInjector:
    """
    Injeta perturbações artificiais para exercitar as situações não previstas.
    """

    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self._fault_schedule: Dict[int, str] = {
            40:  "corrupt_reward",      # SNP-1: reward inválido
            120: "freeze_trajectory",   # SNP-3: divergência forçada
            200: "oscillation_inject",  # SNP-2: oscilação forçada
        }
        self._active_fault: str | None = None
        self._freeze_counter: int = 0

    def maybe_inject(self, step: int, action: np.ndarray, reward: float) -> tuple[np.ndarray, float]:
        if not self.enabled:
            return action, reward

        # Ativa nova falha conforme schedule
        if step in self._fault_schedule:
            self._active_fault = self._fault_schedule[step]
            logger.warning(f"[FaultInjector] ⚡ Injetando falha '{self._active_fault}' no step {step}")

        if self._active_fault == "corrupt_reward":
            # SNP-1: corrompemos o reward por 1 step
            reward = float("nan")
            self._active_fault = None  # falha pontual
            return action, reward

        if self._active_fault == "freeze_trajectory":
            # SNP-3: zeramos a ação por 8 steps consecutivos → robô para → distância cresce
            self._freeze_counter += 1
            if self._freeze_counter >= 8:
                self._active_fault = None
                self._freeze_counter = 0
            return np.zeros_like(action), reward

        if self._active_fault == "oscillation_inject":
            # SNP-2: alterna direção da ação → oscila no mesmo lugar
            return -action * 0.3, reward

        return action, reward


# ===========================================================================
# Loop MAPE-K Principal
# ===========================================================================

def run_mapek(
    total_steps: int = 300,
    render: bool = False,
    inject_faults: bool = False,
):
    import gymnasium as gym
    import panda_gym  # noqa: F401 — necessário para registrar os envs

    if render:
        env = gym.make("PandaReachDense-v3", render_mode="human")
    else:
        env = gym.make("PandaReachDense-v3")

    # --- Inicialização do MAPE-K ---
    kb       = KnowledgeBase(history_window=50)
    monitor  = Monitor(kb)
    analyzer = Analyzer(kb)
    planner  = Planner(kb)
    executor = Executor(kb)
    faults   = FaultInjector(enabled=inject_faults)

    # --- Estado do loop ---
    gym_obs, info = env.reset()
    episode        = 1
    global_step    = 0

    logger.info("=" * 60)
    logger.info("  Sistema MAPE-K iniciado")
    logger.info(f"  total_steps={total_steps} | render={render} | inject_faults={inject_faults}")
    logger.info("=" * 60)

    for step in range(total_steps):
        global_step = step

        # ──────────────────────────────────────────────────────────────────
        # 1. Gera ação com parâmetros atuais da KB
        # ──────────────────────────────────────────────────────────────────
        action = generate_action(gym_obs, kb)

        # ──────────────────────────────────────────────────────────────────
        # 2. Injeta falhas (se habilitado) — simula situações não previstas
        # ──────────────────────────────────────────────────────────────────
        # Primeiro executa o step para obter reward real
        gym_obs_new, reward, terminated, truncated, info = env.step(action)
        reward_float = float(reward)

        action, reward_float = faults.maybe_inject(step, action, reward_float)

        # ──────────────────────────────────────────────────────────────────
        # M — Monitor: observa e registra na KB
        # ──────────────────────────────────────────────────────────────────
        obs = monitor.observe(step, gym_obs_new, reward_float)

        # ──────────────────────────────────────────────────────────────────
        # A — Analyzer: detecta situações (previstas + não previstas)
        # ──────────────────────────────────────────────────────────────────
        situations = analyzer.analyze()

        # ──────────────────────────────────────────────────────────────────
        # P — Planner: seleciona e prioriza planos
        # ──────────────────────────────────────────────────────────────────
        plans = planner.plan(situations)

        # ──────────────────────────────────────────────────────────────────
        # E — Executor: aplica adaptações e coleta side effects
        # ──────────────────────────────────────────────────────────────────
        side_effects = executor.execute(plans)

        # Log periódico
        if step % 20 == 0:
            logger.info(
                f"[Step {step:04d}] ep={episode} | "
                f"dist={obs.distance_to_goal:.4f} | "
                f"reward={obs.reward:.4f} | "
                f"step_size={kb.config['step_size']:.4f} | "
                f"situations={situations}"
            )

        # ──────────────────────────────────────────────────────────────────
        # Trata side effects do Executor
        # ──────────────────────────────────────────────────────────────────
        do_reset = (
            side_effects.get("trigger_reset", False)
            or terminated
            or truncated
        )

        if do_reset:
            reason = "adaptação" if side_effects.get("trigger_reset") else ("terminated" if terminated else "truncated")
            logger.info(f"  ↺ Reset de episódio (razão: {reason}) no step {step}")
            gym_obs, _ = env.reset()
            kb.episode_step_count = 0
            kb.best_reward_seen   = float("-inf")
            kb.stagnation_counter = 0
            episode += 1
        else:
            gym_obs = gym_obs_new

    env.close()

    # ──────────────────────────────────────────────────────────────────────
    # Relatório Final
    # ──────────────────────────────────────────────────────────────────────
    _print_report(kb, episode, total_steps)


# ===========================================================================
# Relatório
# ===========================================================================

def _print_report(kb: KnowledgeBase, episodes: int, total_steps: int):
    sep = "=" * 60

    print(f"\n{sep}")
    print("  RELATÓRIO FINAL — Sistema MAPE-K + panda-gym")
    print(sep)
    print(f"  Total steps executados : {total_steps}")
    print(f"  Episódios completados  : {episodes}")
    print(f"  Adaptações realizadas  : {len(kb.adaptation_log)}")
    print(f"  Situações não previstas: {len(kb.unplanned_detections)}")
    print()

    print("  ── Situações PREVISTAS detectadas ──")
    from collections import Counter
    counts = Counter(e.situation for e in kb.adaptation_log)
    if counts:
        for sit, cnt in counts.most_common():
            print(f"    [{cnt:3d}x]  {sit}")
    else:
        print("    (nenhuma)")

    print()
    print("  ── Situações NÃO PREVISTAS detectadas ──")
    if kb.unplanned_detections:
        unplanned_counts = Counter(d["type"] for d in kb.unplanned_detections)
        for typ, cnt in unplanned_counts.most_common():
            print(f"    [{cnt:3d}x]  {typ}")
            # Mostra primeiro exemplo
            ex = next(d for d in kb.unplanned_detections if d["type"] == typ)
            print(f"           → {ex['description']}")
    else:
        print("    (nenhuma)")

    print()
    print("  ── Configuração final na KB ──")
    for k, v in kb.config.items():
        print(f"    {k}: {v}")

    if kb.adaptation_log:
        print()
        print("  ── Últimas 5 adaptações ──")
        for ev in kb.adaptation_log[-5:]:
            delta = {
                k: (ev.params_before.get(k), ev.params_after.get(k))
                for k in ev.params_after
                if ev.params_before.get(k) != ev.params_after.get(k)
            }
            print(f"    step={ev.step:04d} | {ev.situation} | delta={delta}")

    print(sep)


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MAPE-K + panda-gym")
    parser.add_argument("--steps",         type=int,  default=300,   help="Total de steps de simulação")
    parser.add_argument("--render",        action="store_true",       help="Abre GUI PyBullet")
    parser.add_argument("--inject-faults", action="store_true",       help="Injeta falhas não previstas")
    args = parser.parse_args()

    run_mapek(
        total_steps=args.steps,
        render=args.render,
        inject_faults=args.inject_faults,
    )
