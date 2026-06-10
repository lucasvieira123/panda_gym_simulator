from __future__ import annotations

from typing import Any, Dict

import numpy as np

from panda_gym.envs.core import RobotTaskEnv
from panda_gym.envs.robots.panda import Panda
from panda_gym.pybullet import PyBullet

from .configurable_task import ConfigurableTask


def make_configurable_env(config: Dict[str, Any]) -> RobotTaskEnv:
    simulation_config = config.get("simulation", {})
    robot_config = config.get("robot", {})
    task_config = config.get("task", {})

    sim = PyBullet(
        render_mode=simulation_config.get("render_mode", None),
    )

    robot = Panda(
        sim=sim,
        block_gripper=bool(robot_config.get("block_gripper", True)),
        base_position=np.array(robot_config.get("base_position", [-0.6, 0.0, 0.0]), dtype=float),
        control_type=robot_config.get("control_type", "ee"),
    )

    task_type = task_config.get("type", "configurable")

    if task_type == "configurable":
        task = ConfigurableTask(sim=sim, config=config)
    else:
        raise ValueError(f"Task ainda não suportada nesta versão: {task_type}")

    env = RobotTaskEnv(robot=robot, task=task)

    return env
