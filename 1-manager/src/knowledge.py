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
    # ASM monitored parameters
    object_available:        int = 0
    task_started:            int = 0
    gripper_width_cm:        int = 0
    distance_ee_object_cm:   int = 0
    grasp_completed:         int = 0
    finger_contacts:         int = 0
    grasp_attempts:          int = 0
    object_lift_height_cm:   int = 0
    distance_object_goal_cm: int = 0
    task_aborted:            int = 0
    # managing perception — unmapped fields from perception msg
    current_subtask:    str  = ""
    current_task:       str  = ""
    active_target_name: str  = ""
    obstacles:          dict = field(default_factory=dict)
    objects:            dict = field(default_factory=dict)
    scripts:            dict = field(default_factory=dict)
    target_goal:        dict = field(default_factory=dict)
    scene:              dict = field(default_factory=dict)
    robot_config:       dict = field(default_factory=dict)
    obstacle_positions: dict = field(default_factory=dict)
    # MAPE-K state
    current_asm_scenario: str = "__init__"
    goal_status: str = "not_applicable"
    matched_scenario: object = None

    def to_new_perception(self) -> dict:
        ee  = self.ee_position
        ev  = self.ee_velocity
        cb  = self.cube_position
        rot = self.cube_rotation
        clv = self.cube_linear_velocity
        tgt = self.target_position
        ja  = (self.joint_angles + [0.0] * 7)[:7]
        jv  = (self.joint_velocities + [0.0] * 7)[:7]
        act = (self.action + [0.0] * 4)[:4]

        return {
            # identity
            "episode": self.episode,
            "step":    self.step,
            # ASM monitored parameters (processed)
            "object_available":        int(self.object_available),
            "task_started":            int(self.task_started),
            "gripper_width_cm":        int(self.gripper_width_cm),
            "distance_ee_object_cm":   int(self.distance_ee_object_cm),
            "grasp_completed":         int(self.grasp_completed),
            "finger_contacts":         int(self.finger_contacts),
            "grasp_attempts":          int(self.grasp_attempts),
            "object_lift_height_cm":   int(self.object_lift_height_cm),
            "distance_object_goal_cm": int(self.distance_object_goal_cm),
            "task_aborted":            int(self.task_aborted),
            # raw sensor scalars (observed)
            "fingers_width":           float(self.fingers_width),
            "dist_ee_to_cube":         float(self.dist_ee_to_cube),
            "dist_cube_to_target":     float(self.dist_cube_to_target),
            "obstacle_in_path":        bool(self.obstacle_in_path),
            "obstacle_count_in_path":  int(self.obstacle_count_in_path),
            "reward":                  float(self.reward),
            "is_success":              bool(self.is_success),
            # raw sensor arrays (observed)
            "ee_x":  float(ee[0]),  "ee_y":  float(ee[1]),  "ee_z":  float(ee[2]),
            "ee_vx": float(ev[0]),  "ee_vy": float(ev[1]),  "ee_vz": float(ev[2]),
            "cube_x": float(cb[0]), "cube_y": float(cb[1]), "cube_z": float(cb[2]),
            "cube_roll":  float(rot[0]), "cube_pitch": float(rot[1]), "cube_yaw": float(rot[2]),
            "cube_vx": float(clv[0]), "cube_vy": float(clv[1]), "cube_vz": float(clv[2]),
            "target_x": float(tgt[0]), "target_y": float(tgt[1]), "target_z": float(tgt[2]),
            "action_x": float(act[0]), "action_y": float(act[1]),
            "action_z": float(act[2]), "action_gripper": float(act[3]),
            "j0": float(ja[0]), "j1": float(ja[1]), "j2": float(ja[2]),
            "j3": float(ja[3]), "j4": float(ja[4]), "j5": float(ja[5]), "j6": float(ja[6]),
            "jv0": float(jv[0]), "jv1": float(jv[1]), "jv2": float(jv[2]),
            "jv3": float(jv[3]), "jv4": float(jv[4]), "jv5": float(jv[5]), "jv6": float(jv[6]),
            # task context
            "current_subtask":    self.current_subtask,
            "current_task":       self.current_task,
            "active_target_name": self.active_target_name,
            # dicts — DejaVu serializa conforme necessário
            "objects":            self.objects,
            "obstacles":          self.obstacles,
            "scene":              self.scene,
            "robot_config":       self.robot_config,
            "target_goal":        self.target_goal,
            "scripts":            self.scripts,
            "obstacle_positions": self.obstacle_positions,
        }

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
            "current_subtask":        self.current_subtask,
            # ASM monitored parameters
            "object_available":       int(self.object_available),
            "task_started":           int(self.task_started),
            "gripper_width_cm":       int(self.gripper_width_cm),
            "distance_ee_object_cm":  int(self.distance_ee_object_cm),
            "grasp_completed":        int(self.grasp_completed),
            "finger_contacts":        int(self.finger_contacts),
            "grasp_attempts":         int(self.grasp_attempts),
            "object_lift_height_cm":  int(self.object_lift_height_cm),
            "distance_object_goal_cm":int(self.distance_object_goal_cm),
            "task_aborted":           int(self.task_aborted),
        }


@dataclass
class Knowledge:
    adaptation_options: dict = field(default_factory=dict)
    situation_strategy_map: Dict[str, str] = field(default=None)

    def __post_init__(self):
        if self.situation_strategy_map is None:
            self.situation_strategy_map = {"normal": "PUSH"}
