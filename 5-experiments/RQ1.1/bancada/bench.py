"""
Bancada exploratória da RQ1.1: testa mecanismos físicos candidatos para C2 e C7.

Usa as tasks e a física reais do Managing, sem janela, Manager ou DejaVu. As regras de
violação e de início da adaptação imitam o fluxo real, e o modo `validate` confere isso
contra os runs da Etapa 1. Nada aqui altera o código de produção.

Uso, a partir da raiz do projeto:
    python 5-experiments/RQ1.1/bancada/bench.py validate
    python 5-experiments/RQ1.1/bancada/bench.py force
    python 5-experiments/RQ1.1/bancada/bench.py friction
    python 5-experiments/RQ1.1/bancada/bench.py map
    python 5-experiments/RQ1.1/bancada/bench.py second
    python 5-experiments/RQ1.1/bancada/bench.py perturb
    python 5-experiments/RQ1.1/bancada/bench.py vary
    python 5-experiments/RQ1.1/bancada/bench.py c1fix
    python 5-experiments/RQ1.1/bancada/bench.py c2after "V5 rotina completa"
    python 5-experiments/RQ1.1/bancada/bench.py transport

Os modos anteriores a `c1fix` usam o vacuum antigo (`legacy_vacuum_assist_task.py`) como
primeiro candidato. `transport` reproduz a produção atual: C1/C6 com atrito ×3 e C2/C7 com ×7.
"""
import csv
import json
import math
import os
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE    = Path(__file__).resolve().parent
ROOT    = HERE.parents[2]
RESULTS = HERE / "results"
BASE    = ROOT / "5-experiments" / "base" / "managing"
sys.path.insert(0, str(ROOT / "2-managing" / "src"))
sys.path.insert(0, str(HERE))

CUBE_REST_Z   = 0.02
GOAL_DISTANCE = 0.05
GOAL_WIDTH    = 0.06
FINGER_LINKS  = (9, 10)

# Fora das 25 configurações da avaliação final
EXPLORATORY_MU = [
    0.19, 0.175, 0.165, 0.1575, 0.1525, 0.1475, 0.1425, 0.1375, 0.1325, 0.125, 0.115,
    0.105, 0.095, 0.09, 0.085, 0.075, 0.07, 0.065, 0.055, 0.05, 0.045, 0.035, 0.03, 0.025, 0.015,
]


class Regrasp:
    """Abre, sobe, alinha sobre o cubo, desce, fecha e sobe, com tolerâncias e velocidade configuráveis."""

    return_to       = "TRANSPORT_OBJECT"
    current_subtask = "REGRASP"

    def __init__(self, sim, robot, obj, goal_task, finger_friction=1.0, force=170.0, tolerance=0.005,
                 grasp_dz=0.0, close_ticks=3, lift_speed=1.0, align_yaw=False, hover=0.12):
        self.sim, self.robot, self.obj = sim, robot, obj
        self.goal_task       = goal_task
        self.finger_friction = finger_friction
        self.force           = force
        self.tolerance       = tolerance
        self.grasp_dz        = grasp_dz
        self.close_ticks     = close_ticks
        self.lift_speed      = lift_speed
        self.align_yaw       = align_yaw
        self.hover           = hover
        self.phase           = "SETUP"
        self.ticks           = 0
        self.base_z          = None

    # A interface usada pelo RobotTaskEnv vem da task de objetivo da sequência
    def __getattr__(self, name):
        return getattr(self.__dict__["goal_task"], name)

    @property
    def done(self):
        return self.phase == "DONE"

    def reset_phase(self):
        pass

    def _toward(self, target, gripper, speed=1.0):
        delta = np.asarray(target) - np.asarray(self.robot.get_ee_position())
        distance = np.linalg.norm(delta)
        step = delta / max(distance, 1e-9) * min(distance / 0.05, 1.0) * speed if distance > 0 else delta
        return np.array([step[0], step[1], step[2], gripper], dtype=np.float32)

    def compute_action(self):
        ee   = np.array(self.robot.get_ee_position())
        cube = np.array(self.sim.get_base_position(self.obj))
        self.ticks += 1

        if self.phase == "SETUP":
            for link in FINGER_LINKS:
                self.sim.set_lateral_friction("panda", link, self.finger_friction)
            self.robot.joint_forces[7:9] = self.force
            self.phase = "RISE"

        if self.phase == "RISE":
            target = [ee[0], ee[1], cube[2] + self.hover]
            if abs(ee[2] - target[2]) < 0.02:
                self.phase = "ALIGN"
                if self.align_yaw:
                    self.robot.bench_yaw = _cube_yaw(self.sim, self.obj)
            return self._toward(target, 1.0)

        if self.phase == "ALIGN":
            target = [cube[0], cube[1], cube[2] + self.hover]
            if np.linalg.norm(ee - target) < self.tolerance * 2:
                self.phase = "DESCEND"
            return self._toward(target, 1.0)

        if self.phase == "DESCEND":
            target = [cube[0], cube[1], cube[2] + self.grasp_dz]
            if np.linalg.norm(ee - target) < self.tolerance:
                self.phase, self.hold = "CLOSE", 0
            return self._toward(target, 1.0, speed=0.5)

        if self.phase == "CLOSE":
            self.hold += 1
            if self.hold >= self.close_ticks:
                self.phase, self.base_z = "LIFT", cube[2]
            return np.array([0.0, 0.0, 0.0, -1.0], dtype=np.float32)

        if self.phase == "LIFT":
            target = [ee[0], ee[1], self.base_z + 0.15]
            if abs(ee[2] - target[2]) < 0.02:
                self.phase = "DONE"
            return self._toward(target, -1.0, speed=self.lift_speed)

        return np.array([0.0, 0.0, 0.0, -1.0], dtype=np.float32)


