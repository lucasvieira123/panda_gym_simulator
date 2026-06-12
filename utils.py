import queue
import threading
import tkinter as tk

import numpy as np

_LINE = "─" * 44


class DebugOverlay:
    """Exibe informações do MAPE-K diretamente na janela 3D do PyBullet."""

    _LABELS = [
        "header",
        "ee_pos",
        "ee_vel",
        "garra",
        "cube_pos",
        "target",
        "dist_ee_cube",
        "dist_cube_tgt",
        "reward",
        "sucesso",
    ]
    _X = -0.3
    _Y =  0.8
    _Z_TOP = 0.75
    _Z_STEP = 0.07

    def __init__(self, physics_client) -> None:
        self._client = physics_client
        self._ids = {}

    def render(self, episode: int, step: int, obs: dict, reward: float,
               info: dict, task=None, robot=None, sim=None) -> None:
        o             = obs["observation"]
        ee_pos        = o[0:3]
        ee_vel        = o[3:6]
        fingers       = o[6]
        cube_pos      = o[7:10]
        target_pos    = obs["desired_goal"]
        dist_ee_cube  = float(np.linalg.norm(ee_pos - cube_pos))
        dist_cube_tgt = float(np.linalg.norm(cube_pos - target_pos))
        gripper_state = "ABERTA" if fingers > 0.02 else "FECHADA"
        task_name     = type(task).__name__ if task is not None else "?"
        success       = info.get("is_success", False)

        lines = [
            (f"{task_name} | Ep {episode:>2} | Step {step:>3}",                          [1.0, 1.0, 1.0]),
            (f"EE posicao  : [{ee_pos[0]:+.3f}, {ee_pos[1]:+.3f}, {ee_pos[2]:+.3f}]",   [1.0, 1.0, 1.0]),
            (f"EE veloc.   : [{ee_vel[0]:+.3f}, {ee_vel[1]:+.3f}, {ee_vel[2]:+.3f}]",   [1.0, 1.0, 1.0]),
            (f"Garra       : {fingers:.3f} m  ({gripper_state})",                         [1.0, 0.8, 0.2] if gripper_state == "ABERTA" else [0.2, 1.0, 0.2]),
            (f"Cubo posicao: [{cube_pos[0]:+.3f}, {cube_pos[1]:+.3f}, {cube_pos[2]:+.3f}]", [1.0, 1.0, 1.0]),
            (f"Target      : [{target_pos[0]:+.3f}, {target_pos[1]:+.3f}, {target_pos[2]:+.3f}]", [1.0, 1.0, 1.0]),
            (f"Dist EE->Cubo    : {dist_ee_cube:.4f} m",                                  [1.0, 1.0, 1.0]),
            (f"Dist Cubo->Target: {dist_cube_tgt:.4f} m",                                 [1.0, 1.0, 1.0]),
            (f"Reward      : {reward:+.4f}",                                              [1.0, 1.0, 1.0]),
            (f"Sucesso     : {success}",                                                   [0.2, 1.0, 0.2] if success else [1.0, 1.0, 1.0]),
        ]

        for i, (label, (text, color)) in enumerate(zip(self._LABELS, lines)):
            pos = [self._X, self._Y, self._Z_TOP - i * self._Z_STEP]
            self._update(label, text, pos, color)

    def _update(self, key: str, text: str, position: list, color: list) -> None:
        kwargs = dict(textPosition=position, textColorRGB=color, textSize=1.3, lifeTime=0)
        if key in self._ids:
            self._client.addUserDebugText(text, replaceItemUniqueId=self._ids[key], **kwargs)
        else:
            self._ids[key] = self._client.addUserDebugText(text, **kwargs)


