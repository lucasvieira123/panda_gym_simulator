from typing import Tuple

import numpy as np
from panda_gym.envs.robots.panda import Panda
from panda_gym.pybullet import PyBullet


def start_simulation(sim_cfg: dict, environment_cfg: dict, target_goal_cfg: dict) -> Tuple[PyBullet, Panda]:
    sim = PyBullet(render_mode=sim_cfg["simulation"]["render_mode"])

    robot_cfg = environment_cfg["robot"]
    goal_position = np.array(target_goal_cfg["position"], dtype=np.float32)

    with sim.no_rendering():
        _create_scene(sim, environment_cfg["scene"]["table"])
        _create_objects(sim, environment_cfg.get("objects", []))
        _create_obstacles(sim, environment_cfg.get("obstacles", []))
        _create_target(sim, goal_position)

    robot = Panda(
        sim,
        block_gripper=robot_cfg["block_gripper"],
        base_position=np.array(robot_cfg["base_position"]),
        control_type=robot_cfg["control_type"],
    )

    return sim, robot


def _create_scene(sim: PyBullet, table: dict) -> None:
    sim.create_plane(z_offset=-0.4)
    sim.create_table(
        length=table["length"],
        width=table["width"],
        height=table["height"],
        x_offset=table["x_offset"],
    )


def _create_objects(sim: PyBullet, objects: list) -> None:
    for obj in objects:
        if obj["type"] == "box":
            size = np.array(obj["size"])
            sim.create_box(
                body_name=obj["name"],
                half_extents=size / 2,
                mass=obj["mass"],
                position=np.array(obj["initial_position"]),
                rgba_color=np.array(obj["color"]),
                lateral_friction=obj.get("lateral_friction"),
                spinning_friction=obj.get("spinning_friction"),
            )


def _create_obstacles(sim: PyBullet, obstacles: list) -> None:
    for obs in obstacles:
        if obs["type"] == "box":
            size = np.array(obs["size"])
            sim.create_box(
                body_name=obs["name"],
                half_extents=size / 2,
                mass=obs["mass"],
                position=np.array(obs["position"]),
                rgba_color=np.array(obs["color"]),
            )


def _create_target(sim: PyBullet, position: np.ndarray) -> None:
    sim.create_sphere(
        body_name="target",
        radius=0.02,
        mass=0.0,
        ghost=True,
        position=position,
        rgba_color=np.array([0.1, 0.9, 0.1, 0.3]),
    )
