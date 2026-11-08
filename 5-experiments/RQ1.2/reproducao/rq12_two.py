"""ASM com só as duas primeiras incorporações da sequência: transporte em 0,170 e lift em 0,140.

Os limiares vêm de `rq12_sequential.py` (0,335 em log; 0,1425 reproduzido com o dataset preservado).
Não altera o projeto: evolui uma cópia do asm.json do base em `results/`. Uso, a partir da raiz do projeto:
    python 5-experiments/RQ1.2/reproducao/rq12_two.py
"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "3-dejavu" / "src"))
from asm_evolver import AsmEvolver  # noqa: E402

BASE_ASM = ROOT / "5-experiments" / "RQ1.1" / "bateria" / "results" / "10_0_17" / "inputs" / "manager" / "arm" / "asm.json"
INCORPORATIONS = [
    ("transport_object", "lateral_friction <= 0.335", "apply_vacuum_assist()"),   # μ = 0,170, C6
    ("lift_object",      "lateral_friction <= 0.1425", "apply_vacuum_assist()"),  # μ = 0,140, C1
]


def main():
    out = HERE / "results" / "asm_two_incorporations.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(BASE_ASM, out)
    base = json.load(open(BASE_ASM, encoding="utf-8"))
    evolver = AsmEvolver(str(out))
    for key, condition, do in INCORPORATIONS:
        evolver.evolve({"anticipated_id": key}, {"diagnostic_conditions": condition}, {"do": do})
    asm = json.load(open(out, encoding="utf-8"))
    for key in ("lift_object", "lift_object_vacuum_assist", "transport_object", "transport_object_vacuum_assist"):
        s = asm["scenarios"][key]
        print(f"{s['name']} ({s['type']})\n  Given: {s['given']}\n  When : {s['when']}\n"
              f"  Do   : {s['do']}\n  Then : {s['then']}")
    print("Novas transições:", [(t["from"], t["to"]) for t in asm["transitions"] if t not in base["transitions"]])


if __name__ == "__main__":
    main()
