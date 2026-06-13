from typing import List, Tuple

import numpy as np
from panda_gym.envs.robots.panda import Panda
from panda_gym.pybullet import PyBullet


def setup_environment(configs: dict) -> Tuple[PyBullet, Panda]:
    simulation = PyBullet(render_mode=configs["simulation"]["render_mode"])

    environment_cfg = configs["environment"]
    robot_cfg       = environment_cfg["robot"]

    with simulation.no_rendering():
        _create_scene(simulation, environment_cfg["scene"]["table"])
        _create_objects(simulation, environment_cfg.get("objects", []))
        _create_obstacles(simulation, environment_cfg.get("obstacles", []))
        _create_targets(simulation, configs["target_goal"])

    robot = Panda(
        simulation,
        block_gripper=robot_cfg["block_gripper"],
        base_position=np.array(robot_cfg["base_position"]),
        control_type=robot_cfg["control_type"],
    )

    return simulation, robot


def _create_scene(simulation: PyBullet, table: dict) -> None:
    simulation.create_plane(z_offset=-0.4)
    simulation.create_table(
        length=table["length"],
        width=table["width"],
        height=table["height"],
        x_offset=table["x_offset"],
    )


def _create_objects(simulation: PyBullet, objects: list) -> None:
    for obj in objects:
        if obj["type"] == "box":
            size = np.array(obj["size"])
            simulation.create_box(
                body_name=obj["name"],
                half_extents=size / 2,
                mass=obj["mass"],
                position=np.array(obj["initial_position"]),
                rgba_color=np.array(obj["color"]),
                lateral_friction=obj.get("lateral_friction"),
                spinning_friction=obj.get("spinning_friction"),
            )


def _create_obstacles(simulation: PyBullet, obstacles: list) -> None:
    for obs in obstacles:
        if obs["type"] == "box":
            size = np.array(obs["size"])
            simulation.create_box(
                body_name=obs["name"],
                half_extents=size / 2,
                mass=obs["mass"],
                position=np.array(obs["position"]),
                rgba_color=np.array(obs["color"]),
            )


def _create_targets(simulation: PyBullet, target_goal_cfg: dict) -> None:
    mode, positions, colors = _parse_target_goals(target_goal_cfg)

    for i, (position, color) in enumerate(zip(positions, colors)):
        name = "target" if i == 0 else f"target_{i}"
        simulation.create_sphere(
            body_name=name,
            radius=0.02,
            mass=0.0,
            ghost=True,
            position=np.array(position, dtype=np.float32),
            rgba_color=np.array(color),
        )


_COLOR_ACTIVE  = [0.1, 0.9, 0.1, 0.8]   # verde — alvo atual
_COLOR_PENDING = [0.9, 0.5, 0.1, 0.5]  # laranja — demais alvos


def _parse_target_goals(target_goal_cfg: dict):
    for key in ("goal_options", "goal_sequence", "goal_set"):
        if key in target_goal_cfg:
            positions = target_goal_cfg[key]
            mode = key.replace("goal_", "")
            n = len(positions)
            colors = [_COLOR_ACTIVE] + [_COLOR_PENDING] * (n - 1)
            return mode, positions, colors

    raise ValueError("target_goal_cfg deve conter goal_options, goal_sequence ou goal_set")
