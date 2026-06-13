import numpy as np

from .trace import TraceWriter

_LINE = "─" * 44


class StepLogger:
    """Imprime e grava cada step no trace.

        logger = StepLogger()
        logger.log(perception_msg)

    O arquivo de trace é fechado automaticamente ao fim do processo.
    """

    def __init__(self, traces_dir: str = None) -> None:
        import atexit
        self._writer = TraceWriter(traces_dir) if traces_dir else TraceWriter()
        atexit.register(self._writer.close)

    def log(self, msg: dict) -> None:
        log_step(msg, writer=self._writer)


def build_perception_msg(episode: int, step: int, obs: dict, reward: float,
                         info: dict, perception: dict, robot=None, sim=None) -> dict:
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
        "reward":                 float(reward),
        "is_success":             bool(info.get("is_success", False)),
        "obstacle_in_path":       bool(perception.get("obstacle_in_path", False)),
        "obstacle_count_in_path": int(perception.get("obstacle_count_in_path", 0)),
        "obstacles":              perception.get("obstacles", {}),
        "objects":                perception.get("objects", {}),
        "situations":             perception.get("situations", {}),
        "adaptation_options":     perception.get("adaptation_options", {}),
        "scripts":                {k: True for k in perception.get("scripts", {})},
        "target_goal":            perception.get("target_goal", {}),
        "scene":                  perception.get("scene", {}),
        "robot_config":           perception.get("robot", {}),
    }

    if robot is not None:
        msg["joint_angles"]     = [float(robot.get_joint_angle(i))    for i in range(7)]
        msg["joint_velocities"] = [float(robot.get_joint_velocity(i)) for i in range(7)]

    if sim is not None:
        msg["cube_rotation"]        = [float(x) for x in sim.get_base_rotation("cube_1", type="euler")]
        msg["cube_linear_velocity"] = [float(x) for x in sim.get_base_velocity("cube_1")]
        msg["obstacle_positions"]   = {
            name: [float(x) for x in sim.get_base_position(name)]
            for name in perception.get("obstacles", {})
        }

    return msg


def log_step(msg: dict, writer=None) -> None:
    text = _format_step(msg)
    print(text)
    if writer is not None:
        writer.write(text)


def _format_step(msg: dict) -> str:
    ee_pos      = msg["ee_position"]
    ee_vel      = msg["ee_velocity"]
    fingers     = msg["fingers_width"]
    cube_pos    = msg["cube_position"]
    target_pos  = msg["target_position"]
    gripper_state = "ABERTA" if fingers > 0.02 else "FECHADA"

    lines = [
        _LINE,
        f" Ep {msg['episode']:>2} | Step {msg['step']:>3}",
        _LINE,
        f"  EE posição      : [{ee_pos[0]:+.3f}, {ee_pos[1]:+.3f}, {ee_pos[2]:+.3f}]",
        f"  EE velocidade   : [{ee_vel[0]:+.3f}, {ee_vel[1]:+.3f}, {ee_vel[2]:+.3f}]",
        f"  Garra           : {fingers:.3f} m  ({gripper_state})",
        f"  Cubo posição    : [{cube_pos[0]:+.3f}, {cube_pos[1]:+.3f}, {cube_pos[2]:+.3f}]",
        f"  Target          : [{target_pos[0]:+.3f}, {target_pos[1]:+.3f}, {target_pos[2]:+.3f}]",
        f"  Dist EE→Cubo    : {msg['dist_ee_to_cube']:.4f} m",
        f"  Dist Cubo→Target: {msg['dist_cube_to_target']:.4f} m",
        f"  Reward          : {msg['reward']:+.4f}",
        f"  Sucesso         : {msg['is_success']}",
    ]

    lines.append(f"  Obstáculo caminho: {'SIM' if msg['obstacle_in_path'] else 'nao'}  (count: {msg['obstacle_count_in_path']})")

    for name, data in msg.get("obstacles", {}).items():
        lines.append(f"  Obstáculo [{name}]: tipo={data.get('type')}  massa={data.get('mass')} kg  tamanho={data.get('size')}")

    for name, data in msg.get("objects", {}).items():
        lines.append(f"  Objeto [{name}]: tipo={data.get('type')}  massa={data.get('mass')} kg  tamanho={data.get('size')}")

    if msg.get("target_goal"):
        lines.append(f"  Target goal     : {msg['target_goal']}")

    table = msg.get("scene", {}).get("table", {})
    if table:
        lines.append(f"  Mesa            : {table.get('length')}x{table.get('width')}x{table.get('height')} m  offset_x={table.get('x_offset')}")

    if msg.get("robot_config"):
        rc = msg["robot_config"]
        lines.append(f"  Robô config     : control={rc.get('control_type')}  block_gripper={rc.get('block_gripper')}  base={rc.get('base_position')}")

    if msg.get("situations"):
        lines.append(f"  Situações       : {list(msg['situations'].keys())}")

    if msg.get("adaptation_options"):
        lines.append(f"  Adapt. options  : {msg['adaptation_options']}")

    if msg.get("scripts"):
        lines.append(f"  Scripts         : {list(msg['scripts'].keys())}")

    if "joint_angles" in msg:
        lines.append(f"  Juntas ângulos  : [{', '.join(f'{a:+.2f}' for a in msg['joint_angles'])}]")
        lines.append(f"  Juntas veloc.   : [{', '.join(f'{v:+.2f}' for v in msg['joint_velocities'])}]")

    if "cube_rotation" in msg:
        cr  = msg["cube_rotation"]
        clv = msg["cube_linear_velocity"]
        lines.append(f"  Cubo rotação    : [{cr[0]:+.3f}, {cr[1]:+.3f}, {cr[2]:+.3f}]  (roll/pitch/yaw)")
        lines.append(f"  Cubo vel.linear : [{clv[0]:+.3f}, {clv[1]:+.3f}, {clv[2]:+.3f}]")

    return "\n".join(lines)