class TkOverlay:
    """Janela tkinter separada que exibe informações do MAPE-K ao lado do simulador."""

    _BG    = "#1e1e2e"
    _TAGS  = {
        "header":  {"foreground": "#cdd6f4", "font": ("Consolas", 10, "bold")},
        "cyan":    {"foreground": "#89dceb"},
        "yellow":  {"foreground": "#f9e2af"},
        "red":     {"foreground": "#f38ba8"},
        "green":   {"foreground": "#a6e3a1"},
        "dim":     {"foreground": "#585b70"},
        "white":   {"foreground": "#cdd6f4"},
        "sep":     {"foreground": "#45475a"},
    }

    def __init__(self, obstacle_meta: dict | None = None) -> None:
        self._obstacle_meta = obstacle_meta or {}
        self._queue  = queue.Queue(maxsize=1)
        self._ready  = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait()

    def _run(self) -> None:
        self._root = tk.Tk()
        self._root.title("MAPE-K Debug")
        self._root.configure(bg=self._BG)
        self._root.geometry("+960+60")

        self._text = tk.Text(
            self._root,
            font=("Consolas", 10),
            bg=self._BG,
            fg="#cdd6f4",
            width=62,
            height=24,
            state="disabled",
            wrap="none",
            relief="flat",
            padx=10,
            pady=8,
            cursor="arrow",
        )
        self._text.pack(fill="both", expand=True)

        for tag, opts in self._TAGS.items():
            self._text.tag_configure(tag, **opts)

        self._ready.set()
        self._root.after(50, self._poll)
        self._root.mainloop()

    def _poll(self) -> None:
        try:
            segments = self._queue.get_nowait()
            self._text.configure(state="normal")
            self._text.delete("1.0", "end")
            for text, tag in segments:
                self._text.insert("end", text, tag)
            self._text.configure(state="disabled")
        except queue.Empty:
            pass
        if self._root.winfo_exists():
            self._root.after(50, self._poll)

    def render(self, episode: int, step: int, obs: dict, reward: float,
               info: dict, task=None, robot=None, sim=None, mapek_state=None, action=None) -> None:
        if mapek_state is None:
            return

        m             = mapek_state
        gripper_state = "ABERTA" if m.fingers_width > 0.02 else "FECHADA"
        success       = info.get("is_success", False)

        s: list[tuple[str, str]] = []
        s.append((f"  MAPE-K  |  Ep {episode:>2}  |  Step {step:>4}\n", "header"))
        s.append(("  " + "─" * 56 + "\n", "sep"))
        s.append((f"  Estratégia      : {m.current_strategy.value}\n",  "cyan"))
        s.append((f"  Situação        : {m.current_situation.value}\n", "cyan"))
        s.append((f"  Obstáculo caminho: {'SIM' if m.obstacle_in_path else 'nao'}\n",
                  "red" if m.obstacle_in_path else "white"))
        for name, pos in m.obstacle_positions.items():
            s.append((f"  Obstáculo [{name}]: [{pos[0]:+.3f}, {pos[1]:+.3f}, {pos[2]:+.3f}]\n", "yellow"))
            meta = self._obstacle_meta.get(name, {})
            if meta:
                sz = meta.get("size", [])
                sz_str = f"[{', '.join(f'{v:.3f}' for v in sz)}]" if sz else "?"
                s.append((f"    tipo : {meta.get('type', '?')}   massa: {meta.get('mass', '?')} kg   tamanho: {sz_str}\n", "dim"))
        s.append(("  " + "·" * 54 + "\n", "sep"))
        s.append((f"  EE posição      : [{m.ee_position[0]:+.3f}, {m.ee_position[1]:+.3f}, {m.ee_position[2]:+.3f}]\n",   "white"))
        s.append((f"  EE velocidade   : [{m.ee_velocity[0]:+.3f}, {m.ee_velocity[1]:+.3f}, {m.ee_velocity[2]:+.3f}]\n",   "white"))
        s.append((f"  Garra           : {m.fingers_width:.3f} m  ({gripper_state})\n",
                  "yellow" if gripper_state == "ABERTA" else "green"))
        s.append((f"  Cubo posição    : [{m.cube_position[0]:+.3f}, {m.cube_position[1]:+.3f}, {m.cube_position[2]:+.3f}]\n", "white"))
        s.append((f"  Target          : [{m.target_position[0]:+.3f}, {m.target_position[1]:+.3f}, {m.target_position[2]:+.3f}]\n", "white"))
        s.append((f"  Dist EE→Cubo    : {m.dist_ee_to_cube:.4f} m\n",    "white"))
        s.append((f"  Dist Cubo→Target: {m.dist_cube_to_target:.4f} m\n", "white"))
        s.append((f"  Reward          : {reward:+.4f}\n",                 "white"))
        s.append((f"  Sucesso         : {success}\n", "green" if success else "white"))
        if m.joint_angles:
            s.append((f"  Juntas ângulos  : [{', '.join(f'{a:+.2f}' for a in m.joint_angles)}]\n",     "white"))
            s.append((f"  Juntas veloc.   : [{', '.join(f'{v:+.2f}' for v in m.joint_velocities)}]\n", "white"))
        cr = m.cube_rotation
        cv = m.cube_linear_velocity
        s.append((f"  Cubo rotação    : [{cr[0]:+.3f}, {cr[1]:+.3f}, {cr[2]:+.3f}]  (roll/pitch/yaw)\n", "white"))
        s.append((f"  Cubo vel.linear : [{cv[0]:+.3f}, {cv[1]:+.3f}, {cv[2]:+.3f}]\n",                   "white"))
        if action is not None:
            s.append((f"  Action          : [{action[0]:+.3f}, {action[1]:+.3f}, {action[2]:+.3f}, {action[3]:+.3f}]  (dx, dy, dz, gripper)\n", "cyan"))

        try:
            self._queue.put_nowait(s)
        except queue.Full:
            pass

    def close(self) -> None:
        if hasattr(self, "_root") and self._root.winfo_exists():
            self._root.after(0, self._root.destroy)