def _cube_yaw(sim, obj):
    """Giro no plano da mesa, em [-45°, 45°], que alinha a garra a uma face do cubo em repouso."""
    x, y, z, w = sim.get_base_rotation(obj, type="quaternion")
    rotation = np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
        [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
    ])
    for axis in rotation.T:
        if abs(axis[2]) < 0.2:
            yaw = math.atan2(axis[1], axis[0])
            return (yaw + math.pi / 4) % (math.pi / 2) - math.pi / 4
    return 0.0


def _install_yaw_control(robot):
    """Só na bancada: permite girar a garra em torno do eixo vertical."""
    robot.bench_yaw = 0.0
    original = robot.ee_displacement_to_target_arm_angles

    def with_yaw(displacement):
        if abs(robot.bench_yaw) < 1e-6:
            return original(displacement)
        position = robot.get_ee_position() + displacement[:3] * 0.05
        position[2] = max(0, position[2])
        half = robot.bench_yaw / 2
        qz = (0.0, 0.0, math.sin(half), math.cos(half))
        q0 = (1.0, 0.0, 0.0, 0.0)
        orientation = np.array([
            qz[3] * q0[0] + qz[0] * q0[3] + qz[1] * q0[2] - qz[2] * q0[1],
            qz[3] * q0[1] - qz[0] * q0[2] + qz[1] * q0[3] + qz[2] * q0[0],
            qz[3] * q0[2] + qz[0] * q0[1] - qz[1] * q0[0] + qz[2] * q0[3],
            qz[3] * q0[3] - qz[0] * q0[0] - qz[1] * q0[1] - qz[2] * q0[2],
        ])
        return robot.inverse_kinematics(link=robot.ee_link, position=position, orientation=orientation)[:7]

    robot.ee_displacement_to_target_arm_angles = with_yaw


def _contacts(sim, obj):
    client, panda, cube = sim.physics_client, sim._bodies_idx["panda"], sim._bodies_idx[obj]
    points = [client.getContactPoints(bodyA=panda, bodyB=cube, linkIndexA=link) for link in FINGER_LINKS]
    return sum(1 for p in points if p), [float(sum(c[9] for c in p)) for p in points]


