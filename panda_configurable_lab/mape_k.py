from __future__ import annotations

from collections import deque
from typing import Any, Dict, List

import numpy as np


GOAL_HEIGHT_THRESHOLD = 0.05   # z acima disso → goal no ar, precisa de pick_and_place
STUCK_WINDOW          = 15     # steps analisados para detectar stuck
STUCK_THRESHOLD       = 0.002  # variação máxima de distância para ser considerado stuck
NO_PROGRESS_WINDOW    = 30     # janela para detectar falta de progresso
NO_PROGRESS_MIN       = 0.02   # progresso mínimo (m) esperado em NO_PROGRESS_WINDOW steps


class Knowledge:
    """Repositório compartilhado entre os 4 componentes do MAPE-K."""

    def __init__(self, initial_policy: str = "greedy_push"):
        self.current_policy   : str   = initial_policy
        self.prev_policy      : str   = initial_policy
        self.policy_start_step: int   = 0
        self.step_count       : int   = 0
        self.distance_history : deque = deque(maxlen=NO_PROGRESS_WINDOW + 5)
        self.adaptations_log  : List[dict] = []


class MAPEKController:
    """
    Controlador autoadaptativo baseado no loop MAPE-K.

    Monitora o estado da simulação a cada step e adapta a política interna
    conforme regras definidas nos componentes Analyze e Plan.

    Políticas gerenciadas internamente:
      greedy_push          → mover cubo no plano (goal no chão)
      greedy_pick_and_place → pegar e depositar cubo (goal no ar)

    Regras de adaptação:
      1. goal.z > GOAL_HEIGHT_THRESHOLD e policy != pick_and_place → troca para pick_and_place
      2. goal.z ≤ GOAL_HEIGHT_THRESHOLD e policy != greedy_push    → troca para greedy_push
      3. Distância sem variar por STUCK_WINDOW steps               → troca para política alternativa
      4. Sem progresso em NO_PROGRESS_WINDOW steps                 → troca para política alternativa
    """

    def __init__(self, initial_policy: str = "greedy_push", gain: float = 5.0):
        self.gain = gain
        self.k    = Knowledge(initial_policy=initial_policy)
        # Import local para evitar circular import com policies.py
        from .policies import SimplePolicy
        self._inner = SimplePolicy(name=initial_policy, gain=gain)

    # ── Interface pública ────────────────────────────────────────────────────

    def reset(self) -> None:
        initial = self.k.current_policy
        self.k  = Knowledge(initial_policy=initial)
        self._inner.reset_phase()

    def act(self, env, observation: Dict[str, Any]) -> np.ndarray:
        state    = self._monitor(env, observation)
        symptoms = self._analyze(state)
        plan     = self._plan(symptoms)
        self._execute(plan)

        self.k.distance_history.append(state["goal"]["distance"])
        self.k.step_count += 1

        return self._inner.act(env, observation)

    # ── Monitor ──────────────────────────────────────────────────────────────

    def _monitor(self, env, observation: Dict[str, Any]) -> dict:
        """
        Coleta o estado completo da simulação e organiza em um dicionário estruturado.

        Retorna:
        {
            "step": int,
            "ee": {
                "position":     [x, y, z],
                "velocity":     [vx, vy, vz],
                "orientation":  [x, y, z, w],
                "fingers_width": float,
            },
            "joints": {
                "angles":     [j0..j6],
                "velocities": [v0..v6],
            },
            "cube": {
                "position":    [x, y, z],
                "orientation": [roll, pitch, yaw],
                "velocity":    [vx, vy, vz],
                "angular_vel": [wx, wy, wz],
            },
            "goal": {
                "achieved": [x, y, z],
                "desired":  [x, y, z],
                "distance": float,
                "height":   float,
            },
        }
        """
        robot = env.robot
        sim   = env.sim

        # ── End-Effector ────────────────────────────────────────────────────
        ee_pos  = robot.get_ee_position().tolist()
        ee_vel  = robot.get_ee_velocity().tolist()
        try:
            ee_ori = sim.get_link_orientation("panda", robot.ee_link).tolist()
        except Exception:
            ee_ori = [0.0, 0.0, 0.0, 1.0]
        fingers = float(robot.get_fingers_width())

        # ── Juntas ──────────────────────────────────────────────────────────
        joint_angles = [float(robot.get_joint_angle(i))    for i in range(7)]
        joint_vels   = [float(robot.get_joint_velocity(i)) for i in range(7)]

        # ── Cubo ────────────────────────────────────────────────────────────
        has_cube = "cube_1" in sim._bodies_idx
        cube = {
            "position":    sim.get_base_position("cube_1").tolist()         if has_cube else None,
            "orientation": sim.get_base_rotation("cube_1").tolist()         if has_cube else None,
            "velocity":    sim.get_base_velocity("cube_1").tolist()         if has_cube else None,
            "angular_vel": sim.get_base_angular_velocity("cube_1").tolist() if has_cube else None,
        }

        # ── Goal ────────────────────────────────────────────────────────────
        achieved = observation.get("achieved_goal")
        desired  = observation.get("desired_goal")
        achieved_arr = np.asarray(achieved, dtype=float).reshape(-1, 3)[0] if achieved is not None else np.zeros(3)
        desired_arr  = np.asarray(desired,  dtype=float).reshape(-1, 3)[0] if desired  is not None else np.zeros(3)
        distance     = float(np.linalg.norm(achieved_arr - desired_arr))

        return {
            "step"  : self.k.step_count,
            "ee"    : {
                "position"     : ee_pos,
                "velocity"     : ee_vel,
                "orientation"  : ee_ori,
                "fingers_width": fingers,
            },
            "joints": {
                "angles"    : joint_angles,
                "velocities": joint_vels,
            },
            "cube"  : cube,
            "goal"  : {
                "achieved": achieved_arr.tolist(),
                "desired" : desired_arr.tolist(),
                "distance": distance,
                "height"  : float(desired_arr[2]),
            },
        }

    # ── Analyze ──────────────────────────────────────────────────────────────

    def _analyze(self, state: dict) -> List[str]:
        """Detecta sintomas que podem exigir adaptação."""
        symptoms = []
        k        = self.k

        # Mismatch entre altura do goal e política atual
        if state["goal"]["height"] > GOAL_HEIGHT_THRESHOLD:
            symptoms.append("goal_needs_lift")
        else:
            symptoms.append("goal_on_floor")

        # Stuck: distância praticamente imóvel nos últimos STUCK_WINDOW steps
        if len(k.distance_history) >= STUCK_WINDOW:
            recent    = list(k.distance_history)[-STUCK_WINDOW:]
            variation = max(recent) - min(recent)
            if variation < STUCK_THRESHOLD:
                symptoms.append("stuck")

        # Sem progresso: política ativa por muitos steps sem aproximar do goal
        steps_on_policy = k.step_count - k.policy_start_step
        if steps_on_policy >= NO_PROGRESS_WINDOW and len(k.distance_history) >= NO_PROGRESS_WINDOW:
            window   = list(k.distance_history)[-NO_PROGRESS_WINDOW:]
            progress = window[0] - window[-1]   # positivo = aproximando
            if progress < NO_PROGRESS_MIN:
                symptoms.append("no_progress")

        return symptoms

    # ── Plan ─────────────────────────────────────────────────────────────────

    def _plan(self, symptoms: List[str]) -> dict:
        """Decide qual adaptação executar com base nos sintomas."""
        k = self.k

        # Prioridade 1: mismatch de altura do goal (regra mais determinística)
        if "goal_needs_lift" in symptoms and k.current_policy != "greedy_pick_and_place":
            return {"action": "switch_policy", "to": "greedy_pick_and_place", "reason": "goal_needs_lift"}

        if "goal_on_floor" in symptoms and k.current_policy != "greedy_push":
            return {"action": "switch_policy", "to": "greedy_push", "reason": "goal_on_floor"}

        # Prioridade 2: stuck — tenta política alternativa
        if "stuck" in symptoms:
            alt = "greedy_pick_and_place" if k.current_policy == "greedy_push" else "greedy_push"
            return {"action": "switch_policy", "to": alt, "reason": "stuck"}

        # Prioridade 3: sem progresso — tenta política alternativa
        if "no_progress" in symptoms:
            alt = "greedy_pick_and_place" if k.current_policy == "greedy_push" else "greedy_push"
            return {"action": "switch_policy", "to": alt, "reason": "no_progress"}

        return {"action": "none"}

    # ── Execute ──────────────────────────────────────────────────────────────

    def _execute(self, plan: dict) -> None:
        """Aplica a adaptação planejada."""
        if plan["action"] != "switch_policy":
            return

        new_policy = plan["to"]
        k          = self.k

        if new_policy == k.current_policy:
            return

        k.adaptations_log.append({
            "step"  : k.step_count,
            "from"  : k.current_policy,
            "to"    : new_policy,
            "reason": plan["reason"],
        })

        print(
            f"[MAPE-K] step={k.step_count:3d}"
            f"  {k.current_policy} → {new_policy}"
            f"  razão: {plan['reason']}"
        )

        k.prev_policy       = k.current_policy
        k.current_policy    = new_policy
        k.policy_start_step = k.step_count

        self._inner.name = new_policy
        self._inner.reset_phase()