def print_step(episode: int, step: int, obs: dict, reward: float, info: dict, task=None, robot=None, sim=None) -> None:
    o = obs["observation"]
    # obs layout: [ee_x, ee_y, ee_z, ee_vx, ee_vy, ee_vz, fingers_width, cube_x, cube_y, cube_z]
    ee_pos        = o[0:3]
    ee_vel        = o[3:6]
    fingers       = o[6]
    cube_pos      = o[7:10]
    target_pos    = obs["desired_goal"]
    dist_ee_cube  = float(np.linalg.norm(ee_pos - cube_pos))
    dist_cube_tgt = float(np.linalg.norm(cube_pos - target_pos))
    gripper_state = "ABERTA" if fingers > 0.02 else "FECHADA"

    task_name = type(task).__name__ if task is not None else "?"
    print(_LINE)
    print(f" {task_name} | Ep {episode:>2} | Step {step:>3}")
    print(_LINE)
    print(f"  EE posição      : [{ee_pos[0]:+.3f}, {ee_pos[1]:+.3f}, {ee_pos[2]:+.3f}]")
    print(f"  EE velocidade   : [{ee_vel[0]:+.3f}, {ee_vel[1]:+.3f}, {ee_vel[2]:+.3f}]")
    print(f"  Garra           : {fingers:.3f} m  ({gripper_state})")
    print(f"  Cubo posição    : [{cube_pos[0]:+.3f}, {cube_pos[1]:+.3f}, {cube_pos[2]:+.3f}]")
    print(f"  Target          : [{target_pos[0]:+.3f}, {target_pos[1]:+.3f}, {target_pos[2]:+.3f}]")
    print(f"  Dist EE→Cubo    : {dist_ee_cube:.4f} m")
    print(f"  Dist Cubo→Target: {dist_cube_tgt:.4f} m")
    print(f"  Reward          : {reward:+.4f}")
    print(f"  Sucesso         : {info['is_success']}")

    if robot is not None:
        joint_angles = [robot.get_joint_angle(i) for i in range(7)]
        joint_vels   = [robot.get_joint_velocity(i) for i in range(7)]
        angles_str   = ", ".join(f"{a:+.2f}" for a in joint_angles)
        vels_str     = ", ".join(f"{v:+.2f}" for v in joint_vels)
        print(f"  Juntas ângulos  : [{angles_str}]")
        print(f"  Juntas veloc.   : [{vels_str}]")

    if sim is not None:
        cube_rot     = sim.get_base_rotation("cube_1", type="euler")
        cube_lin_vel = sim.get_base_velocity("cube_1")
        print(f"  Cubo rotação    : [{cube_rot[0]:+.3f}, {cube_rot[1]:+.3f}, {cube_rot[2]:+.3f}]  (roll/pitch/yaw)")
        print(f"  Cubo vel.linear : [{cube_lin_vel[0]:+.3f}, {cube_lin_vel[1]:+.3f}, {cube_lin_vel[2]:+.3f}]")


