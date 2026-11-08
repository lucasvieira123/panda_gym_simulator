"""Translates the managed system's subtask changes into ASM-SM events.

Domain and adaptive scenarios use a fixed map: when a subtask ends, its scenario's Do event fires.

An evolved scenario's Do (e.g. apply_vacuum_assist()) is followed by the task of the scenario it
evolved from (e.g. the transport resumes), and its Then (inherited from that scenario) only holds
after both. Its event therefore fires when the managed system leaves that phase: the subtasks of
its Do and of its origin scenario.
"""
import re

# current_subtask (upper case) -> ASM-SM event of the initial ASM
DOMAIN_EVENTS = {
    "APPROACH_OBJECT":  "approach_object() (APPROACH_OBJECT)",
    "GRASP_OBJECT":     "close_gripper() (GRASP_OBJECT)",
    "RETRY_GRASP":      "retry_grasp() (RETRY_GRASP)",
    "SAFE_ABORT":       "abort_grasp() (SAFE_ABORT)",
    "LIFT_OBJECT":      "lift_object() (LIFT_OBJECT)",
    "TRANSPORT_OBJECT": "transport_to_goal() (TRANSPORT_OBJECT)",
    "PLACE_OBJECT":     "place_object() (PLACE_OBJECT)",
}

_KEYWORDS = {"AND", "OR", "NOT", "and", "or", "not", "True", "False", "true", "false"}


def _do_subtask(do: str) -> str:
    return re.sub(r"\(.*?\)", "", do).strip().upper()


class SubtaskEventMapper:
    def __init__(self, asm: dict) -> None:
        scenarios = asm.get("scenarios", {})
        # event of each evolved scenario -> subtasks of its phase
        self.evolved_phases: dict[str, set[str]] = {}
        for s in scenarios.values():
            if s.get("type") != "evolutionary":
                continue
            origin = scenarios.get(s.get("evolved_from", ""), {}).get("name", "")
            self.evolved_phases[f"{s['do']} ({s['name']})"] = {_do_subtask(s["do"]), origin} - {""}
        # variables the ASM-SM guards use (e.g. lateral_friction in an evolved Given)
        text = " ".join(s.get(k, "") for s in scenarios.values() for k in ("given", "when", "then"))
        self.variables = sorted(set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text)) - _KEYWORDS)

    def action(self, prev_subtask: str | None, subtask: str, task_complete: bool,
               awaited_events: set[str]) -> str | None:
        """Event for this tick, or None. Called with the subtask of the previous and the current tick."""
        changed = bool(prev_subtask) and subtask != prev_subtask
        if not (changed or task_complete):
            return None
        awaited = sorted(e for e in awaited_events if e in self.evolved_phases)
        if awaited:
            phase = self.evolved_phases[awaited[0]]
            if prev_subtask in phase:
                return awaited[0] if (task_complete or subtask not in phase) else None
        return DOMAIN_EVENTS.get(prev_subtask)
