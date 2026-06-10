"""
knowledge_base.py
-----------------
The K in MAPE-K.

Holds everything the four components need to communicate:
  - Observation  : one timestep of sensor data from panda-gym
  - KnowledgeBase: shared store (history, active plan, adaptation log, context)
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

import numpy as np

if TYPE_CHECKING:
    from plan import SequentialPlan


# ---------------------------------------------------------------------------
# Observation — typed snapshot of one panda-gym timestep
# ---------------------------------------------------------------------------

@dataclass
class Observation:
    """
    Structured view of a single panda-gym step.

    PandaPickAndPlaceDense-v3 observation layout (20 floats total):
      obs[0:3]  ee_pos            end-effector position
      obs[3:6]  ee_vel            end-effector velocity
      obs[6]    fingers_width     gripper opening (0=closed, ~0.08=open)
      obs[7:10] object_pos        object position  (= achieved_goal)
      obs[10:14] object_rot       object quaternion
      obs[14:17] object_vel       object linear velocity
      obs[17:20] object_ang_vel   object angular velocity
    """
    step:          int
    ee_pos:        np.ndarray   # shape (3,)
    fingers_width: float        # scalar
    object_pos:    np.ndarray   # shape (3,)
    object_vel:    np.ndarray   # shape (3,)
    desired_goal:  np.ndarray   # shape (3,) — target position
    reward:        float
    timestamp:     float = field(default_factory=time.time)

    # ------------------------------------------------------------------
    # Derived quantities used by Analyzer and plan steps
    # ------------------------------------------------------------------

    @property
    def dist_ee_to_object(self) -> float:
        return float(np.linalg.norm(self.ee_pos - self.object_pos))

    @property
    def dist_object_to_goal(self) -> float:
        return float(np.linalg.norm(self.object_pos - self.desired_goal))

    @property
    def vertical_separation(self) -> float:
        """Positive value = ee is above the object."""
        return float(self.ee_pos[2] - self.object_pos[2])

    @property
    def gripper_is_closed(self) -> bool:
        return self.fingers_width < 0.05


# ---------------------------------------------------------------------------
# AdaptationEvent — one logged activation of a plan
# ---------------------------------------------------------------------------

@dataclass
class AdaptationEvent:
    step:      int
    plan_name: str
    trigger:   str
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# KnowledgeBase
# ---------------------------------------------------------------------------

class KnowledgeBase:
    """
    Central shared store for Monitor, Analyzer, Planner, and Executor.

    Responsibilities:
      - Keep a rolling window of Observation objects
      - Hold the currently-executing SequentialPlan (or None)
      - Maintain an adaptation log for history-aware decisions
      - Pass diagnostic context from Analyzer to Planner
    """

    def __init__(self, history_size: int = 50):
        self.history:         deque[Observation]  = deque(maxlen=history_size)
        self.active_plan:     Optional[SequentialPlan] = None
        self.adaptation_log:  List[AdaptationEvent]    = []
        self.context:         Dict[str, Any]           = {}
        self.current_step:    int = 0
        self.episode:         int = 0

    # ------------------------------------------------------------------
    # Writers
    # ------------------------------------------------------------------

    def push(self, obs: Observation) -> None:
        self.history.append(obs)
        self.current_step = obs.step

    def log_adaptation(self, plan_name: str, trigger: str) -> None:
        self.adaptation_log.append(
            AdaptationEvent(self.current_step, plan_name, trigger)
        )

    # ------------------------------------------------------------------
    # Readers
    # ------------------------------------------------------------------

    def last(self) -> Optional[Observation]:
        return self.history[-1] if self.history else None

    def recent(self, n: int) -> List[Observation]:
        return list(self.history)[-n:]

    @property
    def n_adaptations(self) -> int:
        return len(self.adaptation_log)
