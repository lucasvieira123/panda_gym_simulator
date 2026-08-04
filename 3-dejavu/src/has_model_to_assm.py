import json
import re
import sys
from pathlib import Path

import yaml

from constants import PROJECT_ROOT

# ── Expression helpers ────────────────────────────────────────────────────────

def normalize_expr(expr: str) -> str:
    """Convert hAS model expression syntax to Sismic/Python syntax."""
    expr = expr.strip()
    if expr == "*":
        return "True"
    expr = re.sub(r'\bAND\b', 'and', expr)
    expr = re.sub(r'\bOR\b',  'or',  expr)
    expr = re.sub(r'\btrue\b',  'True',  expr)
    expr = re.sub(r'\bfalse\b', 'False', expr)
    return expr


def negate_expr(expr: str) -> str:
    return f"not ({expr})"


# ── Core transformation ───────────────────────────────────────────────────────

def has_to_assm(has_model: dict) -> dict:
    """
    Transform a hAS model dict into a Sismic statechart dict.

    Pattern per scenario (Given, When, Do, Then):

        PREV ──[When]──> PHI_n ──[Given]──> S_(n+1) ──[Do event]──> PHI_(n+2) ──[Then]──> S_(n+3) ──> NEXT
                              └─[not Given]─> ERR_n                           └─[not Then]─> ERR_(n+2)

    The When condition of scenario X is used as the guard on the transition
    that ENTERS X (i.e., from the previous scenario's end state).
    """
    scenarios = has_model["scenarios"]   # { id: {name,given,when,do,then} }

    # ── Filter __init__/__end__ sentinel transitions (fixed names) ────────────
    _SENTINELS = {"__init__", "__end__"}
    all_transitions   = has_model.get("transitions", [])
    transitions_clean = [
        t for t in all_transitions
        if t["from"] not in _SENTINELS and t["to"] not in _SENTINELS
    ]

    scenario_ids = list(scenarios.keys())

    # Assign base state number to each scenario: PHI_n where n = 4i+1
    state_nums = {sid: 4 * i + 1 for i, sid in enumerate(scenario_ids)}

    # Build adjacency maps from clean transitions only
    outgoing     = {sid: [] for sid in scenario_ids}
    has_incoming = {sid: False for sid in scenario_ids}
    for t in transitions_clean:
        outgoing[t["from"]].append(t["to"])
        has_incoming[t["to"]] = True

    # First scenario: explicit from __init__ transition, fallback to heuristic
    first_scenario = next(
        (t["to"] for t in all_transitions if t["from"] == "__init__"),
        next((sid for sid in scenario_ids if not has_incoming[sid]), scenario_ids[0])
    )

    states     = []
    err_states = set()

    # ── INIT ──────────────────────────────────────────────────────────────────
    first_when = normalize_expr(scenarios[first_scenario]["when"])
    states.append({
        "name":       "INIT",
        "contract":   [{"always": "True"}],
        "transitions": [
            {"target": f"PHI_{state_nums[first_scenario]}", "guard": first_when}
        ],
    })

    # ── 4 states per scenario ─────────────────────────────────────────────────
    for sid in scenario_ids:
        s          = scenarios[sid]
        n          = state_nums[sid]
        given      = normalize_expr(s["given"])
        then_expr  = normalize_expr(s["then"])
        do_action  = s["do"]
        name       = s["name"]

        # PHI_n — checks Given
        states.append({
            "name":     f"PHI_{n}",
            "contract": [{"always": "True"}],
            "transitions": [
                {"target": f"S{n+1}",    "guard": given},
                {"target": f"ERR_{n}",   "guard": negate_expr(given)},
            ],
        })
        err_states.add(f"ERR_{n}")

        # S_(n+1) — contract Given, waits for Do event
        states.append({
            "name":     f"S{n+1}",
            "contract": [{"always": given}],
            "transitions": [
                {"target": f"PHI_{n+2}", "event": f"{do_action} ({name})"}
            ],
        })

        # PHI_(n+2) — checks Then
        states.append({
            "name":     f"PHI_{n+2}",
            "contract": [{"always": "True"}],
            "transitions": [
                {"target": f"S{n+3}",      "guard": then_expr},
                {"target": f"ERR_{n+2}",   "guard": negate_expr(then_expr)},
            ],
        })
        err_states.add(f"ERR_{n+2}")

        # S_(n+3) — contract Then, routes to next scenarios via their When
        next_transitions = [
            {
                "target": f"PHI_{state_nums[target_sid]}",
                "guard":  normalize_expr(scenarios[target_sid]["when"]),
            }
            for target_sid in outgoing[sid]
        ]
        if not next_transitions:
            next_transitions = [{"target": "FINAL", "guard": "True"}]

        states.append({
            "name":     f"S{n+3}",
            "contract": [{"always": then_expr}],
            "transitions": next_transitions,
        })

    # ── ERR states (terminal) ─────────────────────────────────────────────────
    for err in sorted(err_states):
        states.append({"name": err})

    # ── FINAL ─────────────────────────────────────────────────────────────────
    states.append({"name": "FINAL", "type": "final"})

    return {
        "statechart": {
            "name":        "ScenarioStateMachine",
            "description": f"Generated from hAS model: {has_model.get('metadata', {}).get('name', '')}",
            "root state": {
                "name":    "root",
                "initial": "INIT",
                "states":  states,
            },
        }
    }


# ── YAML serialization ────────────────────────────────────────────────────────

# Custom representer so that expression strings are never quoted
# (e.g. "True" outputs as True, "h == 0" outputs as h == 0)
class _ExprStr(str):
    pass

def _expr_representer(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="")

yaml.add_representer(_ExprStr, _expr_representer)


def _wrap_exprs(obj):
    """Recursively convert string values to _ExprStr so they are not quoted."""
    if isinstance(obj, dict):
        return {k: _wrap_exprs(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_wrap_exprs(i) for i in obj]
    if isinstance(obj, str):
        return _ExprStr(obj)
    return obj


def to_yaml(assm: dict) -> str:
    return yaml.dump(
        _wrap_exprs(assm),
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1:
        has_model_path = Path(sys.argv[1])
    else:
        has_model_path = PROJECT_ROOT / "res" / "drone_has_model.json"

    output_path = PROJECT_ROOT / "configs" / "arm" / "scenario_state_machine.yaml"

    with open(has_model_path, encoding="utf-8") as f:
        has_model = json.load(f)

    assm = has_to_assm(has_model)
    yaml_str = to_yaml(assm)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(yaml_str)

    print(f"Generated: {output_path}")
