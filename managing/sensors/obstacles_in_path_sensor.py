import numpy as np

from ._sensor import _Sensor


class ObstaclesInPathSensor(_Sensor):
    """
    Calcula quantos obstáculos estão no caminho em linha reta entre o cubo e o target.
    Retorna obstacle_count_in_path e obstacle_in_path.
    """

    PATH_RADIUS = 0.10

    def sense(self, simulation, robot, environment, obs: dict) -> dict:
        cube_position   = np.array(obs["observation"][7:10], dtype=np.float32)
        target_position = np.array(obs["desired_goal"],      dtype=np.float32)

        obstacle_names = [o["name"] for o in self.configs["environment"].get("obstacles", [])]
        count = 0
        for name in obstacle_names:
            try:
                obs_pos = simulation.get_base_position(name)
                d = _point_to_segment_distance(
                    np.array(obs_pos, dtype=np.float32),
                    cube_position,
                    target_position,
                )
                if d < self.PATH_RADIUS:
                    count += 1
            except KeyError:
                pass

        return {
            "obstacle_count_in_path": count,
            "obstacle_in_path":       count > 0,
        }


def _point_to_segment_distance(point: np.ndarray, seg_a: np.ndarray, seg_b: np.ndarray) -> float:
    v  = seg_b - seg_a
    w  = point - seg_a
    c2 = float(np.dot(v, v))
    if c2 == 0.0:
        return float(np.linalg.norm(point - seg_a))
    t = max(0.0, min(1.0, float(np.dot(w, v)) / c2))
    return float(np.linalg.norm(point - (seg_a + t * v)))