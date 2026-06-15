import numpy as np
from panda_gym.envs.robots.panda import Panda
from panda_gym.pybullet import PyBullet

_ORIENTATION_NEUTRAL = np.array([0.0, 0.0, 0.0, 1.0])

_COLOR_ACTIVE  = [0.1, 0.9, 0.1, 0.8]
_COLOR_PENDING = [0.9, 0.5, 0.1, 0.5]


class EnvironmentManager:
    def __init__(self, configs: dict) -> None:
        environment_cfg = configs["environment"]
        robot_cfg       = environment_cfg["robot"]

        self.sim = PyBullet(render_mode=configs["simulation"]["render_mode"])

        # dicts name → cfg completo para distinguir e descrever obstáculos e objetos
        self._obstacles:    dict[str, dict] = {}
        self._objects:      dict[str, dict] = {}
        self._target_names: list[str]       = []
        self._label_ids:    dict[str, int]  = {}

        with self.sim.no_rendering():
            self._create_scene(environment_cfg["scene"]["table"])
            self._create_objects(environment_cfg.get("objects", []))
            self._create_obstacles(environment_cfg.get("obstacles", []))
            self._create_targets(configs["target_goal"])

        self._create_all_labels()

        self.robot = Panda(
            self.sim,
            block_gripper=robot_cfg["block_gripper"],
            base_position=np.array(robot_cfg["base_position"]),
            control_type=robot_cfg["control_type"],
        )

    # ── setup ─────────────────────────────────────────────────────────────────

    def _create_scene(self, table: dict) -> None:
        self.sim.create_plane(z_offset=-0.4)
        self.sim.create_table(
            length=table["length"],
            width=table["width"],
            height=table["height"],
            x_offset=table["x_offset"],
            lateral_friction=table.get("lateral_friction"),
            spinning_friction=table.get("spinning_friction"),
        )

    def _create_objects(self, objects: list) -> None:
        for obj in objects:
            if obj["type"] == "box":
                self.sim.create_box(
                    body_name=obj["name"],
                    half_extents=np.array(obj["size"]) / 2,
                    mass=obj["mass"],
                    position=np.array(obj["initial_position"]),
                    rgba_color=np.array(obj["color"]),
                    lateral_friction=obj.get("lateral_friction"),
                    spinning_friction=obj.get("spinning_friction"),
                )
                self._objects[obj["name"]] = {
                    "type":              obj["type"],
                    "size":              obj["size"],
                    "mass":              obj["mass"],
                    "color":             obj["color"],
                    "initial_position":  obj["initial_position"],
                    "lateral_friction":  obj.get("lateral_friction"),
                    "spinning_friction": obj.get("spinning_friction"),
                }

    def _create_obstacles(self, obstacles: list) -> None:
        for obs in obstacles:
            if obs["type"] == "box":
                self.sim.create_box(
                    body_name=obs["name"],
                    half_extents=np.array(obs["size"]) / 2,
                    mass=obs["mass"],
                    position=np.array(obs["position"]),
                    rgba_color=np.array(obs["color"]),
                )
                self._obstacles[obs["name"]] = {
                    "type":  obs["type"],
                    "size":  obs["size"],
                    "mass":  obs["mass"],
                    "color": obs["color"],
                }

    def _create_targets(self, target_goal_cfg: dict) -> None:
        names, positions, colors = _parse_target_goals(target_goal_cfg)
        print("[EnvironmentManager] Targets criados:")
        for name, position, color in zip(names, positions, colors):
            self.sim.create_sphere(
                body_name=name,
                radius=0.02,
                mass=0.0,
                ghost=True,
                position=np.array(position, dtype=np.float32),
                rgba_color=np.array(color),
            )
            self._target_names.append(name)
            print(f"  {name:<12} → {position}")

    # ── leitura de estado ─────────────────────────────────────────────────────

    def get_obstacles(self) -> dict:
        """Retorna todos os obstáculos com cfg completo e posição atual do sim."""
        return {
            name: {**cfg, "current_position": self.sim.get_base_position(name).tolist()}
            for name, cfg in self._obstacles.items()
        }

    def get_objects(self) -> dict:
        """Retorna todos os objetos com cfg completo e posição atual do sim."""
        return {
            name: {**cfg, "current_position": self.sim.get_base_position(name).tolist()}
            for name, cfg in self._objects.items()
        }

    # ── runtime: obstáculos ───────────────────────────────────────────────────

    def move_obstacle(self, name: str, position: np.ndarray) -> None:
        """Reposiciona um obstáculo em tempo de execução."""
        self.sim.set_base_pose(name, np.array(position), _ORIENTATION_NEUTRAL)
        self._put_label(name)

    def add_obstacle(self, cfg: dict) -> None:
        """Adiciona um novo obstáculo em tempo de execução.

        cfg esperado: {name, size, position, color, mass (opcional)}
        """
        self.sim.create_box(
            body_name=cfg["name"],
            half_extents=np.array(cfg["size"]) / 2,
            mass=cfg.get("mass", 0.0),
            position=np.array(cfg["position"]),
            rgba_color=np.array(cfg["color"]),
        )
        self._obstacles[cfg["name"]] = {
            "type":  "box",
            "size":  cfg["size"],
            "mass":  cfg.get("mass", 0.0),
            "color": cfg["color"],
        }
        self._put_label(cfg["name"])

    def remove_obstacle(self, name: str) -> None:
        """Remove um obstáculo em tempo de execução."""
        self._remove_label(name)
        body_id = self.sim._bodies_idx.pop(name)
        self.sim.physics_client.removeBody(body_id)
        self._obstacles.pop(name, None)

    # ── runtime: objetos ──────────────────────────────────────────────────────

    def move_object(self, name: str, position: np.ndarray) -> None:
        """Reposiciona um objeto manipulável em tempo de execução."""
        self.sim.set_base_pose(name, np.array(position), _ORIENTATION_NEUTRAL)
        self._put_label(name)

    # ── runtime: robô ─────────────────────────────────────────────────────────

    def move_robot_base(self, position: np.ndarray) -> None:
        """Reposiciona a base do braço robótico em tempo de execução."""
        self.sim.set_base_pose("panda", np.array(position), _ORIENTATION_NEUTRAL)

    # ── runtime: goals ────────────────────────────────────────────────────────

    def move_target(self, name: str, position: np.ndarray) -> None:
        """Reposiciona uma esfera de goal em tempo de execução."""
        self.sim.set_base_pose(name, np.array(position), _ORIENTATION_NEUTRAL)
        self._put_label(name)

    # ── entry points da API ───────────────────────────────────────────────────

    def apply_environment_command(self, cmd: dict) -> None:
        """Despacha um comando de ambiente recebido via API.

        Ações suportadas:
          move_obstacle   — {action, name, position}
          add_obstacle    — {action, name, size, position, color, mass?}
          remove_obstacle — {action, name}
          move_object     — {action, name, position}
        """
        action = cmd.get("action")

        if action == "move_obstacle":
            self.move_obstacle(cmd["name"], cmd["position"])
        elif action == "add_obstacle":
            self.add_obstacle(cmd)
        elif action == "remove_obstacle":
            self.remove_obstacle(cmd["name"])
        elif action == "move_object":
            self.move_object(cmd["name"], cmd["position"])
        elif action == "move_robot_base":
            self.move_robot_base(cmd["position"])
        else:
            print(f"[EnvironmentManager] Ação desconhecida: {action}")

    def apply_goal_command(self, cmd: dict) -> None:
        """Despacha um comando de goal recebido via API.

        Ações suportadas:
          move_target — {action, name, position}
        """
        action = cmd.get("action")

        if action == "move_target":
            self.move_target(cmd["name"], cmd["position"])
        else:
            print(f"[EnvironmentManager] Ação de goal desconhecida: {action}")


    # ── labels visuais ────────────────────────────────────────────────────────

    def _put_label(self, name: str, z_offset: float = 0.0) -> None:
        pos = self.sim.get_base_position(name)
        label_pos = [float(pos[0]), float(pos[1]), float(pos[2]) + z_offset]
        kwargs = dict(textPosition=label_pos, textColorRGB=[0.0, 0.0, 0.0], textSize=1.0, lifeTime=0)
        if name in self._label_ids:
            self.sim.physics_client.addUserDebugText(name, replaceItemUniqueId=self._label_ids[name], **kwargs)
        else:
            self._label_ids[name] = self.sim.physics_client.addUserDebugText(name, **kwargs)

    def _remove_label(self, name: str) -> None:
        if name in self._label_ids:
            self.sim.physics_client.removeUserDebugItem(self._label_ids.pop(name))

    def _create_all_labels(self) -> None:
        for name in self._objects:
            self._put_label(name)
        for name in self._obstacles:
            self._put_label(name)
        for name in self._target_names:
            self._put_label(name)

    def refresh_object_labels(self) -> None:
        """Atualiza a posição das labels dos objetos a cada step (o braço os move)."""
        for name in self._objects:
            self._put_label(name)


# ── helpers ───────────────────────────────────────────────────────────────────

def _parse_target_goals(target_goal_cfg: dict):
    targets   = target_goal_cfg["targets"]
    names     = [t["name"]     for t in targets]
    positions = [t["position"] for t in targets]
    colors    = [_COLOR_ACTIVE] + [_COLOR_PENDING] * (len(positions) - 1)
    return names, positions, colors
