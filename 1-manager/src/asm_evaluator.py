from asm_loader import Asm, AsmScenario
from ts import ts


def _normalise(expr: str) -> str:
    """Converts ASM expression syntax to valid Python for eval()."""
    if not expr or expr.strip() in ("*", ""):
        return "True"
    return (
        expr
        .replace(" AND ", " and ")
        .replace(" OR ",  " or ")
        .replace(" NOT ", " not ")
        .replace("true",  "True")
        .replace("false", "False")
    )


def _eval(expr: str, context: dict) -> bool:
    try:
        return bool(eval(_normalise(expr), {"__builtins__": {}}, context))
    except Exception:
        return False


class AsmEvaluator:
    """
    Navigates the ASM transition graph step by step.

    At each step, evaluates the candidates reachable from current_node
    against the current perception context.  Returns the matched scenario
    (domain or adaptive) or None when no candidate applies yet.
    Advances current_node automatically when a match is found.
    """

    def __init__(self, asm: Asm) -> None:
        self._asm              = asm
        self._current_node     = "__init__"
        self._pending_transition: str | None = None  # candidato cujas condições já foram validadas

    # ── public ──────────────────────────────────────────────────────────────────

    @property
    def current_node(self) -> str:
        return self._current_node

    @property
    def done(self) -> bool:
        return self._current_node == "__end__"

    def reset(self) -> None:
        self._current_node        = "__init__"
        self._pending_transition  = None

    def evaluate(self, context: dict) -> AsmScenario | None:
        """
        Evaluates candidates reachable from current_node.

        Returns:
          AsmScenario  — matched scenario (check .type for "adaptive" vs "domain")
          None         — no candidate matched yet (mid-task) or execution is done
        """
        if self.done:
            return None

        candidates = self._asm.transition_graph.get(self._current_node, [])

        for candidate_key in candidates:

            # structural sentinel nodes handled explicitly
            if candidate_key == "__end__":
                self._advance_to_end(context)
                continue
            if candidate_key not in self._asm.scenarios:
                continue

            scenario = self._asm.scenarios.get(candidate_key)
            if scenario is None:
                continue

            # ── ROLLBACK ──────────────────────────────────────────────────────
            # Comportamento original: avança por given+when para todos os tipos.
            # Problema: ASM 1-tick adiantado nos cenários de domínio.
            # Para reverter: descomenta as 4 linhas abaixo e apaga o bloco novo.
            # if _eval(scenario.given, context) and _eval(scenario.when, context):
            #     prev = self._current_node
            #     self._current_node = candidate_key
            #     tag = "[ADAPT]" if scenario.type == "adaptive" else "[OK]"
            #     print(f"[{ts()}][ASM] {tag} {prev} → {candidate_key}  (type={scenario.type})")
            #     return scenario
            # ──────────────────────────────────────────────────────────────────

            should_advance = False
            if scenario.type == "adaptive":
                # Trigger por condições — manager precisa detectar para agir
                should_advance = _eval(scenario.given, context) and _eval(scenario.when, context)
            else:
                # Domain — duas fases:
                #
                # Fase 1 (subtask ainda não mudou): avalia condições e marca pending
                #   → validação acontece aqui, no contexto correto (último step do cenário atual)
                #
                # Fase 2 (subtask mudou): avança o ASM usando o pending como prova de validade
                #   → se não havia pending: managing transitou sem condições validadas → [WARN]

                # Fase 1: marcar pending quando condições satisfeitas
                if self._pending_transition != candidate_key:
                    if _eval(scenario.given, context) and _eval(scenario.when, context):
                        self._pending_transition = candidate_key
                        print(f"[{ts()}][ASM] [PENDING] {self._current_node} → {candidate_key}: condições satisfeitas, aguardando managing")
                else:
                    print(f"[{ts()}][ASM] [PENDING] {self._current_node} → {candidate_key}: aguardando managing (já validado)")

                # Fase 2: avançar quando managing já está neste cenário
                if context.get("current_subtask") == scenario.name:
                    should_advance = True
                    if self._pending_transition != candidate_key:
                        print(f"[{ts()}][ASM] [WARN] {self._current_node} → {candidate_key}: managing transitou sem condições validadas")
                    self._pending_transition = None

            if should_advance:
                prev = self._current_node
                self._current_node = candidate_key
                tag = "[ADAPT]" if scenario.type == "adaptive" else "[OK]"
                print(f"[{ts()}][ASM] {tag} {prev} → {candidate_key}  (type={scenario.type})")
                return scenario

        return None

    # ── private ─────────────────────────────────────────────────────────────────

    def _advance_to_end(self, context: dict) -> None:
        """Advances to __end__ when the current scenario's 'then' is satisfied."""
        current_scenario = self._asm.scenarios.get(self._current_node)
        if current_scenario is None:
            return
        if _eval(current_scenario.then, context):
            print(f"[{ts()}][ASM] [DONE] {current_scenario.name} → __end__")
            self._current_node = "__end__"