def simulate(plan: dict) -> dict:
    """Roda um episódio com o plano: atrito do objeto, ajustes prévios e tentativas de adaptação."""
    import yaml  # noqa: F401
    from panda_gym.envs.core import RobotTaskEnv
    from config_loader import load_config
    from environment_manager import EnvironmentManager
    from tasks.factory import create_object_delivery, create_vacuum_assist

    with open(os.devnull, "w", encoding="utf-8") as devnull:
        stdout, sys.stdout = sys.stdout, devnull
        try:
            return _simulate(plan, RobotTaskEnv, load_config, EnvironmentManager, create_object_delivery, create_vacuum_assist)
        finally:
            sys.stdout = stdout


def _simulate(plan, RobotTaskEnv, load_config, EnvironmentManager, create_object_delivery, create_vacuum_assist):
    configs = load_config(config_dir=str(BASE))
    configs["simulation"]["render_mode"] = "rgb_array"
    configs["environment"]["objects"][0]["lateral_friction"] = plan["mu"]
    if plan.get("offset"):
        position = configs["environment"]["objects"][0]["initial_position"]
        position[0] += plan["offset"][0]
        position[1] += plan["offset"][1]

    env   = EnvironmentManager(configs)
    sim, robot = env.sim, env.robot
    obj   = configs["environment"]["objects"][0]["name"]
    seq   = create_object_delivery(sim, robot, configs)
    gym   = RobotTaskEnv(robot, seq)
    _install_yaw_control(robot)
    gym.reset(seed=configs["simulation"]["seed"])

    if plan.get("pre_force"):
        robot.joint_forces[7:9] = plan["pre_force"]
    if plan.get("pre_friction"):
        for link in FINGER_LINKS:
            sim.set_lateral_friction("panda", link, plan["pre_friction"])

    result = {**plan, "violation": None, "violation_step": None, "first_start": None, "first_done": None,
              "second_start": None, "second_done": None, "ineligible": None, "status": "ok"}
    previous = None
    prev_sub = None
    adaptive = None
    attempt  = 0
    adaptive_ticks = 0
    held_forces, grip_events, lift_max, grasp_held = [], [], 0.0, 0
    transport_slide = []
    rows = []
    initial_z = None
    transports, transport_open = [], None

    def start_vacuum():
        if plan.get("first_regrasp"):
            return Regrasp(sim, robot, obj, seq, **plan["first_regrasp"])
        import legacy_vacuum_assist_task as vacuum_module
        vacuum_module._FINGER_LENGTH = plan.get("grasp_offset", 0.025)
        task = vacuum_module.VacuumAssistTask(
            sim=sim,
            fingers_indices=robot.fingers_indices,
            get_ee_position=robot.get_ee_position,
            get_object_position=lambda: sim.get_base_position(obj),
            target_goal_cfg=configs["target_goal"],
            object_cfg=configs["environment"]["objects"][0],
            task_cfg=configs.get("simulation"),
        )
        if plan.get("vacuum_threshold"):
            task.threshold = plan["vacuum_threshold"]
        task.reset()
        return task

    def start_regrasp():
        task = Regrasp(sim, robot, obj, seq, **plan["second"])
        return task

    last = None
    for step in range(1, plan.get("max_steps", 400) + 1):
        action = gym.task.compute_action()
        if plan.get("transport_speed") and gym.task is seq and seq.current_subtask == "TRANSPORT_OBJECT":
            action = np.array([*(action[:3] * plan["transport_speed"]), action[3]], dtype=np.float32)
        obs, _, terminated, truncated, info = gym.step(action)

        cube = np.array(sim.get_base_position(obj))
        ee   = np.array(robot.get_ee_position())
        width = float(robot.get_fingers_width())
        target = np.array(seq.goal)
        contacts, forces = _contacts(sim, obj)
        initial_z = cube[2] if initial_z is None else initial_z
        tick = {
            "step": step, "task": "SEQ" if gym.task is seq else ("REGRASP" if isinstance(gym.task, Regrasp) else "VACUUM"),
            "sub": seq.current_subtask, "contacts": contacts, "forces": forces, "width": width,
            "height_cm": max(0, int((cube[2] - initial_z) * 100)),
            "goal_xy_cm": int(np.linalg.norm(cube[:2] - target[:2]) * 100),
            "cube": cube.tolist(), "ee": ee.tolist(), "dist": float(np.linalg.norm(cube - target)),
        }
        if plan.get("keep_ticks"):
            rows.append(tick)

        # Cada trecho contínuo de TRANSPORT_OBJECT na sequência: duração e passagens pelo alvo em X ou Y
        if gym.task is seq and tick["sub"] == "TRANSPORT_OBJECT":
            side = tuple(np.sign(ee[:2] - target[:2]))
            if transport_open is None:
                transport_open = {"start": step, "ticks": 0, "crossings": 0, "side": side,
                                  "after_adaptation": attempt > 0, "held_at_end": None}
                transports.append(transport_open)
            transport_open["ticks"] += 1
            transport_open["crossings"] += sum(1 for a, b in zip(side, transport_open["side"]) if a and b and a != b)
            transport_open["side"] = side
            transport_open["held_at_end"] = contacts == 2
        else:
            transport_open = None

        # Fase de aperto medida depois de uma tentativa ou na pegada normal
        if contacts == 2:
            held_forces.append(sum(forces) / 2)
            if cube[2] > 0.05:
                grasp_held += 1
                lift_max = max(lift_max, (cube[2] - CUBE_REST_Z) * 100)
            if gym.task is seq and seq.current_subtask == "TRANSPORT_OBJECT":
                transport_slide.append(float(ee[2] - cube[2]))

        command = None
        if gym.task is not seq:
            adaptive_ticks += 1
            if adaptive.done:
                # Fim de uma tentativa: falha imediata sem 2 contatos ou abaixo de 10 cm
                failed = contacts < 2 or tick["height_cm"] < 10
                if attempt == 1:
                    result["first_done"], result["first_ok"] = step, not failed
                else:
                    result["second_done"], result["second_ok"] = step, not failed
                on_table = cube[2] > 0.0 and -0.85 <= cube[0] <= 0.25 and -0.35 <= cube[1] <= 0.35
                if failed and attempt == 1 and plan.get("second"):
                    if on_table:
                        command = "second"
                    else:
                        result["ineligible"] = "off_table"
                        command = "resume"
                else:
                    command = "resume"
            elif adaptive_ticks > 200:
                result["status"] = "adaptive_watchdog"
                last = tick
                break
        elif prev_sub and seq.current_subtask != prev_sub and result["violation"] is None and previous:
            # A violação usa o tick anterior, como a state machine real
            lift_then = previous["height_cm"] >= 10 and previous["contacts"] >= 2
            then = lift_then if prev_sub == "LIFT_OBJECT" else (
                previous["goal_xy_cm"] <= 5 and lift_then if prev_sub == "TRANSPORT_OBJECT" else True)
            if not then:
                result["violation"], result["violation_step"] = prev_sub, step
                if plan.get("first"):
                    command = "first"

        if command == "first":
            adaptive, attempt, adaptive_ticks = start_vacuum(), 1, 0
            gym.task = adaptive
            result["first_start"] = step
        elif command == "second":
            adaptive, attempt, adaptive_ticks = start_regrasp(), 2, 0
            gym.task = adaptive
            result["second_start"] = step
            result.update({"forces_before_second": held_forces[-1] if held_forces else 0.0})
            held_forces, lift_max, grasp_held = [], 0.0, 0
        elif command == "resume":
            seq.force_state(adaptive.return_to)
            gym.task = seq

        if gym.task is seq:
            seq.advance_if_done()

        prev_sub, previous, last = tick["sub"], tick, tick
        if terminated or truncated:
            break

    gym.close()
    slide = (transport_slide[-1] - transport_slide[0]) * 1000 if len(transport_slide) > 1 else None
    result.update({
        "end_step": last["step"], "dist_cm": round(last["dist"] * 100, 1), "width_cm": round(last["width"] * 100, 1),
        "goal": bool(last["dist"] <= GOAL_DISTANCE and last["width"] >= GOAL_WIDTH),
        "force_mean": round(float(np.mean(held_forces)), 1) if held_forces else 0.0,
        "lift_max_cm": round(lift_max, 1), "held_ticks": grasp_held,
        "transport_slide_mm": round(slide, 1) if slide is not None else None,
        "cube_final": [round(float(x), 3) for x in last["cube"]],
        "transports": [{k: v for k, v in t.items() if k != "side"} for t in transports],
    })
    if plan.get("keep_ticks"):
        result["ticks"] = rows
    return result


