"""Bancada da RQ1.2: física com os cenários evoluídos aplicados antes do escorregamento.

Não é o sistema completo. Roda a sequência nominal do Managing e a VacuumAssistTask de produção
(com Q1: sem nova pegada se o objeto já está seguro), e imita a decisão do Manager com o ASM evoluído:
- LIFT_OBJECT_VACUUM_ASSIST: Given finger_contacts >= 2 AND lateral_friction <= 0.1425,
  When grasp_completed == 1, avaliado enquanto a subtarefa é GRASP_OBJECT;
- TRANSPORT_OBJECT_VACUUM_ASSIST: Given finger_contacts >= 2 AND lateral_friction <= 0.335,
  When object_lift_height_cm >= 10, avaliado no LIFT_OBJECT ou depois do cenário de lift.
O ASM cresce como na sequência: o cenário de transporte vale depois de 0,170; o de lift, depois de 0,140.
O comando do Manager vale a partir do tick seguinte. A violação é checada como no ASM-SM: Then do lift
ao sair da fase de lift, Then do transporte ao sair da fase de transporte, sempre com o tick anterior.

Uso, a partir da raiz do projeto:
    python 5-experiments/RQ1.2/bancada/bench_evolved.py
"""
import csv
import os
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "5-experiments" / "RQ1.1" / "bancada"))
import bench  # noqa: E402  (insere 2-managing/src no path)

SEQUENCE = [0.17, 0.16, 0.155, 0.15, 0.145, 0.14, 0.135, 0.13, 0.12, 0.11, 0.10, 0.08, 0.06, 0.04, 0.02, 0.01]
TRANSPORT_LIMIT, LIFT_LIMIT = 0.335, 0.1425
GRIPPER_CLOSED = 0.060  # m, como o Manager (monitor_arm.py)
LIFT_PHASE, TRANSPORT_PHASE = {"LIFT_OBJECT"}, {"TRANSPORT_OBJECT"}


def simulate(plan: dict) -> dict:
    from panda_gym.envs.core import RobotTaskEnv
    from config_loader import load_config
    from environment_manager import EnvironmentManager
    from tasks.factory import create_object_delivery, create_vacuum_assist

    with open(os.devnull, "w", encoding="utf-8") as devnull:
        stdout, sys.stdout = sys.stdout, devnull
        try:
            return _simulate(plan, RobotTaskEnv, load_config, EnvironmentManager, create_object_delivery,
                             create_vacuum_assist)
        finally:
            sys.stdout = stdout


