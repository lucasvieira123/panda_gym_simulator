"""
plan.py
-------
Core planning abstractions for the MAPE-K Executor.

PlanStep models a single action in a STRIPS-style plan:
  precondition  →  run action  →  completion (effect)

SequentialPlan is an ordered list of PlanSteps with:
  - advance()  : move to the next step on success
  - retry()    : jump back to a named step on failure (limited attempts)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable, Dict, List, Optional

import numpy as np

if TYPE_CHECKING:
    from knowledge_base import Observation


# ---------------------------------------------------------------------------
# PlanStep
# ---------------------------------------------------------------------------

@dataclass
class PlanStep:
    """
    One step in a sequential plan.

    Fields
    ------
    name           : human-readable identifier (also used as retry jump target)
    precondition   : obs → bool  — state that must be true to enter this step
    action_fn      : obs → ndarray(4,) — action vector sent to panda-gym
    completion_fn  : obs → bool  — true when this step has succeeded
    max_steps      : hard timeout; step is forcibly resolved after this many ticks
    retry_target   : on timeout, jump back to this step name (None = just advance)
    """
    name:          str
    precondition:  Callable[["Observation"], bool]
    action_fn:     Callable[["Observation"], np.ndarray]
    completion_fn: Callable[["Observation"], bool]
    max_steps:     int
    retry_target:  Optional[str] = None

    # Execution state (not part of the plan spec, reset on retry)
    _elapsed: int = field(default=0, init=False, repr=False)

    def tick(self) -> None:
        """Increment the step's elapsed counter."""
        self._elapsed += 1

    def reset(self) -> None:
        """Reset elapsed counter (used when retrying from this step)."""
        self._elapsed = 0

    @property
    def elapsed(self) -> int:
        return self._elapsed

    @property
    def timed_out(self) -> bool:
        return self._elapsed >= self.max_steps


# ---------------------------------------------------------------------------
# SequentialPlan
# ---------------------------------------------------------------------------

class SequentialPlan:
    """
    Ordered execution of PlanSteps with retry/branching support.

    Normal execution:   step 0 → step 1 → … → step N → complete
    On step timeout:
      - if step has retry_target and retries remain → jump back
      - otherwise → advance anyway (best-effort) or signal failure
    """

    def __init__(
        self,
        name:        str,
        steps:       List[PlanStep],
        max_retries: int = 3,
    ):
        self.name        = name
        self.steps       = steps
        self.max_retries = max_retries

        # index lookup for jump-back targets
        self._idx:          Dict[str, int] = {s.name: i for i, s in enumerate(steps)}
        self._current:      int = 0
        self._retry_count:  int = 0

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def current_step(self) -> PlanStep:
        return self.steps[self._current]

    @property
    def is_complete(self) -> bool:
        return self._current >= len(self.steps)

    @property
    def retry_count(self) -> int:
        return self._retry_count

    @property
    def retry_exhausted(self) -> bool:
        return self._retry_count >= self.max_retries

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------

    def advance(self) -> None:
        """Move forward to the next step."""
        self._current += 1

    def retry(self) -> bool:
        """
        Jump back to retry_target of the current step.
        Returns True on success, False when retries are exhausted.
        """
        step = self.current_step
        if step.retry_target is None or self.retry_exhausted:
            return False

        target_idx = self._idx[step.retry_target]
        self._retry_count += 1
        self._current = target_idx

        # reset elapsed counters from the jump-back point onwards
        for s in self.steps[target_idx:]:
            s.reset()

        return True

    def __repr__(self) -> str:
        if self.is_complete:
            return f"SequentialPlan(name={self.name!r}, COMPLETE)"
        return (
            f"SequentialPlan(name={self.name!r}, "
            f"step={self.current_step.name!r} "
            f"[{self._current}/{len(self.steps)}], "
            f"retries={self._retry_count}/{self.max_retries})"
        )
