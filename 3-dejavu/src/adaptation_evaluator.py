import re


class AdaptationEvaluator:
    """
    Evaluates whether an applied adaptation resolved the originally violated then-conditions.

    Flow
    ----
    idle → start() → dispatched → running → evaluating → terminal

    dispatched : the adaptive subtask has not been observed yet
    running    : the adaptive subtask is executing
    evaluating : the adaptive subtask ended; the diagnosed Then is checked every tick

    Terminal results
    ----------------
    success         then_satisfied
    failure         postconditions_not_met | sequence_ended | safe_abort
    timeout         adaptive_task_not_finished
    execution_error adaptation_not_started | postcondition_not_observable

    The decision uses the diagnosed Then. The candidate's own Then is only reported,
    clause by clause, because it may use parameters that have no sensor.

    Call evaluate(sm_tick, sequence_done) on every tick. It returns None while idle and
    a status dict otherwise. Terminal states keep returning the same final result.
    """

    TERMINAL = ("success", "failure", "timeout", "execution_error")

    def __init__(self, max_eval_ticks: int = 30, max_start_ticks: int = 5, max_run_ticks: int = 60):
        self._max_eval_ticks  = max_eval_ticks
        self._max_start_ticks = max_start_ticks
        self._max_run_ticks   = max_run_ticks
        self.reset()

    # ── public API ────────────────────────────────────────────────────────────

    def start(self, diagnosed: dict, adaptation: dict) -> None:
        """Activate evaluator after an adaptation is sent. Called once per episode."""
        self._then_expr        = diagnosed.get("then")
        self._adaptive_subtask = _do_to_subtask(adaptation.get("do", ""))
        self._candidate_name   = adaptation.get("candidate_name")
        self._candidate_then   = adaptation.get("then")
        self._status           = "dispatched"
        self._start_ticks      = 0
        self._run_ticks        = 0
        self._eval_ticks       = 0
        self._result           = None

    def reset(self) -> None:
        """Reset for a new episode."""
        self._status           = "idle"
        self._then_expr: str | None        = None
        self._adaptive_subtask: str | None = None
        self._candidate_name: str | None   = None
        self._candidate_then: str | None   = None
        self._start_ticks      = 0
        self._run_ticks        = 0
        self._eval_ticks       = 0
        self._result: dict | None = None

    def evaluate(self, sm_tick: dict, sequence_done: bool = False) -> dict | None:
        """
        Call every tick with the normalised SM parameters dict.
        Returns None when idle; a status dict otherwise.
        """
        if self._status == "idle":
            return None
        if self._status in self.TERMINAL:
            return self._result

        current_subtask = (sm_tick.get("current_subtask") or "").upper()

        if self._status == "dispatched":
            if current_subtask == self._adaptive_subtask:
                self._status = "running"
            else:
                self._start_ticks += 1
                if self._start_ticks >= self._max_start_ticks:
                    return self._finalise("execution_error", "adaptation_not_started", sm_tick)
                return self._progress("waiting")

        if self._status == "running":
            if current_subtask == self._adaptive_subtask or not current_subtask:
                self._run_ticks += 1
                if self._run_ticks >= self._max_run_ticks:
                    return self._finalise("timeout", "adaptive_task_not_finished", sm_tick)
                return self._progress("waiting")
            self._status = "evaluating"

        self._eval_ticks += 1

        if current_subtask == "SAFE_ABORT":
            return self._finalise("failure", "safe_abort", sm_tick)

        clauses = _check_clauses(self._then_expr, sm_tick)
        if any(c["state"] == "not_observed" for c in clauses):
            return self._finalise("execution_error", "postcondition_not_observable", sm_tick)
        if self._eval_ticks >= self._max_eval_ticks:
            return self._finalise("failure", "postconditions_not_met", sm_tick)
        if clauses and all(c["state"] == "satisfied" for c in clauses):
            return self._finalise("success", "then_satisfied", sm_tick)
        if sequence_done:
            return self._finalise("failure", "sequence_ended", sm_tick)

        return self._progress("evaluating")

    @property
    def status(self) -> str:
        return self._status

    @property
    def result(self) -> dict | None:
        return self._result

    # ── private ───────────────────────────────────────────────────────────────

    def _progress(self, status: str) -> dict:
        return {
            "status":           status,
            "candidate":        self._candidate_name,
            "adaptive_subtask": self._adaptive_subtask,
            "ticks":            self._eval_ticks,
            "run_ticks":        self._run_ticks,
            "then":             self._then_expr,
        }

    def _finalise(self, status: str, reason: str, sm_tick: dict) -> dict:
        self._status = status
        self._result = {
            "status":           status,
            "reason":           reason,
            "candidate":        self._candidate_name,
            "adaptive_subtask": self._adaptive_subtask,
            "ticks":            self._eval_ticks,
            "run_ticks":        self._run_ticks,
            "start_ticks":      self._start_ticks,
            "then":             self._then_expr,
            "then_clauses":     _check_clauses(self._then_expr, sm_tick),
            "candidate_then":   _check_clauses(self._candidate_then, sm_tick),
        }
        return self._result


def _check_clauses(expression: str | None, sm_tick: dict) -> list[dict]:
    """Evaluates each AND clause: satisfied, unsatisfied, or not_observed when a parameter has no value."""
    if not expression:
        return []
    results = []
    for clause in (c.strip() for c in expression.split(" AND ")):
        parameter = re.match(r"\(?\s*(\w+)", clause).group(1)
        if parameter not in sm_tick:
            results.append({"clause": clause, "state": "not_observed", "value": None})
            continue
        try:
            state = "satisfied" if eval(clause, {}, sm_tick) else "unsatisfied"
        except Exception:
            state = "not_observed"
        results.append({"clause": clause, "state": state, "value": sm_tick[parameter]})
    return results


def _do_to_subtask(do: str) -> str:
    """'apply_vacuum_assist()' → 'APPLY_VACUUM_ASSIST'"""
    return re.sub(r"\(.*?\)", "", do).upper().strip()