def print_mapek_step(episode: int, step: int, obs: dict, reward: float, info: dict,
                     mapek_state=None, robot=None, sim=None, obstacle_meta: dict | None = None,
                     action=None) -> None:
    if mapek_state is None:
        return

    m             = mapek_state
    gripper_state = "ABERTA" if m.fingers_width > 0.02 else "FECHADA"

    print(_LINE)
    print(f" MAPE-K | Ep {episode:>2} | Step {step:>3}")
    print(_LINE)
    print(f"  Estratégia      : {m.current_strategy.value}")
    print(f"  Situação        : {m.current_situation.value}")
    print(f"  Obstáculo caminho: {'SIM' if m.obstacle_in_path else 'nao'}")
    for name, pos in m.obstacle_positions.items():
        print(f"  Obstáculo [{name}]: [{pos[0]:+.3f}, {pos[1]:+.3f}, {pos[2]:+.3f}]")
        meta = (obstacle_meta or {}).get(name, {})
        if meta:
            sz     = meta.get("size", [])
            sz_str = f"[{', '.join(f'{v:.3f}' for v in sz)}]" if sz else "?"
            print(f"    tipo : {meta.get('type', '?')}   massa: {meta.get('mass', '?')} kg   tamanho: {sz_str}")
    print("  " + "·" * 40)
    print(f"  EE posição      : [{m.ee_position[0]:+.3f}, {m.ee_position[1]:+.3f}, {m.ee_position[2]:+.3f}]")
    print(f"  EE velocidade   : [{m.ee_velocity[0]:+.3f}, {m.ee_velocity[1]:+.3f}, {m.ee_velocity[2]:+.3f}]")
    print(f"  Garra           : {m.fingers_width:.3f} m  ({gripper_state})")
    print(f"  Cubo posição    : [{m.cube_position[0]:+.3f}, {m.cube_position[1]:+.3f}, {m.cube_position[2]:+.3f}]")
    print(f"  Target          : [{m.target_position[0]:+.3f}, {m.target_position[1]:+.3f}, {m.target_position[2]:+.3f}]")
    print(f"  Dist EE→Cubo    : {m.dist_ee_to_cube:.4f} m")
    print(f"  Dist Cubo→Target: {m.dist_cube_to_target:.4f} m")
    print(f"  Reward          : {reward:+.4f}")
    print(f"  Sucesso         : {info['is_success']}")
    if m.joint_angles:
        print(f"  Juntas ângulos  : [{', '.join(f'{a:+.2f}' for a in m.joint_angles)}]")
        print(f"  Juntas veloc.   : [{', '.join(f'{v:+.2f}' for v in m.joint_velocities)}]")
    cr = m.cube_rotation
    cv = m.cube_linear_velocity
    print(f"  Cubo rotação    : [{cr[0]:+.3f}, {cr[1]:+.3f}, {cr[2]:+.3f}]  (roll/pitch/yaw)")
    print(f"  Cubo vel.linear : [{cv[0]:+.3f}, {cv[1]:+.3f}, {cv[2]:+.3f}]")
    if action is not None:
        print(f"  Action          : [{action[0]:+.3f}, {action[1]:+.3f}, {action[2]:+.3f}, {action[3]:+.3f}]  (dx, dy, dz, gripper)")