def run_all(plans):
    with Pool(max(1, (os.cpu_count() or 2) - 2)) as pool:
        return pool.map(simulate, plans)


def save(name, rows):
    RESULTS.mkdir(parents=True, exist_ok=True)
    keys = sorted({k for r in rows for k in r if k != "ticks"})
    with open(RESULTS / f"{name}.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in r.items() if k != "ticks"})


def validate():
    """Confere a bancada contra os runs reais da Etapa 1. Usa valores já rodados, sem ajuste."""
    expected = {0.13: (75, 1.5, "LIFT_OBJECT", 24), 0.16: (100, 2.0, "TRANSPORT_OBJECT", 39),
                0.06: (73, 47.8, "LIFT_OBJECT", 24), 0.155: (93, 9.0, "TRANSPORT_OBJECT", 42),
                0.135: (105, 6.8, "TRANSPORT_OBJECT", 39), 0.14: (73, 41.4, "LIFT_OBJECT", 24)}
    rows = run_all([{"mu": mu, "first": "vacuum"} for mu in expected])
    for r in rows:
        step, dist, violation, start = expected[r["mu"]]
        same = (r["end_step"], r["dist_cm"], r["violation"], r["first_start"] + 1) == (step, dist, violation, start)
        print(f"mu={r['mu']:<6} bancada: fim={r['end_step']} dist={r['dist_cm']} viol={r['violation']} "
              f"início={r["first_start"] + 1} | real: fim={step} dist={dist} viol={violation} início={start} | "
              f"{'IGUAL' if same else 'DIFERENTE'}")
    save("validate", rows)


def force():
    """O limite de força muda a força aplicada e o limite de atrito? Sem adaptação, da pegada normal ao fim."""
    caps = [85, 170, 340, 680, 1360]
    mus  = [0.19, 0.175, 0.165, 0.1575, 0.1475, 0.125, 0.105, 0.085, 0.065, 0.045, 0.025]
    rows = run_all([{"mu": mu, "pre_force": cap} for cap in caps for mu in mus])
    save("force", rows)
    print("Objetivo global sem adaptação, por limite de força (S) | força média (N) | subida máx. (cm)")
    print("limite  " + " ".join(f"{m:>12}" for m in mus))
    for cap in caps:
        line = [next(r for r in rows if r["mu"] == m and r["pre_force"] == cap) for m in mus]
        print(f"{cap:6}  " + " ".join(f"{'S' if r['goal'] else '-'}{r['force_mean']:6.0f}/{r['lift_max_cm']:4.1f}" for r in line))


def friction():
    """O atrito efetivo é o produto? Limite por atrito dos dedos, sem adaptação."""
    fingers = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0]
    mus     = [0.5, 0.4, 0.3, 0.25, 0.19, 0.165, 0.1475, 0.125, 0.105, 0.085, 0.065, 0.045, 0.035, 0.025, 0.015]
    rows = run_all([{"mu": mu, "pre_friction": f} for f in fingers for mu in mus])
    save("friction", rows)
    print("Objetivo global sem adaptação (S) por atrito dos dedos e do objeto")
    print("dedos   " + " ".join(f"{m:>6}" for m in mus))
    for f in fingers:
        print(f"{f:6}  " + " ".join(f"{'S' if next(r for r in rows if r['mu'] == m and r['pre_friction'] == f)['goal'] else '-':>6}" for m in mus))


