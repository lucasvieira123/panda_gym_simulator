from __future__ import annotations

import numpy as np

from .base import Behavior


class GreedyGoalBehavior(Behavior):
    """Move o end-effector diretamente em direção ao desired_goal."""

    def act(self, env, observation):
        action = np.zeros(env.action_space.shape, dtype=np.float32)

        if not isinstance(observation, dict):
            return action

        desired_goal = observation.get("desired_goal")
        obs_raw      = observation.get("observation")

        if desired_goal is None or obs_raw is None:
            return action

        desired = np.asarray(desired_goal, dtype=float).reshape(-1, 3)[0]
        ee_pos  = np.asarray(obs_raw,      dtype=float)[:3]
        delta   = desired - ee_pos

        flat = action.reshape(-1)
        flat[:min(3, flat.size)] = self.gain * delta[:min(3, flat.size)]

        if flat.size >= 4:
            flat[3] = -1.0  # garra fechada

        self._clip(action, env)
        return action

    @staticmethod
    def _clip(action, env):
        flat = action.reshape(-1)
        try:
            flat[:] = np.clip(flat, env.action_space.low.reshape(-1), env.action_space.high.reshape(-1))
        except Exception:
            flat[:] = np.clip(flat, -1.0, 1.0)


class GreedyPushBehavior(Behavior):
    """
    Push em 2 fases:
      Fase 1 — approach: posiciona ee atrás do cubo (lado oposto ao goal).
      Fase 2 — push: empurra o cubo em direção ao goal.
    """

    APPROACH_OFFSET        = 0.08
    APPROACH_THRESHOLD     = 0.03
    MIN_PUSH_DIST          = 0.06
    LIFT_HEIGHT_ABOVE_CUBE = 0.12

    def act(self, env, observation):
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

        push_dir     = delta / dist_cube_to_goal
        approach_pos = cube_pos - push_dir * self.APPROACH_OFFSET
        approach_pos[2] = cube_pos[2]

        flat = action.reshape(-1)
        n    = min(3, flat.size)

        if flat.size >= 4:
            flat[3] = -1.0  # garra fechada

        if np.linalg.norm(approach_pos - ee_pos) > self.APPROACH_THRESHOLD:
            ee_side       = float(np.dot((ee_pos - cube_pos)[:2], push_dir[:2]))
            on_wrong_side = ee_side > 0.0

            if on_wrong_side:
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
            effective_dist = max(dist_cube_to_goal, self.MIN_PUSH_DIST)
            move    = self.gain * push_dir * effective_dist
            move[2] = self.gain * (cube_pos[2] - ee_pos[2])

        flat[:n] = move[:n]
        self._clip(action, env)
        return action

    @staticmethod
    def _clip(action, env):
        flat = action.reshape(-1)
        try:
            flat[:] = np.clip(flat, env.action_space.low.reshape(-1), env.action_space.high.reshape(-1))
        except Exception:
            flat[:] = np.clip(flat, -1.0, 1.0)


class GreedyPickAndPlaceBehavior(Behavior):
    """
    Pick-and-place em 8 fases (state machine):
      OPEN → HOVER → LOWER → GRASP → LIFT → CARRY → PLACE → RELEASE
    """

    GRASP_ABOVE_HEIGHT = 0.08
    PLACE_ABOVE_HEIGHT = 0.10
    PAP_POS_THRESHOLD  = 0.03
    GRASP_HOLD_STEPS   = 10

    PHASE_OPEN    = 0
    PHASE_HOVER   = 1
    PHASE_LOWER   = 2
    PHASE_GRASP   = 3
    PHASE_LIFT    = 4
    PHASE_CARRY   = 5
    PHASE_PLACE   = 6
    PHASE_RELEASE = 7

    def __init__(self, gain: float = 5.0):
        super().__init__(gain)
        self._phase         = self.PHASE_OPEN
        self._step_in_phase = 0
        self._lift_z        = 0.0

    def reset(self) -> None:
        self._phase         = self.PHASE_OPEN
        self._step_in_phase = 0
        self._lift_z        = 0.0

    def act(self, env, observation):
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

        def move_to(target, gripper):
            move = self.gain * (target - ee_pos)
            flat[:min(3, flat.size)] = move[:min(3, flat.size)]
            if flat.size >= 4:
                flat[3] = gripper

        if self._phase == self.PHASE_OPEN:
            if flat.size >= 4:
                flat[3] = 1.0
            self._step_in_phase += 1
            if self._step_in_phase >= 5:
                self._phase         = self.PHASE_HOVER
                self._step_in_phase = 0

        elif self._phase == self.PHASE_HOVER:
            target    = cube_pos.copy()
            target[2] = cube_pos[2] + self.GRASP_ABOVE_HEIGHT
            move_to(target, 1.0)
            if np.linalg.norm(target - ee_pos) < self.PAP_POS_THRESHOLD:
                self._phase = self.PHASE_LOWER

        elif self._phase == self.PHASE_LOWER:
            target    = cube_pos.copy()
            target[2] = cube_pos[2]
            move_to(target, 1.0)
            if np.linalg.norm(target - ee_pos) < self.PAP_POS_THRESHOLD:
                self._phase         = self.PHASE_GRASP
                self._step_in_phase = 0

        elif self._phase == self.PHASE_GRASP:
            if flat.size >= 4:
                flat[3] = -1.0
            self._step_in_phase += 1
            if self._step_in_phase >= self.GRASP_HOLD_STEPS:
                self._lift_z = max(goal_pos[2], cube_pos[2]) + self.PLACE_ABOVE_HEIGHT
                self._phase  = self.PHASE_LIFT

        elif self._phase == self.PHASE_LIFT:
            target    = ee_pos.copy()
            target[2] = self._lift_z
            move_to(target, -1.0)
            if ee_pos[2] >= self._lift_z - 0.02:
                self._phase = self.PHASE_CARRY

        elif self._phase == self.PHASE_CARRY:
            target    = goal_pos.copy()
            target[2] = self._lift_z
            move_to(target, -1.0)
            if np.linalg.norm((goal_pos - ee_pos)[:2]) < self.PAP_POS_THRESHOLD:
                self._phase = self.PHASE_PLACE

        elif self._phase == self.PHASE_PLACE:
            move_to(goal_pos, -1.0)
            if np.linalg.norm(goal_pos - ee_pos) < self.PAP_POS_THRESHOLD:
                self._phase = self.PHASE_RELEASE

        elif self._phase == self.PHASE_RELEASE:
            if flat.size >= 4:
                flat[3] = 1.0

        try:
            flat[:] = np.clip(flat, env.action_space.low.reshape(-1), env.action_space.high.reshape(-1))
        except Exception:
            flat[:] = np.clip(flat, -1.0, 1.0)

        return action
