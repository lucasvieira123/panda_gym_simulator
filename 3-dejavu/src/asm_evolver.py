import json
import re
from pathlib import Path


_OP_NEG = {
    ">=": "<", "<=": ">", "==": "!=", "!=": "==", ">": "<=", "<": ">=",
}


def _negate_clause(clause: str) -> str:
    s = clause.strip()
    m = re.match(r"^(.*?)(>=|<=|==|!=|>|<)(.*)$", s)
    if not m:
        return f"not ({s})"
    left, op, right = m.group(1).strip(), m.group(2), m.group(3).strip()
    return f"{left} {_OP_NEG[op]} {right}"


def _negate_conditions(conditions_str: str) -> str:
    """Negates each AND-joined clause independently."""
    clauses = [c.strip() for c in conditions_str.split(" AND ")]
    negated = [_negate_clause(c) for c in clauses if c]
    if len(negated) == 1:
        return negated[0]
    return " AND ".join(f"({c})" for c in negated)


def _derive_new_key(violated_key: str, do: str) -> str:
    """'lift_object' + 'apply_vacuum_assist()' → 'lift_object_vacuum_assist'"""
    action = re.sub(r"\(.*?\)", "", do).lower().strip()
    for prefix in ("apply_", "use_", "do_", "execute_"):
        if action.startswith(prefix):
            action = action[len(prefix):]
            break
    return f"{violated_key}_{action}"


class AsmEvolver:
    """
    Evolves the ASM after a confirmed successful adaptation.

    Two mutations are applied atomically to asm.json:

    1. Narrow the violated scenario — adds NOT(diagnostic_conditions) to its
       `given`, eliminating non-determinism with the new scenario.

    2. Create a new adaptive scenario — inherits the violated scenario's
       `when`/`then` and all its incoming/outgoing transitions, but uses the
       original `given` narrowed by diagnostic_conditions and the recommended `do`.

    The updated file is written back to disk. The Manager must be restarted
    (or implement hot-reload) to pick up the changes.
    """

    def __init__(self, asm_path: str) -> None:
        self._asm_path = Path(asm_path)

    def evolve(
        self,
        identified: dict,
        diagnosed: dict,
        adaptation: dict,
    ) -> dict:
        """
        Parameters
        ----------
        identified  : from UnanticipatedScenarioIdentifier.identifies()
                      requires 'anticipated_id' — the dict key in asm["scenarios"]
        diagnosed   : from UnanticipatedScenarioDiagnoser.diagnosis()
                      requires 'diagnostic_conditions' — raw conditions from the DT
        adaptation  : from SimilarityBasedAdapter.recommend()
                      requires 'do' — the recommended action call

        Returns
        -------
        dict with keys: violated_key, updated_given, new_scenario_key, new_scenario
        """
        asm = self._load()

        violated_key          = identified["anticipated_id"]
        diagnostic_conditions = diagnosed["diagnostic_conditions"]
        new_do                = adaptation["do"]

        if violated_key not in asm.get("scenarios", {}):
            raise KeyError(f"Cenário '{violated_key}' não encontrado no ASM.")

        original       = asm["scenarios"][violated_key]
        original_given = original["given"]

        # ── 1. Narrow the violated scenario (eliminates non-determinism) ───────
        negated = _negate_conditions(diagnostic_conditions)
        original["given"] = f"{original_given} AND {negated}"

        # ── 2. Create the new adaptive scenario ──────────────────────────────
        new_key      = _derive_new_key(violated_key, new_do)
        new_name     = new_key.upper()
        new_scenario = {
            "name":  new_name,
            "type":  "evolutionary",
            "given": f"{original_given} AND {diagnostic_conditions}",
            "when":  original["when"],
            "do":    new_do,
            "then":  original["then"],
        }
        asm["scenarios"][new_key] = new_scenario

        # ── 3. Inherit transitions from the violated scenario ─────────────────
        inherited = []
        for tr in asm.get("transitions", []):
            if tr["from"] == violated_key:
                inherited.append({"from": new_key, "to": tr["to"]})
            elif tr["to"] == violated_key:
                inherited.append({"from": tr["from"], "to": new_key})
        asm["transitions"].extend(inherited)

        # ── 4. Persist ────────────────────────────────────────────────────────
        self._save(asm)

        return {
            "violated_key":     violated_key,
            "updated_given":    original["given"],
            "new_scenario_key": new_key,
            "new_scenario":     new_scenario,
        }

    def _load(self) -> dict:
        with open(self._asm_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save(self, asm: dict) -> None:
        with open(self._asm_path, "w", encoding="utf-8") as f:
            json.dump(asm, f, indent=2, ensure_ascii=False)
