import numpy as np

from ._sensor import _Sensor

_CUBE_MARGIN = 0.02  # half-extent do cubo (4 cm / 2)


class ObstaclesInPathSensor(_Sensor):
    """
    Verifica quantos obstáculos bloqueiam o caminho em linha reta entre o cubo
    e o target ativo, usando a área física (XY) de cada obstáculo.

    A detecção é feita em 2D (plano XY da mesa): para cada obstáculo, expande
    seu AABB pelo half-extent do cubo (Minkowski sum) e testa se o segmento
    cubo→target cruza essa área expandida.
    """

    def __init__(self, configs: dict, env) -> None:
        super().__init__(configs)
        self._env = env

    def sense(self, simulation, robot, environment, obs: dict) -> dict:
        cube_xy   = np.array(obs["observation"][7:9], dtype=float)
        target_xy = np.array(obs["desired_goal"][:2],  dtype=float)

        count = 0
        for obs_cfg in self._env.get_obstacles().values():
            cx, cy = obs_cfg["current_position"][:2]
            hx = obs_cfg["size"][0] / 2 + _CUBE_MARGIN
            hy = obs_cfg["size"][1] / 2 + _CUBE_MARGIN

            if _segment_crosses_box_2d(cube_xy, target_xy,
                                       cx - hx, cx + hx,
                                       cy - hy, cy + hy):
                count += 1

        return {
            "obstacle_count_in_path": count,
            "obstacle_in_path":       count > 0,
        }


def _segment_crosses_box_2d(
    p0: np.ndarray, p1: np.ndarray,
    xmin: float, xmax: float,
    ymin: float, ymax: float,
) -> bool:
    """Liang-Barsky: True se o segmento 2D p0→p1 intersecta o AABB."""
    dx, dy = float(p1[0] - p0[0]), float(p1[1] - p0[1])
    t0, t1 = 0.0, 1.0

    for p, q in (
        (-dx, float(p0[0]) - xmin),
        ( dx, xmax - float(p0[0])),
        (-dy, float(p0[1]) - ymin),
        ( dy, ymax - float(p0[1])),
    ):
        if p == 0.0:
            if q < 0:
                return False
        elif p < 0:
            t0 = max(t0, q / p)
        else:
            t1 = min(t1, q / p)
        if t0 > t1:
            return False

    return True