def map_first():
    """Mapa do primeiro candidato nos atritos exploratórios."""
    rows = run_all([{"mu": mu, "first": "vacuum"} for mu in EXPLORATORY_MU])
    save("map", rows)
    for r in rows:
        print(f"mu={r['mu']:<7} viol={str(r['violation']):17} início={str(r['first_start']):5} "
              f"ok_na_task={str(r.get('first_ok')):5} objetivo={str(r['goal']):5} dist={r['dist_cm']:6.1f} status={r['status']}")


STRATEGIES = {
    "S0 repete_atrito3":         {"finger_friction": 3.0, "tolerance": 0.045, "grasp_dz": 0.025, "close_ticks": 1, "hover": 0.0},
    "S1 reposiciona":            {"finger_friction": 1.0},
    "S2 forca340_sem_repos":     {"finger_friction": 1.0, "force": 340.0, "tolerance": 0.045, "grasp_dz": 0.025, "close_ticks": 1, "hover": 0.0},
    "S3 reposiciona_f340":       {"finger_friction": 1.0, "force": 340.0},
    "S4 reposiciona_f680":       {"finger_friction": 1.0, "force": 680.0},
    "S5 reposiciona_atr3":       {"finger_friction": 3.0},
    "S6 reposiciona_atr3_f340":  {"finger_friction": 3.0, "force": 340.0},
    "S7 reposiciona_atr3_f680":  {"finger_friction": 3.0, "force": 680.0},
    "S8 repos_atr3_giro":        {"finger_friction": 3.0, "align_yaw": True},
    "S9 repos_atr3_lento":       {"finger_friction": 3.0, "lift_speed": 0.4},
    "S10 repos_atr3_giro_f340":  {"finger_friction": 3.0, "align_yaw": True, "force": 340.0},
    "S11 repos_atr1_giro_f340":  {"finger_friction": 1.0, "align_yaw": True, "force": 340.0},
    "S12 repos_atr3_giro_lento": {"finger_friction": 3.0, "align_yaw": True, "lift_speed": 0.4},
}


