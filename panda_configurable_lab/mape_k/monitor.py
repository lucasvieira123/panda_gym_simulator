from __future__ import annotations

from typing import Any, Dict, Optional

import numpy as np


# Mudança mínima no desired_goal (metros) para goal_changed ser True
GOAL_CHANGE_THRESHOLD = 0.01


class Monitor:
    """
    M — Monitor

    Responsabilidades:
      collect()       — lê o ambiente e devolve um estado estruturado
      build_context() — achata o estado em campos planos para o Analyzer
    """

    def collect(self, env, observation: Dict[str, Any]) -> dict:
        """
        Lê o ambiente PyBullet e a observação e devolve:

        {
            "ee"    : { position, velocity, orientation, fingers_width },
            "joints": { angles, velocities },
            "cube"  : { position, orientation, velocity, angular_vel },
            "goal"  : { achieved, desired, distance, height },
        }
        """
        robot = env.robot
        sim   = env.sim

        ee_pos  = robot.get_ee_position().tolist()
        ee_vel  = robot.get_ee_velocity().tolist()
        try:
            ee_ori = sim.get_link_orientation("panda", robot.ee_link).tolist()
        except Exception:
            ee_ori = [0.0, 0.0, 0.0, 1.0]
        fingers = float(robot.get_fingers_width())

        joint_angles = [float(robot.get_joint_angle(i))    for i in range(7)]
        joint_vels   = [float(robot.get_joint_velocity(i)) for i in range(7)]

        has_cube = "cube_1" in sim._bodies_idx
        cube = {
            "position":    sim.get_base_position("cube_1").tolist()         if has_cube else None,
            "orientation": sim.get_base_rotation("cube_1").tolist()         if has_cube else None,
            "velocity":    sim.get_base_velocity("cube_1").tolist()         if has_cube else None,
            "angular_vel": sim.get_base_angular_velocity("cube_1").tolist() if has_cube else None,
        }

        achieved     = observation.get("achieved_goal")
        desired      = observation.get("desired_goal")
        achieved_arr = np.asarray(achieved, dtype=float).reshape(-1, 3)[0] if achieved is not None else np.zeros(3)
        desired_arr  = np.asarray(desired,  dtype=float).reshape(-1, 3)[0] if desired  is not None else np.zeros(3)
        distance     = float(np.linalg.norm(achieved_arr - desired_arr))

        return {
            "ee"    : {"position": ee_pos, "velocity": ee_vel, "orientation": ee_ori, "fingers_width": fingers},
            "joints": {"angles": joint_angles, "velocities": joint_vels},
            "cube"  : cube,
            "goal"  : {
                "achieved": achieved_arr.tolist(),
                "desired" : desired_arr.tolist(),
                "distance": distance,
                "height"  : float(desired_arr[2]),
            },
        }

    def build_context(self, state: dict, prev_desired_goal: Optional[list], step_count: int) -> dict:
        """
        Achata o estado em campos planos usados nas condições Given do Analyzer.

        Campos disponíveis:
          step
          goal_changed              bool — desired_goal mudou > 1 cm desde o step anterior
          goal.distance             distância euclidiana achieved → desired (metros)
          goal.height               z do desired_goal
          goal.desired.x/y/z
          goal.achieved.x/y/z
          ee.speed                  magnitude da velocidade do ee (m/s)
          ee.fingers_width
          ee.position.x/y/z
          ee.velocity.x/y/z
          cube.speed                magnitude da velocidade do cubo (m/s)
          cube.position.x/y/z
        """
        ctx: dict = {"step": step_count}

        # goal_changed — campo computado, não existe diretamente no ambiente
        if prev_desired_goal is None:
            ctx["goal_changed"] = False
        else:
            delta = float(np.linalg.norm(
                np.array(state["goal"]["desired"]) - np.array(prev_desired_goal)
            ))
            ctx["goal_changed"] = delta > GOAL_CHANGE_THRESHOLD

        # goal
        ctx["goal.distance"] = state["goal"]["distance"]
        ctx["goal.height"]   = state["goal"]["height"]
        for i, ax in enumerate("xyz"):
            ctx[f"goal.desired.{ax}"]  = state["goal"]["desired"][i]
            ctx[f"goal.achieved.{ax}"] = state["goal"]["achieved"][i]

        # ee
        ctx["ee.fingers_width"] = state["ee"]["fingers_width"]
        ctx["ee.speed"] = float(np.linalg.norm(state["ee"]["velocity"]))
        for i, ax in enumerate("xyz"):
            ctx[f"ee.position.{ax}"] = state["ee"]["position"][i]
            ctx[f"ee.velocity.{ax}"] = state["ee"]["velocity"][i]

        # cube
        ctx["cube.speed"] = (
            float(np.linalg.norm(state["cube"]["velocity"]))
            if state["cube"]["velocity"] is not None else 0.0
        )
        if state["cube"]["position"] is not None:
            for i, ax in enumerate("xyz"):
                ctx[f"cube.position.{ax}"] = state["cube"]["position"][i]

        return ctx
