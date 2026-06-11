from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List

import numpy as np


class Strategy(Enum):
    PUSH = "PUSH"
    PICK_AND_PLACE_OVER = "PICK_AND_PLACE_OVER"
    RECOVER = "RECOVER"


class Situation(Enum):
    NORMAL = "normal"
    PLANNED_OBSTACLE = "planned_obstacle"
    UNPLANNED_STAGNATION = "unplanned_stagnation"
    UNPLANNED_COLLISION = "unplanned_collision"


@dataclass
class SystemState:
    ee_position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    cube_position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    target_position: np.ndarray = field(default_factory=lambda: np.zeros(3))
    dist_cube_to_target: float = 0.0
    obstacle_positions: Dict[str, np.ndarray] = field(default_factory=dict)
    obstacle_in_path: bool = False
    collision_detected: bool = False
    stagnation_count: int = 0
    current_strategy: Strategy = Strategy.PUSH
    current_situation: Situation = Situation.NORMAL
    step: int = 0


@dataclass
class Knowledge:
    """Parâmetros e histórico compartilhados entre os componentes MAPE-K."""
    obstacle_names: List[str] = field(default_factory=list)

    # raio do tubo ao longo do segmento cubo→target para detecção de bloqueio
    obstacle_path_radius: float = 0.10
    # passos consecutivos sem progresso para disparar situação não prevista
    stagnation_steps: int = 20
    # redução mínima de distância no janela para não ser considerado estagnado
    progress_min: float = 0.002
    # distância para considerar contato físico relevante
    contact_distance: float = 0.02

    dist_history: List[float] = field(default_factory=list)
    history_window: int = 20
