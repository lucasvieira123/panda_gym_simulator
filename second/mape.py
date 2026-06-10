"""
mape.py
-------
The four MAPE-K components, each with a single responsibility.

  Monitor  : panda-gym dict → typed Observation → KnowledgeBase
  Analyzer : KnowledgeBase → List[str] of detected situations
  Planner  : List[str] + KB.context → SequentialPlan
  Executor : runs the active SequentialPlan step-by-step each tick
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

from knowledge_base import AdaptationEvent, KnowledgeBase, Observation
from plan import PlanStep, SequentialPlan

logger          = logging.getLogger("mapek")
log_monitor     = logging.getLogger("monitor")
log_analyzer    = logging.getLogger("analyzer")
log_planner     = logging.getLogger("planner")
log_executor    = logging.getLogger("executor")

# ---------------------------------------------------------------------------
# PandaPickAndPlace observation vector indices
# Robot (7): ee_pos(3) + ee_vel(3) + fingers_width(1)
# Task (13): obj_pos(3) + obj_rot(4) + obj_vel(3) + obj_ang_vel(3)
# ---------------------------------------------------------------------------
_EE_POS   = slice(0, 3)
_FINGERS  = 6
_OBJ_VEL  = slice(14, 17)


# ===========================================================================
# Monitor
# ===========================================================================

class Monitor:
    """
    Converts a raw panda-gym observation dict into a typed Observation
    and records it in the Knowledge Base.
    """

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb

    def observe(self, step: int, gym_obs: Dict, reward: float) -> Observation:
        raw = gym_obs["observation"]
        obs = Observation(
            step          = step,
            ee_pos        = np.array(raw[_EE_POS]),
            fingers_width = float(raw[_FINGERS]),
            object_pos    = np.array(gym_obs["achieved_goal"]),
            object_vel    = np.array(raw[_OBJ_VEL]),
            desired_goal  = np.array(gym_obs["desired_goal"]),
            reward        = reward,
        )
        self.kb.push(obs)
        log_monitor.debug(
            f"[M][{step:04d}] "
            f"ee_z={obs.ee_pos[2]:+.3f}  obj_z={obs.object_pos[2]:+.3f}  "
            f"vert_sep={obs.vertical_separation:+.3f}  "
            f"grip={'CLOSED' if obs.gripper_is_closed else 'open ':6s}({obs.fingers_width:.3f})  "
            f"dist_ee→obj={obs.dist_ee_to_object:.3f}  "
            f"dist_obj→goal={obs.dist_object_to_goal:.3f}  "
            f"reward={reward:+.4f}"
        )
        return obs


# ===========================================================================
# Analyzer
# ===========================================================================

class Analyzer:
    """
    Inspects the Knowledge Base and returns a list of detected situations.

    Before returning, it writes diagnostic context into KB.context so the
    Planner can parametrize its plan without re-reading raw observations.

    Currently detects:
      slip_detected — gripper is closed but object has fallen below the ee
    """

    # Object considered "below gripper" if ee.z - obj.z exceeds this
    SLIP_THRESHOLD   = 0.05   # metres
    # Minimum observations before analysis starts
    MIN_HISTORY      = 5
    # Grasp attempt: ee must have been this close to the object at some point
    GRASP_ATTEMPT_DIST = 0.06  # metres

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb
        self._grasp_attempted = False  # True once ee chegou perto do objeto

    def reset_episode(self) -> None:
        """Chamado no reset de episódio para limpar o estado interno."""
        self._grasp_attempted = False

    def analyze(self) -> List[str]:
        # Do not re-analyse while a plan is already executing
        if self.kb.active_plan is not None:
            return []

        if len(self.kb.history) < self.MIN_HISTORY:
            log_analyzer.debug(
                f"[A] aguardando histórico mínimo ({len(self.kb.history)}/{self.MIN_HISTORY})"
            )
            return []

        obs = self.kb.last()

        # Registra se o ee já chegou perto o suficiente do objeto (tentativa de grasp)
        if obs.dist_ee_to_object < self.GRASP_ATTEMPT_DIST:
            if not self._grasp_attempted:
                log_analyzer.debug(
                    f"[A] grasp_attempt registrado — dist_ee→obj={obs.dist_ee_to_object:.3f}"
                )
            self._grasp_attempted = True

        situations: List[str] = []

        slip = self._is_slip(obs)
        log_analyzer.debug(
            f"[A] grip={'CLOSED' if obs.gripper_is_closed else 'open'}  "
            f"vert_sep={obs.vertical_separation:+.3f}m  "
            f"threshold={self.SLIP_THRESHOLD}m  "
            f"grasp_tentado={'sim' if self._grasp_attempted else 'não'}  "
            f"slip={'*** SIM ***' if slip else 'não'}"
        )

        if slip:
            self.kb.context = {
                "vertical_sep":  obs.vertical_separation,
                "object_pos":    obs.object_pos.copy(),
                "n_adaptations": self.kb.n_adaptations,
            }
            situations.append("slip_detected")
            logger.warning(
                "[Analyzer] slip_detected — "
                f"vert_sep={obs.vertical_separation:.3f}m  "
                f"fingers={obs.fingers_width:.3f}"
            )

        return situations

    def _is_slip(self, obs: Observation) -> bool:
        """
        Slip signature: grasp foi tentado, garra está fechada
        e o objeto caiu significativamente abaixo do ee.
        Exige grasp_attempted para evitar falsos positivos no início do episódio.
        """
        return (
            self._grasp_attempted
            and obs.gripper_is_closed
            and obs.vertical_separation > self.SLIP_THRESHOLD
        )


# ===========================================================================
# Planner
# ===========================================================================

class Planner:
    """
    Maps detected situation names to SequentialPlan objects.

    Each plan is built via a factory method that uses KB.context
    (written by the Analyzer) for parametrization.

    The slip_recovery plan implements STRIPS-style precondition chaining:
      effect of step N  ≡  precondition of step N+1
    """

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb

    def plan(self, situations: List[str]) -> Optional[SequentialPlan]:
        log_planner.debug(f"[P] situações recebidas: {situations}")
        if "slip_detected" in situations:
            log_planner.debug(
                f"[P] contexto do Analyzer: "
                f"vert_sep={self.kb.context.get('vertical_sep', '?'):.3f}  "
                f"adaptações anteriores={self.kb.context.get('n_adaptations', '?')}"
            )
            return self._slip_recovery_plan()
        return None

    # ------------------------------------------------------------------
    # Plan factory
    # ------------------------------------------------------------------

    def _slip_recovery_plan(self) -> SequentialPlan:
        """
        7-step recovery after the object slips from the gripper.

        Precondition chain:
          gripper_closed
            → open_gripper → gripper_open
            → rise         → ee_safe_height
            → align        → ee_above_object
            → descend      → ee_grasp_height
            → close_gripper → gripper_closed
            → verify_grasp  → grasp_confirmed  (or retry from 'align')
            → lift          → object_at_transport_height
        """
        logger.info("[Planner] Building slip_recovery plan")
        return SequentialPlan(
            name="slip_recovery",
            steps=[
                self._step_open_gripper(),
                self._step_rise(),
                self._step_align(),
                self._step_descend(),
                self._step_close_gripper(),
                self._step_verify_grasp(),   # retries from 'align' on failure
                self._step_lift(),
            ],
            max_retries=3,
        )

    # ------------------------------------------------------------------
    # Individual step definitions
    # Each method returns one PlanStep.
    # action_fn reads from the *live* Observation so positions stay current.
    # ------------------------------------------------------------------

    def _step_open_gripper(self) -> PlanStep:
        def action(obs: Observation) -> np.ndarray:
            return np.array([0.0, 0.0, 0.0, 1.0])   # full open command

        return PlanStep(
            name          = "open_gripper",
            precondition  = lambda obs: obs.gripper_is_closed,
            action_fn     = action,
            completion_fn = lambda obs: obs.fingers_width > 0.06,
            max_steps     = 15,
        )

    def _step_rise(self) -> PlanStep:
        SAFE_OFFSET = 0.25   # metres above object

        def action(obs: Observation) -> np.ndarray:
            dz = np.clip((obs.object_pos[2] + SAFE_OFFSET) - obs.ee_pos[2], -0.1, 0.1)
            return np.array([0.0, 0.0, dz, 1.0])

        return PlanStep(
            name          = "rise",
            precondition  = lambda obs: obs.fingers_width > 0.05,
            action_fn     = action,
            completion_fn = lambda obs: obs.ee_pos[2] > obs.object_pos[2] + 0.22,
            max_steps     = 35,
        )

    def _step_align(self) -> PlanStep:
        def action(obs: Observation) -> np.ndarray:
            diff_xy = obs.object_pos[:2] - obs.ee_pos[:2]
            dist_xy = np.linalg.norm(diff_xy)
            if dist_xy > 1e-6:
                move_xy = (diff_xy / dist_xy) * min(0.05, dist_xy)
            else:
                move_xy = np.zeros(2)
            return np.array([move_xy[0], move_xy[1], 0.0, 1.0])

        return PlanStep(
            name          = "align",
            precondition  = lambda obs: obs.ee_pos[2] > obs.object_pos[2] + 0.20,
            action_fn     = action,
            completion_fn = lambda obs: (
                np.linalg.norm(obs.object_pos[:2] - obs.ee_pos[:2]) < 0.025
            ),
            max_steps     = 45,
        )

    def _step_descend(self) -> PlanStep:
        GRASP_OFFSET = 0.02   # metres above object surface

        def action(obs: Observation) -> np.ndarray:
            target_z = obs.object_pos[2] + GRASP_OFFSET
            dz = np.clip(target_z - obs.ee_pos[2], -0.08, 0.08)
            return np.array([0.0, 0.0, dz, 1.0])

        def completion(obs: Observation) -> bool:
            target_z = obs.object_pos[2] + GRASP_OFFSET
            return abs(obs.ee_pos[2] - target_z) < 0.015

        return PlanStep(
            name          = "descend",
            precondition  = lambda obs: (
                np.linalg.norm(obs.object_pos[:2] - obs.ee_pos[:2]) < 0.03
            ),
            action_fn     = action,
            completion_fn = completion,
            max_steps     = 40,
        )

    def _step_close_gripper(self) -> PlanStep:
        def action(obs: Observation) -> np.ndarray:
            return np.array([0.0, 0.0, 0.0, -1.0])  # full close command

        return PlanStep(
            name          = "close_gripper",
            precondition  = lambda obs: (
                abs(obs.ee_pos[2] - (obs.object_pos[2] + 0.02)) < 0.02
            ),
            action_fn     = action,
            completion_fn = lambda obs: obs.fingers_width < 0.03,
            max_steps     = 15,
        )

    def _step_verify_grasp(self) -> PlanStep:
        """
        Micro-lift to confirm the object follows the gripper.
        On timeout (object didn't follow) → retry from 'align'.
        This is the branching point in the plan graph.
        """
        def action(obs: Observation) -> np.ndarray:
            return np.array([0.0, 0.0, 0.02, -1.0])   # tiny rise, grip closed

        return PlanStep(
            name          = "verify_grasp",
            precondition  = lambda obs: obs.fingers_width < 0.04,
            action_fn     = action,
            completion_fn = lambda obs: obs.dist_ee_to_object < 0.04,
            max_steps     = 20,
            retry_target  = "align",   # if object didn't follow → re-align
        )

    def _step_lift(self) -> PlanStep:
        TRANSPORT_Z = 0.30   # absolute z-height for transport

        def action(obs: Observation) -> np.ndarray:
            dz = np.clip(TRANSPORT_Z - obs.ee_pos[2], -0.1, 0.1)
            return np.array([0.0, 0.0, dz, -1.0])

        return PlanStep(
            name          = "lift",
            precondition  = lambda obs: obs.dist_ee_to_object < 0.05,
            action_fn     = action,
            completion_fn = lambda obs: obs.ee_pos[2] > TRANSPORT_Z - 0.03,
            max_steps     = 45,
        )


# ===========================================================================
# Executor
# ===========================================================================

class Executor:
    """
    Activates and drives a SequentialPlan step-by-step.

    Two modes
    ---------
    activate(plan)   called once when Planner produces a plan;
                     stores the plan in KB.active_plan

    tick(obs)        called every step while KB.active_plan is not None;
                     returns (action, side_effects)

    side_effects keys
    -----------------
    trigger_reset : bool  — plan exhausted retries; the loop should reset
    """

    def __init__(self, kb: KnowledgeBase):
        self.kb = kb

    def activate(self, plan: SequentialPlan) -> None:
        self.kb.active_plan = plan
        self.kb.log_adaptation(plan.name, "activated")
        logger.info(f"[Executor] Plan '{plan.name}' activated")

    def tick(self, obs: Observation) -> Tuple[np.ndarray, Dict]:
        plan = self.kb.active_plan
        if plan is None:
            raise RuntimeError("Executor.tick() called with no active plan")

        step   = plan.current_step
        action = step.action_fn(obs)
        step.tick()

        completed = step.completion_fn(obs)

        log_executor.debug(
            f"[E] passo='{step.name}'  "
            f"tick={step.elapsed}/{step.max_steps}  "
            f"completo={'SIM' if completed else 'não'}  "
            f"timeout={'SIM' if step.timed_out else 'não'}  "
            f"ação={np.round(action, 3).tolist()}"
        )

        if completed:
            logger.info(
                f"[Executor] '{step.name}' CONCLUÍDO  "
                f"({step.elapsed}/{step.max_steps} ticks)"
            )
            plan.advance()

        elif step.timed_out:
            if step.retry_target is not None:
                succeeded = plan.retry()
                if succeeded:
                    logger.warning(
                        f"[Executor] '{step.name}' TIMEOUT → "
                        f"retry #{plan.retry_count}/{plan.max_retries} "
                        f"voltando para '{plan.current_step.name}'"
                    )
                else:
                    logger.error(
                        f"[Executor] '{plan.name}' RETRIES ESGOTADOS — resetando episódio"
                    )
                    self.kb.active_plan = None
                    return action, {"trigger_reset": True}
            else:
                logger.warning(f"[Executor] '{step.name}' TIMEOUT (sem retry) → avançando")
                plan.advance()

        if plan.is_complete:
            logger.info(f"[Executor] Plano '{plan.name}' COMPLETO — retornando ao controle normal")
            self.kb.active_plan = None

        return action, {}