def failing_mus():
    with open(RESULTS / "map.csv", encoding="utf-8") as f:
        return [(float(r["mu"]), r["violation"]) for r in csv.DictReader(f) if r["goal"] == "False"]


def second():
    """Segunda tentativa, a partir do estado real deixado pela falha do vacuum."""
    failing = failing_mus()
    plans = [{"mu": mu, "first": "vacuum", "second": cfg, "strategy": name} for name, cfg in STRATEGIES.items() for mu, _ in failing]
    rows = run_all(plans)
    save("second", rows)
    fase = dict(failing)
    tried = lambda r: r["second_start"] is not None
    print(f"Atritos em que o vacuum não atingiu o objetivo: {[m for m, _ in failing]}")
    print(f"{'estratégia':28} {'tentou':>6} {'pegou':>6} {'objetivo':>8}  lift  transp  recuperados")
    for name in STRATEGIES:
        group = [r for r in rows if r["strategy"] == name]
        t = [r for r in group if tried(r)]
        ok = [r for r in t if r["goal"]]
        lift = sum(1 for r in ok if fase[r["mu"]] == "LIFT_OBJECT")
        print(f"{name:28} {len(t):6} {sum(1 for r in t if r.get('second_ok')):6} {len(ok):8} {lift:5} {len(ok) - lift:6}  {[r['mu'] for r in ok]}")
    print("Sem segunda tentativa:", sorted({(r["mu"], r["ineligible"] or r["status"]) for r in rows if not tried(r)}))


def perturb():
    """Sensibilidade à posição inicial: ±2 mm em X e Y, para as estratégias indicadas."""
    names = sys.argv[2].split(",") if len(sys.argv) > 2 else ["S1 reposiciona", "S5 reposiciona_atr3", "S8 repos_atr3_giro", "S3 reposiciona_f340"]
    offsets = [(0.002, 0), (-0.002, 0), (0, 0.002), (0, -0.002)]
    mus = [0.1575, 0.1475, 0.1425, 0.1375, 0.125, 0.105, 0.095, 0.075, 0.065, 0.055, 0.045, 0.035]
    plans = [{"mu": mu, "first": "vacuum", "offset": off, "strategy": "C1 só"} for mu in mus for off in offsets]
    plans += [{"mu": mu, "first": "vacuum", "second": STRATEGIES[n], "strategy": n, "offset": off} for n in names for mu in mus for off in offsets]
    rows = run_all(plans)
    save("perturb", rows)
    print(f"Runs por célula: {len(offsets)}. Objetivo global em cada atrito:")
    print(f"{'estratégia':28} " + " ".join(f"{m:>6}" for m in mus) + "   total")
    for name in ["C1 só", *names]:
        cells = [sum(1 for r in rows if r["strategy"] == name and r["mu"] == m and r["goal"]) for m in mus]
        print(f"{name:28} " + " ".join(f"{c:>6}" for c in cells) + f"   {sum(cells)}/{len(mus) * len(offsets)}")


