import re


class AdaptationEvaluator:
    """
    Evaluates whether an applied adaptation resolved the originally violated then-conditions.

    States
    ------
    idle       → start()               → waiting
    waiting    → subtask changes away  → evaluating
    evaluating → then-conditions met   → success
               → SAFE_ABORT received   → failure (reason="safe_abort")
               → tick limit reached    → failure (reason="timeout")

    Call evaluate(sm_tick) on every tick; it returns None while idle and a
    status dict otherwise. Terminal states keep returning the same final result.
    """

    def __init__(self, max_eval_ticks: int = 30):
        self._max_eval_ticks   = max_eval_ticks
        self._status           = "idle"
        self._then_expr: str | None  = None
        self._adaptive_subtask: str | None = None
        self._candidate_name: str | None   = None
        self._eval_ticks = 0
        self._result: dict | None = None

    # ── public API ────────────────────────────────────────────────────────────

    def start(self, diagnosed: dict, adaptation: dict) -> None:
        """Activate evaluator after an adaptation is sent. Called once per episode."""
        self._then_expr        = diagnosed.get("then")
        self._adaptive_subtask = _do_to_subtask(adaptation.get("do", ""))
        self._candidate_name   = adaptation.get("candidate_name")
        self._status           = "waiting"
        self._eval_ticks       = 0
        self._result           = None

    def reset(self) -> None:
        """Reset for a new episode."""
        self._status           = "idle"
        self._then_expr        = None
        self._adaptive_subtask = None
        self._candidate_name   = None
        self._eval_ticks       = 0
        self._result           = None

    def evaluate(self, sm_tick: dict) -> dict | None:
        """
        Call every tick with the normalised SM parameters dict.
        Returns None when idle; a status dict otherwise.
        """
        if self._status == "idle":
            return None
        if self._status in ("success", "failure"):
            return self._result

        current_subtask = (sm_tick.get("current_subtask") or "").upper()

        if self._status == "waiting":
            # Stay waiting while the adaptive task is still running.
            # As soon as the subtask changes (adaptive task done), start evaluating.
            if current_subtask and current_subtask != self._adaptive_subtask:
                self._status = "evaluating"
            else:
                return {"status": "waiting", "candidate": self._candidate_name,
                        "adaptive_subtask": self._adaptive_subtask}

        # ── evaluating ────────────────────────────────────────────────────────
        self._eval_ticks += 1

        if current_subtask == "SAFE_ABORT":
            return self._finalise("failure", "safe_abort")

        if self._eval_ticks >= self._max_eval_ticks:
            return self._finalise("failure", "timeout")

        if self._then_satisfied(sm_tick):
            return self._finalise("success", "then_satisfied")

        return {
            "status":    "evaluating",
            "ticks":     self._eval_ticks,
            "candidate": self._candidate_name,
            "then":      self._then_expr,
        }

    @property
    def status(self) -> str:
        return self._status

    @property
    def result(self) -> dict | None:
        return self._result

    # ── private ───────────────────────────────────────────────────────────────

    def _then_satisfied(self, sm_tick: dict) -> bool:
        """Evaluate the then-expression against the current SM tick parameters."""
        if not self._then_expr:
            return False
        clauses = [c.strip() for c in self._then_expr.split(" AND ")]
        try:
            return all(eval(c, {}, sm_tick) for c in clauses)
        except Exception:
            return False

    def _finalise(self, status: str, reason: str) -> dict:
        self._status = status
        self._result = {
            "status":    status,
            "reason":    reason,
            "ticks":     self._eval_ticks,
            "candidate": self._candidate_name,
            "then":      self._then_expr,
        }
        return self._result


def _do_to_subtask(do: str) -> str:
    """'apply_vacuum_assist()' → 'APPLY_VACUUM_ASSIST'"""
    return re.sub(r"\(.*?\)", "", do).upper().strip()
