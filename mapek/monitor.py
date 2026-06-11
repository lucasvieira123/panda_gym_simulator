import numpy as np

from .knowledge import Knowledge, SystemState


class Monitor:
    """
    Coleta dados brutos do ambiente a cada step e atualiza SystemState.

    Responsável por:
    - Posições de EE, cubo e target (via obs)
    - Posições dos obstáculos (via sim.get_base_position)
    - Detecção de contato físico robot↔obstáculo (via PyBullet getContactPoints)
    - Histórico de distância cubo→target para análise de estagnação
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

        state.collision_detected = self._detect_collision()

        self.knowledge.dist_history.append(state.dist_cube_to_target)
        if len(self.knowledge.dist_history) > self.knowledge.history_window:
            self.knowledge.dist_history.pop(0)

        state.step += 1
        return state

    def _detect_collision(self) -> bool:
        robot_id = self.sim._bodies_idx.get("panda")
        if robot_id is None:
            return False
        for name in self.knowledge.obstacle_names:
            obs_id = self.sim._bodies_idx.get(name)
            if obs_id is None:
                continue
            contacts = self.sim.physics_client.getContactPoints(bodyA=robot_id, bodyB=obs_id)
            if contacts:
                return True
        return False
