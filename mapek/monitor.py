import numpy as np

from .knowledge import Knowledge, SystemState


class Monitor:
    """
    Coleta dados brutos do ambiente a cada step e atualiza SystemState.

    Responsável por:
    - Posições de EE, cubo e target (via obs)
    - Posições dos obstáculos (via sim.get_base_position)
    """

    def __init__(self, sim, robot, knowledge: Knowledge) -> None:
        self.sim = sim
        self.robot = robot
        self.knowledge = knowledge

    def collect(self, obs: dict, state: SystemState) -> SystemState:
        o = obs["observation"]
        # layout: [ee_x, ee_y, ee_z, ee_vx, ee_vy, ee_vz, fingers, cube_x, cube_y, cube_z]
        state.ee_position = np.array(o[0:3], dtype=np.float32)
        state.cube_position = np.array(o[7:10], dtype=np.float32)
        state.target_position = np.array(obs["desired_goal"], dtype=np.float32)
        state.dist_cube_to_target = float(np.linalg.norm(state.cube_position - state.target_position))

        for name in self.knowledge.obstacle_names:
            try:
                state.obstacle_positions[name] = self.sim.get_base_position(name)
            except KeyError:
                pass

        state.step += 1
        return state
