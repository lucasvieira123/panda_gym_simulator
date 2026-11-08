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
    """Negates an AND-joined conjunction: NOT (a AND b) = (NOT a OR NOT b)."""
    clauses = [c.strip() for c in conditions_str.split(" AND ")]
    negated = [_negate_clause(c) for c in clauses if c]
    if len(negated) == 1:
        return negated[0]
    return "(" + " OR ".join(negated) + ")"


class EvolutionRejected(Exception):
    """The ASM is left unchanged; `reason` says why."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def _split_top_level_and(expr: str) -> list[str]:
    """Splits on AND outside parentheses."""
    parts, depth, start, i = [], 0, 0, 0
    while i < len(expr):
        ch = expr[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif depth == 0 and expr.startswith(" AND ", i):
            parts.append(expr[start:i].strip())
            i += len(" AND ")
            start = i
            continue
        i += 1
    parts.append(expr[start:].strip())
    return [p for p in parts if p]


def _variables(expr: str) -> set[str]:
    return set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr)) - {"AND", "OR", "NOT", "True", "False"}


def _holds(expr: str, context: dict) -> bool:
    python = expr.replace(" AND ", " and ").replace(" OR ", " or ").replace("NOT ", "not ")
    return bool(eval(python, {"__builtins__": {}}, context))


def _uncovered_clauses(given: str, witness: dict) -> list[str]:
    """Clauses of `given` over the witness variables that the witness does not satisfy."""
    return [c for c in _split_top_level_and(given)
            if _variables(c) and _variables(c) <= witness.keys() and not _holds(c, witness)]


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
        context: dict | None = None,
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
        context     : observed values of the run; those of the diagnosed variables must satisfy the
                      new scenario's Given, which must therefore cover the situation that produced it

        Returns
        -------
        dict with keys: violated_key, updated_given, new_scenario_key, new_scenario

        Raises
        ------
        EvolutionRejected when the new scenario's key already exists or its Given does not cover the
        observed situation (e.g. an empty region); the ASM is then left unchanged.
        """
        asm = self._load()

        violated_key          = identified["anticipated_id"]
        diagnostic_conditions = diagnosed["diagnostic_conditions"]
        new_do                = adaptation["do"]

        if violated_key not in asm.get("scenarios", {}):
            raise KeyError(f"Cenário '{violated_key}' não encontrado no ASM.")

        original       = asm["scenarios"][violated_key]
        original_given = original["given"]
        new_key        = _derive_new_key(violated_key, new_do)
        new_given      = f"{original_given} AND {diagnostic_conditions}"

        # ── 0. Safeguards (Q3 and P2 in 5-experiments/RQ1.2/decisions.md) ─────
        if new_key in asm["scenarios"]:
            raise EvolutionRejected("scenario_key_exists", f"'{new_key}' já existe no ASM")
        if context is not None:
            witness = {v: context[v] for v in _variables(diagnostic_conditions) if context.get(v) is not None}
            uncovered = _uncovered_clauses(new_given, witness)
            if uncovered:
                raise EvolutionRejected(
                    "given_does_not_cover_situation",
                    f"com {witness}, não valem {uncovered} no Given '{new_given}'",
                )

        # ── 1. Narrow the violated scenario (eliminates non-determinism) ───────
        negated = _negate_conditions(diagnostic_conditions)
        original["given"] = f"{original_given} AND {negated}"

        # ── 2. Create the new adaptive scenario ──────────────────────────────
        new_name     = new_key.upper()
        new_scenario = {
            "name":  new_name,
            "type":  "evolutionary",
            "given": new_given,
            "when":  original["when"],
            "do":    new_do,
            "then":  original["then"],
        }
        asm["scenarios"][new_key] = new_scenario

        # ── 3. Inherit transitions from the violated scenario ─────────────────
        existing  = {(tr["from"], tr["to"]) for tr in asm.get("transitions", [])}
        inherited = []
        for tr in asm.get("transitions", []):
            if tr["from"] == violated_key:
                pair = (new_key, tr["to"])
            elif tr["to"] == violated_key:
                pair = (tr["from"], new_key)
            else:
                continue
            if pair not in existing:
                existing.add(pair)
                inherited.append({"from": pair[0], "to": pair[1]})
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
