from __future__ import annotations

from typing import Any, Dict

import numpy as np


class SimplePolicy:
    """Simple policies for testing the simulation loop."""

    # ── greedy_push ──────────────────────────────────────────────────────────
    APPROACH_OFFSET        = 0.08   # metros atrás do cubo para approach
    APPROACH_THRESHOLD     = 0.03   # tolerância para entrar na fase de push
    MIN_PUSH_DIST          = 0.06   # distância mínima no cálculo da força
    LIFT_HEIGHT_ABOVE_CUBE = 0.12   # subida para contornar o cubo ao reposicionar

    # ── greedy_pick_and_place ────────────────────────────────────────────────
    GRASP_ABOVE_HEIGHT = 0.08   # hover acima do cubo antes de descer
    PLACE_ABOVE_HEIGHT = 0.10   # altura de trânsito acima do goal no carry
    PAP_POS_THRESHOLD  = 0.03   # tolerância de posição para transição de fase
    GRASP_HOLD_STEPS   = 10     # steps mantendo garra fechada antes de levantar

    # Fases da state machine de pick_and_place
    PHASE_OPEN    = 0   # abrir garra
    PHASE_HOVER   = 1   # mover para acima do cubo
    PHASE_LOWER   = 2   # descer até o cubo
    PHASE_GRASP   = 3   # fechar garra e segurar
    PHASE_LIFT    = 4   # levantar até altura de trânsito
    PHASE_CARRY   = 5   # mover horizontalmente para acima do goal
    PHASE_PLACE   = 6   # descer até o goal
    PHASE_RELEASE = 7   # abrir garra (soltar)

    def __init__(self, name: str = "random", gain: float = 5.0):
        self.name = name
        self.gain = gain

        # Estado da pick_and_place state machine
        self._pap_phase          = self.PHASE_OPEN
        self._pap_step_in_phase  = 0
        self._pap_lift_z         = 0.0

    def reset_phase(self) -> None:
        """Reinicia o estado da fase pick_and_place (chamar no início de cada episódio)."""
        self._pap_phase         = self.PHASE_OPEN
        self._pap_step_in_phase = 0
        self._pap_lift_z        = 0.0

    def act(self, env, observation: Dict[str, Any]) -> np.ndarray:
        if self.name == "random":
            return env.action_space.sample()

        if self.name == "hold":
            return np.zeros(env.action_space.shape, dtype=np.float32)

        if self.name == "greedy_goal":
            return self._greedy_goal(env, observation)

        if self.name == "greedy_push":
            return self._greedy_push(env, observation)

        if self.name == "greedy_pick_and_place":
            return self._greedy_pick_and_place(env, observation)

        raise ValueError(f"Política desconhecida: {self.name}")

    def _greedy_goal(self, env, observation: Dict[str, Any]) -> np.ndarray:
        """Move o ee diretamente em direção ao goal (sem considerar a posição do cubo)."""
        action = np.zeros(env.action_space.shape, dtype=np.float32)

        if not isinstance(observation, dict):
            return action

        achieved_goal = observation.get("achieved_goal")
        desired_goal  = observation.get("desired_goal")

        if achieved_goal is None or desired_goal is None:
            return action

        achieved = np.asarray(achieved_goal, dtype=float).reshape(-1, 3)[0]
        desired  = np.asarray(desired_goal,  dtype=float).reshape(-1, 3)[0]

        delta = desired - achieved

        flat_action = action.reshape(-1)
        n = min(3, flat_action.size)
        flat_action[:n] = self.gain * delta[:n]

        # Manter garra fechada quando action space é 4D
        if flat_action.size >= 4:
            flat_action[3] = -1.0

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

        Fase 1 — approach: posiciona ee atrás do cubo (lado oposto ao goal).
        Fase 2 — push: empurra o cubo em direção ao goal.

        Quando o goal muda e a nova approach_pos fica do lado oposto, o ee
        sobe primeiro em Z para passar por cima do cubo sem empurrá-lo na
        direção errada.
        """
        action = np.zeros(env.action_space.shape, dtype=np.float32)

        if not isinstance(observation, dict):
            return action

        achieved_goal = observation.get("achieved_goal")
        desired_goal  = observation.get("desired_goal")
        obs_raw       = observation.get("observation")

        if achieved_goal is None or desired_goal is None or obs_raw is None:
            return action

        cube_pos = np.asarray(achieved_goal, dtype=float).reshape(-1, 3)[0]
        goal_pos = np.asarray(desired_goal,  dtype=float).reshape(-1, 3)[0]
        ee_pos   = np.asarray(obs_raw,       dtype=float)[:3]

        delta             = goal_pos - cube_pos
        dist_cube_to_goal = np.linalg.norm(delta)

        if dist_cube_to_goal < 1e-6:
            return action

        push_dir = delta / dist_cube_to_goal

        approach_pos    = cube_pos - push_dir * self.APPROACH_OFFSET
        approach_pos[2] = cube_pos[2]

        dist_to_approach = np.linalg.norm(approach_pos - ee_pos)

        flat_action = action.reshape(-1)
        n = min(3, flat_action.size)

        # Manter garra fechada durante push
        if flat_action.size >= 4:
            flat_action[3] = -1.0

        if dist_to_approach > self.APPROACH_THRESHOLD:
            # Fase 1: posicionar atrás do cubo.
            # Se perto do cubo, sobe primeiro para passar por cima ao reposicionar.
            dist_ee_to_cube = np.linalg.norm(cube_pos - ee_pos)
            if dist_ee_to_cube < self.APPROACH_OFFSET * 2.0:
                lift_z = cube_pos[2] + self.LIFT_HEIGHT_ABOVE_CUBE
                if ee_pos[2] < lift_z - 0.02:
                    lifted    = approach_pos.copy()
                    lifted[2] = lift_z
                    move = self.gain * (lifted - ee_pos)
                else:
                    move = self.gain * (approach_pos - ee_pos)
            else:
                move = self.gain * (approach_pos - ee_pos)
        else:
            # Fase 2: empurrar com força mínima garantida para vencer fricção.
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

    def _greedy_pick_and_place(self, env, observation: Dict[str, Any]) -> np.ndarray:
        """
        Política de pick_and_place em 8 fases (state machine):

          OPEN    → abrir garra
          HOVER   → mover ee para acima do cubo
          LOWER   → descer até o cubo com garra aberta
          GRASP   → fechar garra e segurar por GRASP_HOLD_STEPS
          LIFT    → subir até altura de trânsito
          CARRY   → mover horizontalmente para acima do goal
          PLACE   → descer até o goal com garra fechada
          RELEASE → abrir garra e soltar o cubo

        Requer block_gripper=false e action space 4D (dx, dy, dz, gripper).
        Resets de fase via reset_phase() no início de cada episódio.
        """
        action = np.zeros(env.action_space.shape, dtype=np.float32)

        if not isinstance(observation, dict):
            return action

        achieved_goal = observation.get("achieved_goal")
        desired_goal  = observation.get("desired_goal")
        obs_raw       = observation.get("observation")

        if achieved_goal is None or desired_goal is None or obs_raw is None:
            return action

        cube_pos = np.asarray(achieved_goal, dtype=float).reshape(-1, 3)[0]
        goal_pos = np.asarray(desired_goal,  dtype=float).reshape(-1, 3)[0]
        ee_pos   = np.asarray(obs_raw,       dtype=float)[:3]

        flat = action.reshape(-1)

        def move_to(target: np.ndarray, gripper: float) -> None:
            move = self.gain * (target - ee_pos)
            n = min(3, flat.size)
            flat[:n] = move[:n]
            if flat.size >= 4:
                flat[3] = gripper

        phase = self._pap_phase

        if phase == self.PHASE_OPEN:
            if flat.size >= 4:
                flat[3] = 1.0
            self._pap_step_in_phase += 1
            if self._pap_step_in_phase >= 5:
                self._pap_phase         = self.PHASE_HOVER
                self._pap_step_in_phase = 0

        elif phase == self.PHASE_HOVER:
            target    = cube_pos.copy()
            target[2] = cube_pos[2] + self.GRASP_ABOVE_HEIGHT
            move_to(target, 1.0)
            if np.linalg.norm(target - ee_pos) < self.PAP_POS_THRESHOLD:
                self._pap_phase = self.PHASE_LOWER

        elif phase == self.PHASE_LOWER:
            target    = cube_pos.copy()
            target[2] = cube_pos[2]
            move_to(target, 1.0)
            if np.linalg.norm(target - ee_pos) < self.PAP_POS_THRESHOLD:
                self._pap_phase         = self.PHASE_GRASP
                self._pap_step_in_phase = 0

        elif phase == self.PHASE_GRASP:
            if flat.size >= 4:
                flat[3] = -1.0
            self._pap_step_in_phase += 1
            if self._pap_step_in_phase >= self.GRASP_HOLD_STEPS:
                # Altura de trânsito: acima do goal ou do cubo, o que for maior
                self._pap_lift_z        = max(goal_pos[2], cube_pos[2]) + self.PLACE_ABOVE_HEIGHT
                self._pap_phase         = self.PHASE_LIFT

        elif phase == self.PHASE_LIFT:
            target    = ee_pos.copy()
            target[2] = self._pap_lift_z
            move_to(target, -1.0)
            if ee_pos[2] >= self._pap_lift_z - 0.02:
                self._pap_phase = self.PHASE_CARRY

        elif phase == self.PHASE_CARRY:
            target    = goal_pos.copy()
            target[2] = self._pap_lift_z   # mantém altitude de trânsito
            move_to(target, -1.0)
            if np.linalg.norm((goal_pos - ee_pos)[:2]) < self.PAP_POS_THRESHOLD:
                self._pap_phase = self.PHASE_PLACE

        elif phase == self.PHASE_PLACE:
            move_to(goal_pos, -1.0)
            if np.linalg.norm(goal_pos - ee_pos) < self.PAP_POS_THRESHOLD:
                self._pap_phase = self.PHASE_RELEASE

        elif phase == self.PHASE_RELEASE:
            if flat.size >= 4:
                flat[3] = 1.0   # abrir garra

        try:
            flat[:] = np.clip(
                flat,
                env.action_space.low.reshape(-1),
                env.action_space.high.reshape(-1),
            )
        except Exception:
            flat[:] = np.clip(flat, -1.0, 1.0)

        return action
