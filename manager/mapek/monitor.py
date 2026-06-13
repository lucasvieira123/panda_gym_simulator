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
        state.ee_position       = np.array(o[0:3],  dtype=np.float32)
        state.ee_velocity       = np.array(o[3:6],  dtype=np.float32)
        state.fingers_width     = float(o[6])
        state.cube_position     = np.array(o[7:10], dtype=np.float32)
        state.target_position   = np.array(obs["desired_goal"], dtype=np.float32)
        state.dist_ee_to_cube   = float(np.linalg.norm(state.ee_position - state.cube_position))
        state.dist_cube_to_target = float(np.linalg.norm(state.cube_position - state.target_position))

        state.joint_angles    = [self.robot.get_joint_angle(i)    for i in range(7)]
        state.joint_velocities = [self.robot.get_joint_velocity(i) for i in range(7)]

        state.cube_rotation       = np.array(self.sim.get_base_rotation("cube_1", type="euler"), dtype=np.float32)
        state.cube_linear_velocity = np.array(self.sim.get_base_velocity("cube_1"),              dtype=np.float32)

        for name in self.knowledge.obstacle_names:
            try:
                state.obstacle_positions[name] = self.sim.get_base_position(name)
            except KeyError:
                pass

        state.step += 1
        return state