def vary():
    """Quanto o resultado de reposicionar com atrito 3 depende dos parâmetros da nova pegada."""
    failing = failing_mus()
    variants = {
        "tolerância 2 mm":    {"tolerance": 0.002},
        "tolerância 5 mm":    {"tolerance": 0.005},
        "tolerância 10 mm":   {"tolerance": 0.010},
        "tolerância 20 mm":   {"tolerance": 0.020},
        "altura +0 mm":       {"grasp_dz": 0.0},
        "altura +10 mm":      {"grasp_dz": 0.010},
        "altura +25 mm":      {"grasp_dz": 0.025},
        "fechar 1 tick":      {"close_ticks": 1},
        "fechar 3 ticks":     {"close_ticks": 3},
        "fechar 6 ticks":     {"close_ticks": 6},
        "subida a 12 cm":     {"hover": 0.12},
        "subida a 8 cm":      {"hover": 0.08},
        "atrito 1,5":         {"finger_friction": 1.5},
        "atrito 2":           {"finger_friction": 2.0},
        "atrito 5":           {"finger_friction": 5.0},
        "atrito 10":          {"finger_friction": 10.0},
    }
    plans = [{"mu": mu, "first": "vacuum", "second": {"finger_friction": 3.0, **cfg}, "strategy": name}
             for name, cfg in variants.items() for mu, _ in failing]
    rows = run_all(plans)
    save("vary", rows)
    print(f"Base: reposicionar com atrito 3, tolerância 5 mm, altura +0, fechar 3 ticks. Atritos: {len(failing)}")
    for name in variants:
        ok = [r["mu"] for r in rows if r["strategy"] == name and r["goal"]]
        print(f"{name:20} objetivo={len(ok):2}  {ok}")


POSITIONS = [None, (0.002, 0), (-0.002, 0), (0, 0.002), (0, -0.002)]
FIRST_VARIANTS = {
    "V0 atual (+25 mm, 45 mm)":  {"grasp_offset": 0.025},
    "V1 +10 mm, 45 mm":          {"grasp_offset": 0.010},
    "V2 +0 mm, 45 mm":           {"grasp_offset": 0.0},
    "V3 +10 mm, 20 mm":          {"grasp_offset": 0.010, "vacuum_threshold": 0.02},
    "V4 +0 mm, 20 mm":           {"grasp_offset": 0.0, "vacuum_threshold": 0.02},
    "V5 rotina completa":        {"first_regrasp": {"finger_friction": 3.0}},
}


def category(r):
    if r["status"] != "ok":
        return "watchdog"
    if not r["violation"]:
        return "A" if r["goal"] else "sem_violacao_falha"
    if r.get("first_ok"):
        return "B" if r["goal"] else "E1"
    if r.get("second_ok"):
        return "C" if r["goal"] else "E2"
    return "acaso" if r["goal"] else "D"


def _table(rows, names, label):
    mus = sorted(EXPLORATORY_MU, reverse=True)
    print(f"{label}: categoria por atrito (5 posições iniciais; contagem de cada categoria)")
    for name in names:
        group = [r for r in rows if r["strategy"] == name]
        total = {}
        for r in group:
            total[category(r)] = total.get(category(r), 0) + 1
        print()
        print(f"{name}  total={dict(sorted(total.items()))}")
        for mu in mus:
            cells = {}
            for r in group:
                if r["mu"] == mu:
                    cells[category(r)] = cells.get(category(r), 0) + 1
            print(f"   {mu:<7} " + " ".join(f"{k}={v}" for k, v in sorted(cells.items())))


