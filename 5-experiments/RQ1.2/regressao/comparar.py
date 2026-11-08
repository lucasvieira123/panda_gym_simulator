"""Etapa 4 da RQ1.2: compara os runs refeitos com as correções (etapas 1–3) com os da bateria da RQ1.1.

Para cada run de `regressao/results/`, lê o outcome.json e os eventos do DejaVu e compara com o run de mesmo
nome em `RQ1.1/bateria/results/`. Diferenças esperadas, que não contam: horários, durações, ids de run e o
campo `evolved_from`, que o AsmEvolver passou a gravar. Uso, a partir da raiz do projeto:
    python 5-experiments/RQ1.2/regressao/comparar.py
"""
import glob
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NEW = HERE / "results"
OLD = HERE.parents[1] / "RQ1.1" / "bateria" / "results"


def summary(run: Path) -> dict:
    outcome = json.loads((run / "outcome.json").read_text(encoding="utf-8"))
    events = [json.loads(line) for line in
              open(glob.glob(str(run / "outputs" / "dejavu_traces" / "events_*.jsonl"))[0], encoding="utf-8")]
    by = lambda name: [e for e in events if e["event"] == name]
    evolution = [{**e["new_scenario"], "updated_given": e["updated_given"]} for e in by("asm_evolution")]
    for scenario in evolution:
        scenario.pop("evolved_from", None)
    return {
        "caminho": outcome.get("scenario"),
        "objetivo global": outcome["physical"]["global_goal_achieved"],
        "distância final (cm)": round(outcome["physical"]["dist_cube_to_target_m"] * 100, 1),
        "último step": outcome["sequence"]["last_step"],
        "violação": [(e["step"], e["active_scenario"], e["active_state"]) for e in by("violation")],
        "diagnóstico": [e["diagnostic_conditions"] for e in by("diagnosis")],
        "ranking": [[(r["candidate"], round(r["score"], 6)) for r in e["ranking"]] for e in by("ranking")],
        "tentativas": [(e["adaptation"]["attempt"], e["adaptation"]["candidate_name"]) for e in by("adaptation_selected")],
        "resultados": [(e["step"], e["attempt"], e["status"], e.get("reason")) for e in by("evaluation") if e.get("reason")],
        "decisões de retry": [(e["step"], e["action"], e["reason"]) for e in by("retry_decision")],
        "evolução do ASM": evolution,
        "evolução recusada": [(e["reason"], e["detail"]) for e in by("evolution_rejected")],
        "erros do pipeline": [(e.get("stage"), e.get("message")) for e in by("pipeline_error")],
    }


def main():
    runs = sorted(p for p in NEW.iterdir() if p.is_dir())
    differences = 0
    for run in runs:
        new, old = summary(run), summary(OLD / run.name)
        diff = {k: (old[k], new[k]) for k in new if new[k] != old[k]}
        differences += len(diff)
        print(f"== {run.name}: {'igual à bateria' if not diff else f'{len(diff)} campo(s) diferente(s)'}")
        for k, v in new.items():
            mark = "≠" if k in diff else " "
            print(f"  {mark} {k}: {v}" + (f"\n      bateria: {diff[k][0]}" if k in diff else ""))
    print(f"\n{differences} diferença(s) em {len(runs)} run(s)")
    sys.exit(1 if differences else 0)


if __name__ == "__main__":
    main()
