from __future__ import annotations

import os
from typing import List

import yaml


DEFAULT_RULES_PATH = os.path.join("configs", "adaptation_options.yaml")

_OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    ">":  lambda a, b: a > b,
    "<":  lambda a, b: a < b,
}


def _parse_value(raw: str):
    s = raw.strip()
    if s.lower() == "true":  return True
    if s.lower() == "false": return False
    try:                     return float(s)
    except ValueError:       return s


def _eval_condition(expr: str, context: dict) -> bool:
    """Avalia uma condição 'campo op valor' contra o contexto monitorado."""
    for op in ("==", "!=", ">=", "<=", ">", "<"):
        if op in expr:
            field, raw = expr.split(op, 1)
            field    = field.strip()
            expected = _parse_value(raw)
            actual   = context.get(field)
            if actual is None:
                return False
            try:
                return _OPS[op](actual, expected)
            except TypeError:
                return False
    raise ValueError(f"Condição sem operador reconhecido: {expr!r}")


class Analyzer:
    """
    A — Analyze

    Responsabilidade:
      Carregar as regras Given/Then de adaptation_rules.yaml e avaliá-las
      contra o contexto monitorado a cada step.

    Retorna a lista das regras cujas condições 'given' são todas verdadeiras.
    """

    def __init__(self, rules_path: str = DEFAULT_RULES_PATH):
        self._rules = self._load_rules(rules_path)

    def analyze(self, context: dict, step_count: int) -> List[dict]:
        """
        Avalia todas as regras habilitadas.

        Condições dentro de cada regra têm AND implícito (todas precisam ser True).
        Regras diferentes são independentes (cada uma pode disparar sozinha).

        Retorna a lista das regras disparadas (dicts completos, incluindo 'execute').
        """
        triggered = []
        for rule in self._rules:
            if not rule.get("enabled", True):
                continue
            conditions = rule.get("given", [])
            if all(_eval_condition(cond, context) for cond in conditions):
                print(
                    f"[MAPE-K/Analyze] step={step_count:3d}"
                    f"  regra disparada: '{rule['id']}'"
                    f"  →  \"{rule['then']}\""
                )
                triggered.append(rule)
        return triggered

    @staticmethod
    def _load_rules(path: str) -> list:
        if not os.path.exists(path):
            print(f"[MAPE-K/Analyzer] Arquivo de regras não encontrado: {path!r} — nenhuma regra carregada.")
            return []
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        rules   = data.get("rules", [])
        enabled = [r for r in rules if r.get("enabled", True)]
        print(f"[MAPE-K/Analyzer] {len(enabled)}/{len(rules)} regra(s) ativa(s) carregada(s) de {path!r}")
        return rules
