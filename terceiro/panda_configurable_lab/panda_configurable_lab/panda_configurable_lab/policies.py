from __future__ import annotations

from typing import Any, Dict

import numpy as np


class SimplePolicy:
    """Simple policies for testing the simulation loop."""

    # greedy_push — quanto atrás do cubo o ee deve se posicionar antes de empurrar
    APPROACH_OFFSET    = 0.08   # metros
    # greedy_push — ee dentro desse raio do cubo → sempre em Fase 2 (evita oscilação)
    APPROACH_THRESHOLD = 0.03   # metros (hysteresis: OFFSET + THRESHOLD = zona de push)
    # greedy_push — distância mínima usada no cálculo da força para vencer fricção
    MIN_PUSH_DIST      = 0.06   # metros → força mínima = gain × MIN_PUSH_DIST
    # greedy_push — altura de subida para contornar o cubo ao reposicionar (Fase 1)
    LIFT_HEIGHT_ABOVE_CUBE = 0.12  # metros acima do centro do cubo

    def __init__(self, name: str = "random", gain: float = 5.0):
        self.name = name
        self.gain = gain

    def act(self, env, observation: Dict[str, Any]) -> np.ndarray:
        if self.name == "random":
            return env.action_space.sample()

        if self.name == "hold":
            return np.zeros(env.action_space.shape, dtype=np.float32)

        if self.name == "greedy_goal":
            return self._greedy_goal(env, observation)

        if self.name == "greedy_push":
            return self._greedy_push(env, observation)

        raise ValueError(f"Política desconhecida: {self.name}")

    def _greedy_goal(self, env, observation: Dict[str, Any]) -> np.ndarray:
        """Move o ee diretamente em direção ao goal (sem considerar a posição do cubo)."""
        action = np.zeros(env.action_space.shape, dtype=np.float32)

        if not isinstance(observation, dict):
            return action

        achieved_goal = observation.get("achieved_goal")
        desired_goal = observation.get("desired_goal")

        if achieved_goal is None or desired_goal is None:
            return action

        achieved = np.asarray(achieved_goal, dtype=float).reshape(-1, 3)[0]
        desired = np.asarray(desired_goal, dtype=float).reshape(-1, 3)[0]

        delta = desired - achieved

        flat_action = action.reshape(-1)
        n = min(3, flat_action.size)

        flat_action[:n] = self.gain * delta[:n]

        try:
            flat_action[:] = np.clip(
                flat_action,
                env.action_space.low.reshape(-1),
                env.action_space.high.reshape(-1),
            )
        except Exception:
            flat_action[:] = np.clip(flat_action, -1.0, 1.0)

        return action

    def _greedy_push(self, env, observation: Dict[str, Any]) -> np.ndarray:
        """
        Política de push em 2 fases:

        Fase 1 — approach: move o ee para atrás do cubo (lado oposto ao goal).
        Fase 2 — push: move o ee em direção ao goal; o cubo está no caminho e é empurrado.

        observation["observation"][:3] = posição do ee (panda-gym Panda robot layout).
        """
        action = np.zeros(env.action_space.shape, dtype=np.float32)

        if not isinstance(observation, dict):
            return action

        achieved_goal = observation.get("achieved_goal")
        desired_goal  = observation.get("desired_goal")
        obs_raw       = observation.get("observation")

        if achieved_goal is None or desired_goal is None or obs_raw is None:
            return action

        cube_pos = np.asarray(achieved_goal, dtype=float).reshape(-1, 3)[0]  # (x,y,z) do cubo
        goal_pos = np.asarray(desired_goal,  dtype=float).reshape(-1, 3)[0]  # (x,y,z) do goal
        ee_pos   = np.asarray(obs_raw,       dtype=float)[:3]                # (x,y,z) do ee

        # Vetor cubo → goal e distância
        delta              = goal_pos - cube_pos
        dist_cube_to_goal  = np.linalg.norm(delta)

        if dist_cube_to_goal < 1e-6:
            return action  # cubo já no goal

        push_dir = delta / dist_cube_to_goal

        # Posição de approach: APPROACH_OFFSET atrás do cubo, na direção oposta ao goal
        approach_pos    = cube_pos - push_dir * self.APPROACH_OFFSET
        approach_pos[2] = cube_pos[2]   # mesma altura do cubo (empurrão horizontal)

        dist_to_approach = np.linalg.norm(approach_pos - ee_pos)

        flat_action = action.reshape(-1)
        n = min(3, flat_action.size)

        if dist_to_approach > self.APPROACH_THRESHOLD:
            # Fase 1: posicionar ee atrás do cubo (lado oposto ao goal).
            # Se o ee está perto do cubo, o caminho direto até a nova approach_pos
            # pode passar pelo cubo e empurrá-lo na direção errada (ex: quando o goal
            # muda e a approach_pos fica no lado oposto). Para evitar isso, sobe
            # primeiro em Z passando por cima do cubo, depois desce na approach_pos.
            dist_ee_to_cube = np.linalg.norm(cube_pos - ee_pos)
            if dist_ee_to_cube < self.APPROACH_OFFSET * 2.0:
                lift_z = cube_pos[2] + self.LIFT_HEIGHT_ABOVE_CUBE
                if ee_pos[2] < lift_z - 0.02:
                    # Sobe em direção à approach_pos mas na altitude lift_z
                    lifted = approach_pos.copy()
                    lifted[2] = lift_z
                    move = self.gain * (lifted - ee_pos)
                else:
                    # Já está alto o suficiente: desce para a approach_pos final
                    move = self.gain * (approach_pos - ee_pos)
            else:
                move = self.gain * (approach_pos - ee_pos)
        else:
            # Fase 2: empurrar com força mínima garantida para vencer a fricção.
            # max(dist, MIN_PUSH_DIST) evita que a força caia a zero quando
            # o cubo está perto do goal mas ainda precisa ser empurrado.
            effective_dist = max(dist_cube_to_goal, self.MIN_PUSH_DIST)
            move = self.gain * push_dir * effective_dist

        flat_action[:n] = move[:n]

        try:
            flat_action[:] = np.clip(
                flat_action,
                env.action_space.low.reshape(-1),
                env.action_space.high.reshape(-1),
            )
        except Exception:
            flat_action[:] = np.clip(flat_action, -1.0, 1.0)

        return action