def _simulate(plan, RobotTaskEnv, load_config, EnvironmentManager, create_object_delivery, create_vacuum_assist):
    mu = plan["mu"]
    configs = load_config(config_dir=str(bench.BASE))
    configs["simulation"]["render_mode"] = "rgb_array"
    configs["environment"]["objects"][0]["lateral_friction"] = mu
    env = EnvironmentManager(configs)
    sim, robot = env.sim, env.robot
    obj = configs["environment"]["objects"][0]["name"]
    seq = create_object_delivery(sim, robot, configs)
    gym = RobotTaskEnv(robot, seq)
    gym.reset(seed=configs["simulation"]["seed"])

    result = {"mu": mu, "lova": plan["lova"], "tova": plan["tova"], "activations": [], "violation": None,
              "violation_step": None}
    initial_z, previous, pending, last = None, None, None, None
    lova_active, lift_open = False, True
    for step in range(1, 1001):
        if pending:  # comando do Manager decidido no tick anterior
            gym.task = create_vacuum_assist(sim, robot, configs)
            gym.task.reset()
            result["activations"].append((pending, step))
            lova_active = lova_active or pending == "LOVA"
            pending = None

        obs, _, terminated, truncated, _ = gym.step(gym.task.compute_action())
        cube = np.array(sim.get_base_position(obj))
        initial_z = cube[2] if initial_z is None else initial_z
        contacts, _ = bench._contacts(sim, obj)
        adaptive = gym.task is not seq
        tick = {
            "step": step,
            "sub": gym.task.current_subtask if adaptive else seq.current_subtask,
            "contacts": contacts,
            "height_cm": max(0, int((cube[2] - initial_z) * 100)),
            "goal_xy_cm": int(np.linalg.norm(cube[:2] - np.array(seq.goal)[:2]) * 100),
            "grasp_completed": float(robot.get_fingers_width()) <= GRIPPER_CLOSED,
            "dist": float(np.linalg.norm(cube - np.array(seq.goal))),
            "width": float(robot.get_fingers_width()),
        }

        # ASM-SM: Then checado ao sair da fase; a fase do cenário de lift evoluído inclui a sucção.
        # A fase de lift termina uma vez; a sucção do transporte, depois, pertence à fase de transporte.
        if previous and tick["sub"] != previous["sub"]:
            lift_phase = LIFT_PHASE | ({"APPLY_VACUUM_ASSIST"} if lova_active else set())
            lift_ok = previous["height_cm"] >= 10 and previous["contacts"] >= 2
            if lift_open and previous["sub"] in lift_phase and tick["sub"] not in lift_phase:
                lift_open = False
                if not lift_ok and result["violation"] is None:
                    result["violation"], result["violation_step"] = "LIFT", step
            if previous["sub"] == "TRANSPORT_OBJECT" and tick["sub"] == "PLACE_OBJECT" and not (
                    lift_ok and previous["goal_xy_cm"] <= 5) and result["violation"] is None:
                result["violation"], result["violation_step"] = "TRANSPORT", step

        # Manager com o ASM evoluído (decide para o próximo tick)
        fired = {name for name, _ in result["activations"]}
        if plan["lova"] and "LOVA" not in fired and not adaptive and seq.current_subtask == "GRASP_OBJECT" \
                and tick["grasp_completed"] and contacts >= 2 and mu <= LIFT_LIMIT:
            pending = "LOVA"
        elif plan["tova"] and "TOVA" not in fired and contacts >= 2 and tick["height_cm"] >= 10 \
                and mu <= TRANSPORT_LIMIT and (lova_active or (not adaptive and seq.current_subtask == "LIFT_OBJECT")):
            pending = "TOVA"

        if adaptive and gym.task.done:
            seq.force_state(gym.task.return_to)  # "continue" do Manager: retoma a sequência
            gym.task = seq
        if gym.task is seq:
            seq.advance_if_done()
        previous = last = tick
        if terminated or truncated or seq.current_subtask == "DONE":
            break

    gym.close()
    result.update({"end_step": last["step"], "dist_cm": round(last["dist"] * 100, 1),
                   "goal": bool(last["dist"] <= bench.GOAL_DISTANCE and last["width"] >= bench.GOAL_WIDTH)})
    return result


def main():
    plans = [{"mu": mu, "tova": mu < 0.17, "lova": mu < 0.14} for mu in SEQUENCE]
    with Pool(max(1, (os.cpu_count() or 2) - 2)) as pool:
        rows = pool.map(simulate, plans)
    out = HERE / "results"
    out.mkdir(exist_ok=True)
    with open(out / "bench_evolved.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["mu", "tova", "lova", "activations", "violation", "violation_step",
                                               "end_step", "dist_cm", "goal"])
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r[k] for k in writer.fieldnames})
    print(f"{'μ':>6} {'ASM':<10} {'ativações':<26} {'violação':<16} {'fim':>4} {'dist':>6} objetivo")
    for r in rows:
        asm = "+".join(n for n, on in (("transp", r["tova"]), ("lift", r["lova"])) if on) or "inicial"
        act = ", ".join(f"{n}@{s}" for n, s in r["activations"]) or "—"
        vio = f"{r['violation']}@{r['violation_step']}" if r["violation"] else "—"
        print(f"{r['mu']:>6} {asm:<10} {act:<26} {vio:<16} {r['end_step']:>4} {r['dist_cm']:>6} {r['goal']}")


if __name__ == "__main__":
    main()
