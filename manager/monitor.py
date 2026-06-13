import numpy as np

from knowledge import SystemState


class Monitor:
    def update(self, msg: dict, state: SystemState) -> SystemState:
        state.ee_position            = np.array(msg["ee_position"],     dtype=np.float32)
        state.ee_velocity            = np.array(msg["ee_velocity"],     dtype=np.float32)
        state.fingers_width          = float(msg["fingers_width"])
        state.cube_position          = np.array(msg["cube_position"],   dtype=np.float32)
        state.target_position        = np.array(msg["target_position"], dtype=np.float32)
        state.dist_ee_to_cube        = float(msg["dist_ee_to_cube"])
        state.dist_cube_to_target    = float(msg["dist_cube_to_target"])
        state.obstacle_in_path       = bool(msg.get("obstacle_in_path", False))
        state.obstacle_count_in_path = int(msg.get("obstacle_count_in_path", 0))
        if "action" in msg:
            state.action = [float(x) for x in msg["action"]]
        if "joint_angles" in msg:
            state.joint_angles     = msg["joint_angles"]
            state.joint_velocities = msg["joint_velocities"]
        if "cube_rotation" in msg:
            state.cube_rotation        = np.array(msg["cube_rotation"],        dtype=np.float32)
            state.cube_linear_velocity = np.array(msg["cube_linear_velocity"], dtype=np.float32)
        state.step       = int(msg.get("step", state.step))
        state.episode    = int(msg.get("episode", state.episode))
        state.reward     = float(msg.get("reward", 0.0))
        state.is_success = bool(msg.get("is_success", False))
        return state
