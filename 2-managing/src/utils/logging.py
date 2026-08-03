import re
import numpy as np

from .formatter import format_step
from .trace import TraceWriter


def _task_label(task) -> str:
    script = getattr(task, "script_name", "")
    if script:
        return f"SCRIPTED_TASK.{script}"
    name = type(task).__name__.replace("Task", "")
    return re.sub(r'(?<=[a-z])(?=[A-Z])', '_', name).upper()


class StepLogger:
    """Imprime no terminal, grava no trace e atualiza o HUD (se fornecido).

        logger = StepLogger(hud=hud)
        logger.log(perception_msg)

    O arquivo de trace é fechado automaticamente ao fim do processo.
    """

    def __init__(self, traces_dir: str = None, hud=None) -> None:
        import atexit
        self._writer = TraceWriter(traces_dir) if traces_dir else TraceWriter()
        self._hud    = hud
        atexit.register(self._writer.close)

    def log(self, msg: dict) -> None:
        log_step(msg, writer=self._writer)
        if self._hud is not None:
            self._hud.render(msg)


def build_perception_msg(episode: int, step: int, obs: dict, reward: float,
                         info: dict, perception: dict, robot=None, sim=None,
                         task=None, action=None) -> dict:
    o          = obs["observation"]
    ee_pos     = o[0:3]
    ee_vel     = o[3:6]
    fingers    = float(o[6])
    cube_pos   = o[7:10]
    target_pos = obs["desired_goal"]

    msg = {
        "episode":                episode,
        "step":                   step,
        "ee_position":            [float(x) for x in ee_pos],
        "ee_velocity":            [float(x) for x in ee_vel],
        "fingers_width":          fingers,
        "cube_position":          [float(x) for x in cube_pos],
        "target_position":        [float(x) for x in target_pos],
        "dist_ee_to_cube":        float(np.linalg.norm(ee_pos - cube_pos)),
        "dist_cube_to_target":    float(np.linalg.norm(cube_pos - target_pos)),
        "finger_contacts":        int(perception.get("finger_contacts", 0)),
        "reward":                 float(reward),
        "is_success":             bool(info.get("is_success", False)),
        "obstacle_in_path":       bool(perception.get("obstacle_in_path", False)),
        "obstacle_count_in_path": int(perception.get("obstacle_count_in_path", 0)),
        "obstacles":              perception.get("obstacles", {}),
        "objects":                perception.get("objects", {}),
        "scripts":                {k: True for k in perception.get("scripts", {})},
        "target_goal":            perception.get("target_goal", {}),
        "scene":                  perception.get("scene", {}),
        "robot_config":           perception.get("robot", {}),
    }

    if task is not None:
        msg["current_task"] = _task_label(task)
        if hasattr(task, "current_subtask"):
            msg["current_subtask"] = task.current_subtask
        if hasattr(task, "active_goal_name"):
            msg["active_target_name"] = task.active_goal_name()
        if hasattr(task, "_goal_mode") and "target_goal" in msg:
            msg["target_goal"] = {**msg["target_goal"], "mode": "goal_" + task._goal_mode}

    if action is not None:
        msg["action"] = [float(x) for x in action]

    if robot is not None:
        msg["joint_angles"]     = [float(robot.get_joint_angle(i))    for i in range(7)]
        msg["joint_velocities"] = [float(robot.get_joint_velocity(i)) for i in range(7)]

    if sim is not None:
        msg["cube_rotation"]        = [float(x) for x in sim.get_base_rotation("object_1", type="euler")]
        msg["cube_linear_velocity"] = [float(x) for x in sim.get_base_velocity("object_1")]
        msg["obstacle_positions"]   = {
            name: [float(x) for x in sim.get_base_position(name)]
            for name in perception.get("obstacles", {})
            if name in sim._bodies_idx
        }

    return msg


def log_step(msg: dict, writer=None) -> None:
    text = format_step(msg)
    print(text)
    if writer is not None:
        writer.write(text)
