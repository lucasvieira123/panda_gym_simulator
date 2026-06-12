import numpy as np

from .knowledge import Knowledge, Situation, SystemState


class Analyzer:
    """
    Identifica sintomas no estado do sistema e classifica a Situation atual.

    Regras:
      PLANNED_OBSTACLE – obstáculo geométrico no caminho cubo→target
      NORMAL           – sem obstáculo detectado
    """

    def __init__(self, knowledge: Knowledge) -> None:
        self.knowledge = knowledge

    def analyze(self, state: SystemState) -> SystemState:
        count = self._count_obstacles_in_path(state)
        state.obstacle_in_path = count > 0

        if count >= 2:
            state.current_situation = Situation.TWO_OBSTACLES
        elif count == 1:
            state.current_situation = Situation.PLANNED_OBSTACLE
        else:
            state.current_situation = Situation.NORMAL

        return state

    def _count_obstacles_in_path(self, state: SystemState) -> int:
        count = 0
        for _, obs_pos in state.obstacle_positions.items():
            d = _point_to_segment_distance(
                np.array(obs_pos, dtype=np.float32),
                state.cube_position,
                state.target_position,
            )
            if d < self.knowledge.obstacle_path_radius:
                count += 1
        return count


def _point_to_segment_distance(point: np.ndarray, seg_a: np.ndarray, seg_b: np.ndarray) -> float:
    """Distância mínima entre um ponto e um segmento de reta."""
    v = seg_b - seg_a
    w = point - seg_a
    c2 = float(np.dot(v, v))
    if c2 == 0.0:
        return float(np.linalg.norm(point - seg_a))
    t = float(np.dot(w, v)) / c2
    t = max(0.0, min(1.0, t))
    closest = seg_a + t * v
    return float(np.linalg.norm(point - closest))
