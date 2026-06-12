from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List

import numpy as np


class Strategy(Enum):
    PUSH = "PUSH"
    PICK_AND_PLACE_OVER = "PICK_AND_PLACE_OVER"
    SCRIPTED_script_1 = "SCRIPTED_script_1"
    SCRIPTED_reach_only = "SCRIPTED_reach_only"
    SCRIPTED_left_right = "SCRIPTED_left_right"



class Situation(Enum):
    NORMAL = "normal"
    PLANNED_OBSTACLE = "planned_obstacle"
    TWO_OBSTACLES = "two_obstacles"


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
    obstacle_positions: Dict[str, np.ndarray] = field(default_factory=dict)
    obstacle_in_path: bool = False
    current_strategy: Strategy = Strategy.PUSH
    current_situation: Situation = Situation.NORMAL
    step: int = 0


@dataclass
class Knowledge:
    """Parâmetros e histórico compartilhados entre os componentes MAPE-K."""
    obstacle_names: List[str] = field(default_factory=list)
    obstacle_path_radius: float = 0.10
    scripts: dict = field(default_factory=dict)
    situation_strategy_map: Dict[Situation, Strategy] = field(default_factory=lambda: {
        Situation.NORMAL:           Strategy.PUSH,
        Situation.PLANNED_OBSTACLE: Strategy.PICK_AND_PLACE_OVER,
        Situation.TWO_OBSTACLES:    Strategy.SCRIPTED_left_right,
    })