def c1fix():
    """O primeiro candidato com a pegada corrigida, sem segunda tentativa."""
    plans = [{"mu": mu, "first": "vacuum", "strategy": name, "offset": off, **cfg}
             for name, cfg in FIRST_VARIANTS.items() for mu in EXPLORATORY_MU for off in POSITIONS]
    rows = run_all(plans)
    save("c1fix", rows)
    _table(rows, list(FIRST_VARIANTS), "Primeiro candidato")


def c2after():
    """O segundo candidato com mais atrito, usando a mesma rotina de pegada do primeiro."""
    first = FIRST_VARIANTS[sys.argv[2]]
    frictions = [3.0, 5.0, 7.0, 10.0]
    plans = [{"mu": mu, "first": "vacuum", "strategy": f"C2 atrito {f}", "offset": off, **first,
              "second": {"finger_friction": f}}
             for f in frictions for mu in EXPLORATORY_MU for off in POSITIONS]
    rows = run_all(plans)
    save("c2after", rows)
    _table(rows, [f"C2 atrito {f}" for f in frictions], f"Primeiro: {sys.argv[2]}")


def transport():
    """Duração do transporte com C1/C6 (atrito ×3) e C2/C7 (atrito ×7), como na produção.

    `results/transport_before_fix.*` guarda a medição com o transporte antigo, sem desaceleração,
    e `results/transport_slowdown.*` a variante que a bancada testou antes de levá-la à produção.
    """
    plans = [{"mu": mu, "first": "vacuum", "strategy": "produção", "offset": off, "max_steps": 1000,
              "first_regrasp": {"finger_friction": 3.0}, "second": {"finger_friction": 7.0}}
             for mu in EXPLORATORY_MU for off in POSITIONS]
    rows = run_all(plans)
    save("transport", rows)

    print("Trechos de TRANSPORT_OBJECT: duração em ticks e passagens pelo alvo")
    print(f"{'mu':>7} {'pos':>14} cat  fim   trechos (início:ticks/passagens, * = após adaptação, h = segurando no fim)")
    for r in rows:
        parts = " ".join(f"{t['start']}:{t['ticks']}/{t['crossings']}{'*' if t['after_adaptation'] else ''}"
                         f"{'h' if t['held_at_end'] else ''}" for t in r["transports"])
        print(f"{r['mu']:>7} {str(r['offset']):>14} {category(r):4} {r['end_step']:4}  {parts}")

    def summary(label, segments):
        ticks = sorted(t["ticks"] for t in segments)
        if not ticks:
            print(f"{label}: nenhum")
            return
        long = [t for t in ticks if t > 30]
        print(f"{label}: n={len(ticks)} mediana={ticks[len(ticks) // 2]} máx={ticks[-1]} "
              f">30 ticks={len(long)} >100 ticks={sum(1 for t in ticks if t > 100)}")

    held = lambda t: t["held_at_end"]
    segments = [t for r in rows for t in r["transports"]]
    print()
    summary("Transporte sem adaptação, segurando", [t for t in segments if not t["after_adaptation"] and held(t)])
    summary("Transporte sem adaptação, cubo perdido", [t for t in segments if not t["after_adaptation"] and not held(t)])
    summary("Transporte após adaptação, segurando", [t for t in segments if t["after_adaptation"] and held(t)])
    summary("Transporte após adaptação, cubo perdido", [t for t in segments if t["after_adaptation"] and not held(t)])
    ends = sorted(r["end_step"] for r in rows)
    print(f"Fim do episódio: mediana={ends[len(ends) // 2]} máx={ends[-1]} "
          f">300={sum(1 for e in ends if e > 300)} >500={sum(1 for e in ends if e > 500)} "
          f"watchdog={sum(1 for r in rows if r['status'] != 'ok')}")


if __name__ == "__main__":
    {"validate": validate, "force": force, "friction": friction, "map": map_first,
     "second": second, "perturb": perturb, "vary": vary, "c1fix": c1fix, "c2after": c2after,
     "transport": transport}[sys.argv[1]]()
