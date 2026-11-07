"""
Applicability filter of the Retriever: only candidates whose When matches the
diagnosed scenario's When go on to the similarity calculation.

Two Whens match when they have the same AND-joined clauses, ignoring whitespace,
outer parentheses and clause order. There is no semantic comparison:
"10 <= x" does not match "x >= 10".
"""
import re

_AND = re.compile(r"\s+AND\s+")
_OPERATOR = re.compile(r"\s*(<=|>=|==|!=|<|>)\s*")
_WHITESPACE = re.compile(r"\s+")


def _strip_outer_parentheses(expression: str) -> str:
    expression = expression.strip()
    while expression.startswith("(") and expression.endswith(")"):
        depth = 0
        for i, char in enumerate(expression):
            depth += {"(": 1, ")": -1}.get(char, 0)
            if depth == 0 and i < len(expression) - 1:
                return expression  # the first "(" closes before the end
        expression = expression[1:-1].strip()
    return expression


def _normalize_clause(clause: str) -> str:
    clause = _strip_outer_parentheses(clause)
    clause = _OPERATOR.sub(r" \1 ", clause)
    return _WHITESPACE.sub(" ", clause).strip()


def normalize_when(expression: str | None) -> frozenset[str]:
    if not expression:
        return frozenset()
    clauses = _AND.split(_strip_outer_parentheses(expression))
    return frozenset(c for c in map(_normalize_clause, clauses) if c)


def when_matches(when_1: str | None, when_2: str | None) -> bool:
    normalized = normalize_when(when_1)
    return bool(normalized) and normalized == normalize_when(when_2)


def filter_candidates_by_when(diagnosed_when: str | None, candidates: list[dict]) -> tuple[list[dict], list[dict]]:
    """Splits candidates, keeping their order, into (applicable, excluded)."""
    applicable, excluded = [], []
    for candidate in candidates:
        target = applicable if when_matches(diagnosed_when, candidate.get("when")) else excluded
        target.append(candidate)
    return applicable, excluded
