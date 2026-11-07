MAX_ATTEMPTS = 2


def decide_after_attempt(evaluation: dict, attempts_used: int, candidates_available: int, observed: dict) -> dict | None:
    """
    After a terminal adaptation result, chooses between trying the next ranked candidate and
    the fail-safe. Returns None when the adaptation succeeded.

    Retry needs an object that is not secured, is still on the table and a task still running.
    It does not reuse the diagnosed When or height clauses: a failed attempt invalidates them
    (grasp_completed returns to 0, and in transport they contradict each other).
    """
    if evaluation["status"] == "success":
        return None
    if attempts_used >= MAX_ATTEMPTS:
        return _fail_safe("attempts_exhausted")
    if attempts_used >= candidates_available:
        return _fail_safe("no_candidate_left")
    if observed.get("is_success"):
        return _fail_safe("sequence_ended")
    if observed.get("cube_z", 0.0) < 0.0:  # o tampo da mesa está em z = 0
        return _fail_safe("object_off_table")
    if observed.get("finger_contacts", 0) >= 2:
        return _fail_safe("object_held_but_postconditions_failed")
    return {"action": "retry", "reason": evaluation["reason"]}


def _fail_safe(reason: str) -> dict:
    return {"action": "fail_safe", "reason": reason}
