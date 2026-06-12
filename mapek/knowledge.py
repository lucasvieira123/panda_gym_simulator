from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List

import numpy as np


class Strategy(Enum):
    PUSH = "PUSH"
    PICK_AND_PLACE_OVER = "PICK_AND_PLACE_OVER"


class Situation(Enum):
    NORMAL = "normal"
    PLANNED_OBSTACLE = "planned_obstacle"


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

    # raio do tubo ao longo do segmento cubo→target para detecção de bloqueio
    obstacle_path_radius: float = 0.10
