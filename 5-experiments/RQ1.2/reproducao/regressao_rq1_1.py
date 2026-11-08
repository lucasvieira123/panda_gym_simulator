"""Regressão: os 15 diagnósticos da RQ1.1 reproduzidos com o Diagnoser atual são iguais aos dos logs.

Para cada run com violação, monta o dataset que o run usou (5 CSVs nominais + o CSV do run) numa pasta
temporária e diagnostica pelo caminho da execução atual. Não altera o projeto. Uso, da raiz do projeto:
    python 5-experiments/RQ1.2/reproducao/regressao_rq1_1.py
"""
import glob
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "3-dejavu" / "src"))
from unanticipated_scenario_diagnoser import UnanticipatedScenarioDiagnoser  # noqa: E402

RES = ROOT / "5-experiments" / "RQ1.1" / "bateria" / "results"


def main():
    differences = 0
    for run in sorted(p for p in RES.iterdir() if p.is_dir()):
        events = [json.loads(line) for line in
                  open(glob.glob(str(run / "outputs/dejavu_traces/events_*.jsonl"))[0], encoding="utf-8")]
        diag = next((e for e in events if e["event"] == "diagnosis"), None)
        if diag is None:
            continue
        own = Path(glob.glob(str(run / "outputs/dataset/antecipated_scenario_dataset_*.csv"))[0])
        with tempfile.TemporaryDirectory() as folder:
            for f in glob.glob(str(run / "inputs/dejavu/antecipated_scenario_dataset/*.csv")) + [str(own)]:
                shutil.copy2(f, folder)
            diagnoser = UnanticipatedScenarioDiagnoser()
            diagnoser._dataset_folder = folder
            now = diagnoser.diagnosis({"name": f"{diag['active_scenario']}_unanticipated", "given": "G"},
                                      current_execution=own.stem)["diagnostic_conditions"]
        same = now == diag["diagnostic_conditions"]
        differences += not same
        print(f"{run.name:<10} {diag['active_scenario']:<17} log: {diag['diagnostic_conditions']:<28} "
              f"atual: {now:<28} {'igual' if same else 'DIFERENTE'}")
    print(f"\n{differences} diferença(s)")
    sys.exit(1 if differences else 0)


if __name__ == "__main__":
    main()
