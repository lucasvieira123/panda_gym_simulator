"""Tabela principal da RQ1.2: por atrito, RQ1.1 (conhecimento reiniciado) × RQ1.2 (conhecimento preservado).

Para cada μ da sequência: na RQ1.1, se houve violação e quem tratou; na RQ1.2, quais cenários incorporados o
Manager ativou, se houve violação (e o DejaVú foi acionado) e o que foi incorporado. Lê os outcome.json e os
eventos do DejaVú; não altera nada. Grava `rq1_1_x_rq1_2.csv` na pasta da sequência.
Uso, a partir da raiz do projeto:
    python 5-experiments/RQ1.2/sequencia/comparar_rq1_1.py <pasta da sequência>
"""
import csv
import glob
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RQ11 = HERE.parents[1] / "RQ1.1" / "bateria" / "results"
SHORT = {"transport_object_vacuum_assist": "transporte (C6)", "lift_object_vacuum_assist": "lift (C1)"}


def events(run: Path) -> list[dict]:
    path = glob.glob(str(run / "outputs" / "dejavu_traces" / "events_*.jsonl"))[0]
    return [json.loads(line) for line in open(path, encoding="utf-8")]


def rq11(name: str) -> dict:
    outcome = json.loads((RQ11 / name / "outcome.json").read_text(encoding="utf-8"))
    violation = outcome["violation"]
    tried = [f"{a['candidate']} ({a['status']})" for a in outcome["attempts"]]
    return {"violation": violation["active_scenario"] if violation else "—",
            "handled_by": ("DejaVú: " + ", ".join(tried)) if violation else "ASM inicial",
            "path": outcome["scenario"], "goal": outcome["physical"]["global_goal_achieved"]}


def rq12(run: Path) -> dict:
    outcome = json.loads((run / "outcome.json").read_text(encoding="utf-8"))
    ev = events(run)
    violation = outcome["violation"]
    activated = [SHORT.get(a["scenario"], a["scenario"]) for a in outcome["evolved_scenarios_activated"]]
    tried = [f"{a['candidate']} ({a['status']})" for a in outcome["attempts"]]
    incorporated = [f"{e['new_scenario_key']}: {e['new_scenario']['given']}" for e in ev if e["event"] == "asm_evolution"]
    if violation:
        handled = "DejaVú: " + ", ".join(tried)
    elif activated:
        handled = "conhecimento incorporado"
    else:
        handled = "ASM inicial"
    return {"mu": outcome["lateral_friction"], "carried_from": outcome["knowledge"]["carried_from"],
            "activated": ", ".join(activated) or "—", "violation": violation["active_scenario"] if violation else "—",
            "handled_by": handled, "path": outcome["scenario"], "goal": outcome["physical"]["global_goal_achieved"],
            "dist_cm": round(outcome["physical"]["dist_cube_to_target_m"] * 100, 1),
            "incorporated": "; ".join(incorporated) or "—",
            "rejected": "; ".join(e["reason"] for e in ev if e["event"] == "evolution_rejected") or "—",
            "errors": [e for e in ev if e["event"] == "pipeline_error"], "timed_out": outcome["run"]["timed_out"]}


def main():
    folder = Path(sys.argv[1])
    runs = {p.name: rq12(p) for p in folder.iterdir() if (p / "outcome.json").exists()}
    first = next(n for n, r in runs.items() if r["carried_from"] is None)
    ordered, current = [], first
    while current:
        ordered.append(current)
        current = next((n for n, r in runs.items() if r["carried_from"] == current), None)
    rows = []
    for name in ordered:
        new, old = runs[name], rq11(name)
        rows.append({"mu": new["mu"],
                     "rq1_1_violacao": old["violation"], "rq1_1_tratado_por": old["handled_by"],
                     "rq1_1_caminho": old["path"], "rq1_1_objetivo": old["goal"],
                     "rq1_2_ativados": new["activated"], "rq1_2_violacao": new["violation"],
                     "rq1_2_tratado_por": new["handled_by"], "rq1_2_caminho": new["path"],
                     "rq1_2_objetivo": new["goal"], "rq1_2_distancia_cm": new["dist_cm"],
                     "rq1_2_incorporado": new["incorporated"], "rq1_2_recusado": new["rejected"]})
    with open(folder / "rq1_1_x_rq1_2.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print("| μ | RQ1.1: violação | RQ1.1: tratado por | RQ1.2: cenários incorporados ativados | RQ1.2: violação | "
          "RQ1.2: tratado por | Objetivo (1.1 / 1.2) | Incorporado na RQ1.2 |")
    print("|---|---|---|---|---|---|---|---|")
    for r in rows:
        print(f"| {r['mu']:.3f} | {r['rq1_1_violacao']} | {r['rq1_1_tratado_por']} | {r['rq1_2_ativados']} | "
              f"{r['rq1_2_violacao']} | {r['rq1_2_tratado_por']} | {r['rq1_1_objetivo']} / {r['rq1_2_objetivo']} | "
              f"{r['rq1_2_incorporado']} |")
    dejavu_11 = sum(r["rq1_1_violacao"] != "—" for r in rows)
    dejavu_12 = sum(r["rq1_2_violacao"] != "—" for r in rows)
    reused = sum(r["rq1_2_tratado_por"] == "conhecimento incorporado" for r in rows)
    goals = lambda key: sum(bool(r[key]) for r in rows)
    print(f"\nConfigurações: {len(rows)}. Precisaram do DejaVú: RQ1.1 {dejavu_11}, RQ1.2 {dejavu_12}. "
          f"Tratadas pelo conhecimento incorporado, sem violação: {reused}. "
          f"Objetivo: RQ1.1 {goals('rq1_1_objetivo')}/{len(rows)}, RQ1.2 {goals('rq1_2_objetivo')}/{len(rows)}.")
    problems = [n for n, r in runs.items() if r["errors"] or r["timed_out"]]
    print(f"Erros de pipeline ou timeouts: {problems or 'nenhum'}")


if __name__ == "__main__":
    main()
