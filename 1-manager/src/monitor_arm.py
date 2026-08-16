import numpy as np

from knowledge import SystemState
from monitor_abs import MonitorAbs

_GRIPPER_CLOSED_THRESHOLD = 0.060  # m — garra considerada fechada (≤) — cobre objetos até ~6cm
_GRIPPER_OPEN_THRESHOLD   = 0.075  # m — garra considerada aberta (histerese)
_FINGER_LENGTH_M          = 0.025  # m — distância pulso→ponta dos dedos (Franka Panda)


class MonitorARM(MonitorAbs):
    def __init__(self) -> None:
        self._initial_cube_z: float | None = None
        self._prev_grasp_completed: int    = 0
        self._grasp_attempts: int          = 0

    def update(self, msg: dict, state: SystemState) -> SystemState:
        # ── raw sensor fields ────────────────────────────────────────────────────
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
        state.step               = int(msg.get("step", state.step))
        state.episode            = int(msg.get("episode", state.episode))
        state.reward             = float(msg.get("reward", 0.0))
        state.is_success         = bool(msg.get("is_success", False))
        state.current_subtask    = msg.get("current_subtask", "")
        state.current_task       = msg.get("current_task", "")
        state.active_target_name = msg.get("active_target_name", "")
        state.obstacles          = msg.get("obstacles", {})
        state.objects            = msg.get("objects", {})
        state.scripts            = msg.get("scripts", {})
        state.target_goal        = msg.get("target_goal", {})
        state.scene              = msg.get("scene", {})
        state.robot_config       = msg.get("robot_config", {})
        state.obstacle_positions = msg.get("obstacle_positions", {})

        # ── ASM monitored parameters (mapeados a partir dos sensores) ────────────
        fw     = state.fingers_width
        dec    = state.dist_ee_to_cube
        cz     = float(state.cube_position[2])
        dct_xy = float(np.linalg.norm(state.cube_position[:2] - state.target_position[:2]))

        if self._initial_cube_z is None:
            self._initial_cube_z = cz

        if fw <= _GRIPPER_CLOSED_THRESHOLD:
            new_grasp = 1
        elif fw > _GRIPPER_OPEN_THRESHOLD:
            new_grasp = 0
        else:
            new_grasp = self._prev_grasp_completed

        state.object_available        = 1
        state.task_started            = 1
        state.gripper_width_cm        = int(fw     * 100)
        # state.distance_ee_object_cm   = int(dec * 100)  # distância ao centro do cubo (rollback)
        state.distance_ee_object_cm   = max(0, int((dec - _FINGER_LENGTH_M) * 100))  # distância ao ponto de grasp
        state.distance_object_goal_cm = int(dct_xy * 100)
        state.grasp_completed         = new_grasp
        state.finger_contacts         = int(msg.get("finger_contacts", 0))
        state.object_lift_height_cm   = max(0, int((cz - self._initial_cube_z) * 100))
        state.task_aborted            = int(state.current_task == "ABORT" and state.is_success)

        if state.grasp_completed == 1 and self._prev_grasp_completed == 0:
            self._grasp_attempts += 1
        self._prev_grasp_completed = state.grasp_completed
        state.grasp_attempts = self._grasp_attempts

        obj1 = state.objects.get("object_1", {})
        state.lateral_friction = float(obj1.get("lateral_friction", 0.0))

        return state
