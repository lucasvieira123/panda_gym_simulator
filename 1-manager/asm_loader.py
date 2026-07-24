import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class AsmScenario:
    key:   str
    name:  str
    type:  str   # "predefined" | "adaptive"
    given: str
    when:  str
    do:    str
    then:  str


@dataclass
class AsmNode:
    key:  str
    name: str
    type: str    # "init" | "end"


@dataclass
class Asm:
    metadata:             dict
    nodes:                Dict[str, AsmNode]
    scenarios:            Dict[str, AsmScenario]
    monitored_parameters: dict
    transition_graph:     Dict[str, List[str]]   # { from_key: [to_key, ...] }


def load_asm(path: str | Path) -> Asm:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))

    nodes: Dict[str, AsmNode] = {}
    for key, n in raw.get("nodes", {}).items():
        nodes[key] = AsmNode(key=key, name=n["name"], type=n["type"])

    scenarios: Dict[str, AsmScenario] = {}
    for key, s in raw.get("scenarios", {}).items():
        scenarios[key] = AsmScenario(
            key=key,
            name=s["name"],
            type=s.get("type", "predefined"),
            given=s.get("given", "*"),
            when=s.get("when",  "*"),
            do=s.get("do",    ""),
            then=s.get("then",  "*"),
        )

    transition_graph: Dict[str, List[str]] = {}
    for t in raw.get("transitions", []):
        src = t["from"]
        dst = t["to"]
        transition_graph.setdefault(src, []).append(dst)

    return Asm(
        metadata=raw.get("metadata", {}),
        nodes=nodes,
        scenarios=scenarios,
        monitored_parameters=raw.get("monitored_parameters", {}),
        transition_graph=transition_graph,
    )
