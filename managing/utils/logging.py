import numpy as np


_LINE = "─" * 44


def log_step(episode: int, step: int, obs: dict, reward: float, info: dict,
             perception: dict, robot=None, sim=None, writer=None) -> None:
    text = _format_step(episode, step, obs, reward, info, perception, robot, sim)
    print(text)
    if writer is not None:
        writer.write(text)


def _format_step(episode: int, step: int, obs: dict, reward: float, info: dict,
                 perception: dict, robot=None, sim=None) -> str:
    o             = obs["observation"]
    ee_pos        = o[0:3]
    ee_vel        = o[3:6]
    fingers       = o[6]
    cube_pos      = o[7:10]
    target_pos    = obs["desired_goal"]
    dist_ee_cube  = float(np.linalg.norm(ee_pos - cube_pos))
    dist_cube_tgt = float(np.linalg.norm(cube_pos - target_pos))
    gripper_state = "ABERTA" if fingers > 0.02 else "FECHADA"

    lines = [
        _LINE,
        f" Ep {episode:>2} | Step {step:>3}",
        _LINE,
        f"  EE posição      : [{ee_pos[0]:+.3f}, {ee_pos[1]:+.3f}, {ee_pos[2]:+.3f}]",
        f"  EE velocidade   : [{ee_vel[0]:+.3f}, {ee_vel[1]:+.3f}, {ee_vel[2]:+.3f}]",
        f"  Garra           : {fingers:.3f} m  ({gripper_state})",
        f"  Cubo posição    : [{cube_pos[0]:+.3f}, {cube_pos[1]:+.3f}, {cube_pos[2]:+.3f}]",
        f"  Target          : [{target_pos[0]:+.3f}, {target_pos[1]:+.3f}, {target_pos[2]:+.3f}]",
        f"  Dist EE→Cubo    : {dist_ee_cube:.4f} m",
        f"  Dist Cubo→Target: {dist_cube_tgt:.4f} m",
        f"  Reward          : {reward:+.4f}",
        f"  Sucesso         : {info['is_success']}",
    ]

    obstacle_in_path = perception.get("obstacle_in_path", False)
    obstacle_count   = perception.get("obstacle_count_in_path", 0)
    lines.append(f"  Obstáculo caminho: {'SIM' if obstacle_in_path else 'nao'}  (count: {obstacle_count})")

    for name, data in perception.get("obstacles", {}).items():
        lines.append(f"  Obstáculo [{name}]: tipo={data.get('type')}  massa={data.get('mass')} kg  tamanho={data.get('size')}")

    for name, data in perception.get("objects", {}).items():
        lines.append(f"  Objeto [{name}]: tipo={data.get('type')}  massa={data.get('mass')} kg  tamanho={data.get('size')}")

    target_goal = perception.get("target_goal", {})
    if target_goal:
        lines.append(f"  Target goal     : {target_goal}")

    table = perception.get("scene", {}).get("table", {})
    if table:
        lines.append(f"  Mesa            : {table.get('length')}x{table.get('width')}x{table.get('height')} m  offset_x={table.get('x_offset')}")

    robot_cfg = perception.get("robot", {})
    if robot_cfg:
        lines.append(f"  Robô config     : control={robot_cfg.get('control_type')}  block_gripper={robot_cfg.get('block_gripper')}  base={robot_cfg.get('base_position')}")

    situations = perception.get("situations", {})
    if situations:
        lines.append(f"  Situações       : {list(situations.keys())}")

    adaptation_options = perception.get("adaptation_options", {})
    if adaptation_options:
        lines.append(f"  Adapt. options  : {adaptation_options}")

    scripts = perception.get("scripts", {})
    if scripts:
        lines.append(f"  Scripts         : {list(scripts.keys())}")

    if robot is not None:
        joint_angles = [robot.get_joint_angle(i)    for i in range(7)]
        joint_vels   = [robot.get_joint_velocity(i) for i in range(7)]
        lines.append(f"  Juntas ângulos  : [{', '.join(f'{a:+.2f}' for a in joint_angles)}]")
        lines.append(f"  Juntas veloc.   : [{', '.join(f'{v:+.2f}' for v in joint_vels)}]")

    if sim is not None:
        cube_rot     = sim.get_base_rotation("cube_1", type="euler")
        cube_lin_vel = sim.get_base_velocity("cube_1")
        lines.append(f"  Cubo rotação    : [{cube_rot[0]:+.3f}, {cube_rot[1]:+.3f}, {cube_rot[2]:+.3f}]  (roll/pitch/yaw)")
        lines.append(f"  Cubo vel.linear : [{cube_lin_vel[0]:+.3f}, {cube_lin_vel[1]:+.3f}, {cube_lin_vel[2]:+.3f}]")

    return "\n".join(lines)
