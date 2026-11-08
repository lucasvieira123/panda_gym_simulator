"""Regressão do monitor: as 25 execuções da RQ1.1 reproduzidas no ASM-SM gerado do ASM.

Cada CSV do run guarda, por tick, a percepção que o DejaVu recebeu e o estado e o `sat` do ASM-SM.
O script passa as percepções pelo monitor atual (ASM-SM gerado do asm.json do run e eventos do
SubtaskEventMapper) e compara estado e `sat` tick a tick. Não altera o projeto. Uso, da raiz do projeto:
    python 5-experiments/RQ1.2/reproducao/regressao_monitor_rq1_1.py
"""
import contextlib
import glob
import io
import json
import math
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "3-dejavu" / "src"))
from antecipated_scenario_monitor import StateMachineEngine  # noqa: E402
from dejavu import _SM_INITIAL, _sm_params  # noqa: E402
from subtask_events import SubtaskEventMapper  # noqa: E402

RES = ROOT / "5-experiments" / "RQ1.1" / "bateria" / "results"


def _value(v):
    if isinstance(v, float) and math.isnan(v):
        return None
    return v


def _sat(v):
    if v is None or (isinstance(v, float) and math.isnan(v)) or v == "":
        return None
    return str(v).strip().lower() == "true"


def replay(run: Path) -> list[str]:
    asm_path = run / "inputs" / "manager" / "arm" / "asm.json"
    csv = pd.read_csv(glob.glob(str(run / "outputs" / "dataset" / "antecipated_scenario_dataset_*.csv"))[0])
    with contextlib.redirect_stdout(io.StringIO()):
        engine = StateMachineEngine(dict(_SM_INITIAL), asm_path=asm_path)
        mapper = SubtaskEventMapper(json.loads(asm_path.read_text(encoding="utf-8")))
        prev, differences = None, []
        for _, row in csv.iterrows():
            perception = {k: _value(v) for k, v in row.items()}
            perception["current_subtask"] = perception.get("current_subtask") or ""
            perception["is_success"] = str(perception.get("is_success")).lower() == "true"
            sm_tick, prev, skip = _sm_params(perception, prev, mapper, engine.awaited_events())
            sat = engine.check_state_machine(sm_tick, skip_rewind=skip)
            states = [s for s in engine.itp.configuration if s != "root"]
            state = states[0] if states else "—"
            if state != row["active_state"] or sat != _sat(row["sat"]):
                differences.append(f"step {row['step']}: gravado {row['active_state']}/{_sat(row['sat'])}, "
                                   f"atual {state}/{sat}")
    return differences


def main():
    total = 0
    for run in sorted(p for p in RES.iterdir() if p.is_dir()):
        differences = replay(run)
        total += len(differences)
        print(f"{run.name:<10} {'igual' if not differences else f'{len(differences)} tick(s) diferentes'}")
        for d in differences[:5]:
            print("    ", d)
    print(f"\n{total} tick(s) diferentes")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
