"""Reproduz os diagnósticos e a evolução do ASM numa sequência 0,170 -> 0,010 com conhecimento preservado.

Não executa o simulador nem altera o projeto. Usa o Diagnoser e o AsmEvolver atuais sobre cópias:
- dataset de cada passo = 5 CSVs nominais do base + CSVs dos runs anteriores da sequência + o do run;
- os CSVs são os gravados na bateria da RQ1.1 (hipótese: cada run se comporta como na RQ1.1);
- o ASM evolui em cadeia, a partir do asm.json do base, nos runs que tiveram evolução na RQ1.1.

Saída de trabalho em `results/` (ignorada pelo git). Uso, a partir da raiz do projeto:
    python 5-experiments/RQ1.2/reproducao/rq12_sequential.py
"""
import glob
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "3-dejavu" / "src"))
from asm_evolver import AsmEvolver, EvolutionRejected  # noqa: E402
from unanticipated_scenario_diagnoser import UnanticipatedScenarioDiagnoser  # noqa: E402

RES = ROOT / "5-experiments" / "RQ1.1" / "bateria" / "results"
WORK = HERE / "results" / "sequential"
SEQ = ["10_0_17", "11_0_16", "12_0_155", "13_0_150", "14_0_145", "15_0_140", "16_0_135", "17_0_130",
       "18_0_120", "19_0_110", "20_0_100", "21_0_080", "22_0_060", "23_0_040", "24_0_020", "25_0_010"]


def events(run):
    path = glob.glob(str(RES / run / "outputs/dejavu_traces/events_*.jsonl"))[0]
    return [json.loads(line) for line in open(path, encoding="utf-8")]


def diagnose(folder, scenario, current_execution):
    diagnoser = UnanticipatedScenarioDiagnoser()
    diagnoser._dataset_folder = str(folder)
    try:
        return diagnoser.diagnosis({"name": f"{scenario}_unanticipated", "given": "G"},
                                   current_execution=current_execution)["diagnostic_conditions"]
    except ValueError as e:
        return f"ERRO: {e}"


def main():
    shutil.rmtree(WORK, ignore_errors=True)
    dataset = WORK / "dataset"
    dataset.mkdir(parents=True)
    for f in glob.glob(str(RES / SEQ[0] / "inputs/dejavu/antecipated_scenario_dataset/*.csv")):
        shutil.copy2(f, dataset)
    asm_path = WORK / "asm.json"
    shutil.copy2(RES / SEQ[0] / "inputs/manager/arm/asm.json", asm_path)
    evolver = AsmEvolver(str(asm_path))

    for run in SEQ:
        own = Path(glob.glob(str(RES / run / "outputs/dataset/antecipated_scenario_dataset_*.csv"))[0])
        shutil.copy2(own, dataset)
        ev = events(run)
        diag = next((e for e in ev if e["event"] == "diagnosis"), None)
        if diag is None:
            print(f"{run}: sem violação")
            continue
        scenario = diag["active_scenario"]
        sequential = diagnose(dataset, scenario, own.stem)
        print(f"{run}: {scenario}\n  RQ1.1 (isolado):       {diag['diagnostic_conditions']}\n"
              f"  sequencial (acumulado): {sequential}")
        evo = next((e for e in ev if e["event"] == "asm_evolution"), None)
        if evo and not sequential.startswith("ERRO"):
            do = [e["adaptation"] for e in ev if e["event"] == "adaptation_selected"][-1]["do"]
            mu = next(e for e in ev if e["event"] == "violation")["observed"]["lateral_friction"]
            try:
                r = evolver.evolve({"anticipated_id": evo["violated_key"]}, {"diagnostic_conditions": sequential},
                                   {"do": do}, context={"lateral_friction": mu})
                print(f"  evolução: {r['new_scenario_key']}\n    Given novo:     {r['new_scenario']['given']}\n"
                      f"    Given original: {r['updated_given']}")
            except EvolutionRejected as e:
                print(f"  evolução recusada ({mu}): {e}")

    asm = json.load(open(asm_path, encoding="utf-8"))
    dup = len(asm["transitions"]) - len({(t["from"], t["to"]) for t in asm["transitions"]})
    print(f"\nTransições duplicadas no ASM final: {dup}. ASM final em {asm_path}")


if __name__ == "__main__":
    main()
