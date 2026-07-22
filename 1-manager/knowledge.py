from dataclasses import dataclass, field
from typing import Dict, List

import numpy as np

# Strategies are plain strings (e.g. "PUSH", "SCRIPTED.left_right") loaded from YAML.
Strategy = str


@dataclass
class SystemState:
    ee_position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    ee_velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))
    fingers_width: float = 0.0
    cube_position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    cube_rotation: np.ndarray = field(default_factory=lambda: np.zeros(3))
    cube_linear_velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))
    target_position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    dist_ee_to_cube: float = 0.0
    dist_cube_to_target: float = 0.0
    joint_angles: List[float] = field(default_factory=list)
    joint_velocities: List[float] = field(default_factory=list)
    action: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    obstacle_count_in_path: int = 0
    obstacle_in_path: bool = False
    episode: int = 0
    reward: float = 0.0
    is_success: bool = False
    current_strategy: str = "PUSH"
    current_situation: str = "normal"
    step: int = 0

    def to_eval_dict(self) -> dict:
        ee  = self.ee_position
        ev  = self.ee_velocity
        cb  = self.cube_position
        rot = self.cube_rotation
        clv = self.cube_linear_velocity
        tgt = self.target_position
        ja  = (self.joint_angles + [0.0] * 7)[:7]

        return {
            "episode": self.episode,
            "step":    self.step,
            "ee_x":  float(ee[0]),  "ee_y":  float(ee[1]),  "ee_z":  float(ee[2]),
            "ee_vx": float(ev[0]),  "ee_vy": float(ev[1]),  "ee_vz": float(ev[2]),
            "fingers_width": float(self.fingers_width),
            "cube_x": float(cb[0]),    "cube_y": float(cb[1]),    "cube_z": float(cb[2]),
            "cube_roll":  float(rot[0]), "cube_pitch": float(rot[1]), "cube_yaw": float(rot[2]),
            "cube_vx": float(clv[0]),  "cube_vy": float(clv[1]),  "cube_vz": float(clv[2]),
            "target_x": float(tgt[0]), "target_y": float(tgt[1]), "target_z": float(tgt[2]),
            "dist_ee_to_cube":     float(self.dist_ee_to_cube),
            "dist_cube_to_target": float(self.dist_cube_to_target),
            "reward":     float(self.reward),
            "is_success": bool(self.is_success),
            "obstacle_in_path":       bool(self.obstacle_in_path),
            "obstacle_count_in_path": int(self.obstacle_count_in_path),
            "action_x":       float(self.action[0]),
            "action_y":       float(self.action[1]),
            "action_z":       float(self.action[2]),
            "action_gripper": float(self.action[3]),
            "j0": float(ja[0]), "j1": float(ja[1]), "j2": float(ja[2]),
            "j3": float(ja[3]), "j4": float(ja[4]), "j5": float(ja[5]), "j6": float(ja[6]),
        }


@dataclass
class Knowledge:
    adaptation_options: dict = field(default_factory=dict)
    situation_strategy_map: Dict[str, str] = field(default=None)

    def __post_init__(self):
        if self.situation_strategy_map is None:
            self.situation_strategy_map = {"normal": "PUSH"}
