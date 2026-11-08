"""Análise de uma sequência da RQ1.2 executada com `execute_simulations.py --preserve-knowledge`.

Para cada run, na ordem da sequência (pelo campo knowledge.carried_from): cenários evoluídos no ASM de
entrada, cenários evoluídos ativados pelo Manager, violação, diagnóstico, tentativas, caminho, objetivo e
o que foi incorporado (ou recusado). Confere também que o ASM de entrada de cada run é o ASM de saída do
run anterior. Uso, a partir da raiz do projeto:
    python 5-experiments/RQ1.2/sequencia/analisar.py <pasta de resultados>
"""
import csv
import glob
import json
import sys
from pathlib import Path


def load(run: Path) -> dict:
    outcome = json.loads((run / "outcome.json").read_text(encoding="utf-8"))
    events = [json.loads(line) for line in
              open(glob.glob(str(run / "outputs" / "dejavu_traces" / "events_*.jsonl"))[0], encoding="utf-8")]
    asm_in = json.loads((run / "outputs" / "asm_before_run.json").read_text(encoding="utf-8"))
    asm_out = json.loads((run / "outputs" / "asm_after_run.json").read_text(encoding="utf-8"))
    by = lambda name: [e for e in events if e["event"] == name]
    evolved = lambda asm: [k for k, s in asm["scenarios"].items() if s.get("type") == "evolutionary"]
    violation = (by("violation") or [None])[0]
    return {
        "run": run.name,
        "mu": outcome["lateral_friction"],
        "carried_from": outcome.get("knowledge", {}).get("carried_from"),
        "asm_in": asm_in, "asm_out": asm_out,
        "evolved_in": evolved(asm_in),
        "activated": [(a["scenario"], a["step"]) for a in outcome.get("evolved_scenarios_activated", [])],
        "violation": (violation["active_scenario"], violation["step"]) if violation else None,
        "diagnosis": [e["diagnostic_conditions"] for e in by("diagnosis")],
        "attempts": [(a["attempt"], a["candidate"], a["status"], a["reason"]) for a in outcome["attempts"]],
        "path": outcome["scenario"],
        "goal": outcome["physical"]["global_goal_achieved"],
        "dist_cm": round(outcome["physical"]["dist_cube_to_target_m"] * 100, 1),
        "fail_safe": outcome["fail_safe"],
        "incorporated": [(e["new_scenario_key"], e["new_scenario"]["given"]) for e in by("asm_evolution")],
        "rejected": [(e["reason"], e["detail"]) for e in by("evolution_rejected")],
        "errors": [(e.get("stage"), e.get("message")) for e in by("pipeline_error")],
        "timed_out": outcome["run"]["timed_out"],
    }


def order(rows: list[dict]) -> list[dict]:
    by_prev = {r["carried_from"]: r for r in rows}
    current = by_prev.get(None)
    ordered = []
    while current:
        ordered.append(current)
        current = by_prev.get(current["run"])
    return ordered


def main():
    folder = Path(sys.argv[1])
    rows = order([load(p) for p in sorted(folder.iterdir()) if (p / "outcome.json").exists()])
    problems = []
    for prev, cur in zip(rows, rows[1:]):
        if cur["asm_in"] != prev["asm_out"]:
            problems.append(f"{cur['run']}: ASM de entrada diferente do ASM de saída de {prev['run']}")
    for r in rows:
        if r["timed_out"] or r["errors"]:
            problems.append(f"{r['run']}: timeout={r['timed_out']} erros={r['errors']}")
        print(f"== {r['run']}  μ={r['mu']}  (conhecimento de: {r['carried_from'] or 'entradas'})")
        print(f"   ASM de entrada, evoluídos: {r['evolved_in'] or '—'}")
        print(f"   ativados pelo Manager:     {r['activated'] or '—'}")
        print(f"   violação: {r['violation'] or '—'}   diagnóstico: {r['diagnosis'] or '—'}")
        print(f"   tentativas: {r['attempts'] or '—'}")
        print(f"   caminho: {r['path']}   objetivo: {r['goal']}   distância: {r['dist_cm']} cm   fail-safe: {r['fail_safe']}")
        print(f"   incorporado: {r['incorporated'] or '—'}   recusado: {r['rejected'] or '—'}")
    with open(folder / "sequencia.csv", "w", newline="", encoding="utf-8") as f:
        fields = ["run", "mu", "carried_from", "evolved_in", "activated", "violation", "diagnosis", "attempts",
                  "path", "goal", "dist_cm", "fail_safe", "incorporated", "rejected"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r[k] for k in fields})
    print(f"\nPassagem do conhecimento e execução: {'ok' if not problems else problems}")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
