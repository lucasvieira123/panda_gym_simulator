import numpy as np

from .knowledge import Knowledge, Situation, Strategy, SystemState


class Analyzer:
    """
    Identifica sintomas no estado do sistema e classifica a Situation atual.

    Prioridade de situações (maior para menor):
      1. UNPLANNED_COLLISION  – contato físico durante PUSH
      2. UNPLANNED_STAGNATION – cubo sem progresso por N passos (apenas durante PUSH)
      3. PLANNED_OBSTACLE     – obstáculo geométrico no caminho cubo→target
      4. NORMAL               – sem anomalias detectadas
    """

    def __init__(self, knowledge: Knowledge) -> None:
        self.knowledge = knowledge

    def analyze(self, state: SystemState) -> SystemState:
        state.obstacle_in_path = self._obstacle_in_path(state)

        if state.current_strategy == Strategy.PUSH:
            if self._is_stagnant():
                state.stagnation_count += 1
            else:
                state.stagnation_count = 0
        else:
            # durante PICK_OVER ou RECOVER não há critério de estagnação por push
            state.stagnation_count = 0

        if state.collision_detected and state.current_strategy == Strategy.PUSH:
            state.current_situation = Situation.UNPLANNED_COLLISION
        elif state.stagnation_count >= self.knowledge.stagnation_steps:
            state.current_situation = Situation.UNPLANNED_STAGNATION
        elif state.obstacle_in_path:
            state.current_situation = Situation.PLANNED_OBSTACLE
        else:
            state.current_situation = Situation.NORMAL

        return state

    def _obstacle_in_path(self, state: SystemState) -> bool:
        for _, obs_pos in state.obstacle_positions.items():
            d = _point_to_segment_distance(
                np.array(obs_pos, dtype=np.float32),
                state.cube_position,
                state.target_position,
            )
            if d < self.knowledge.obstacle_path_radius:
                return True
        return False

    def _is_stagnant(self) -> bool:
        h = self.knowledge.dist_history
        if len(h) < self.knowledge.history_window:
            return False
        # progresso positivo = cubo se aproximou do target ao longo da janela
        total_progress = h[0] - h[-1]
        return total_progress < self.knowledge.progress_min


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
