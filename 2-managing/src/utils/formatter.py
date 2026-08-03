_LINE = "─" * 44


def gripper_state(fingers: float, obj_size: float = 0.04) -> str:
    if fingers < 0.01:
        return "FECHADA"
    if fingers < obj_size * 1.2:
        return "AGARRADA"
    return "ABERTA"


def format_step(msg: dict) -> str:
    ee_pos     = msg["ee_position"]
    ee_vel     = msg["ee_velocity"]
    fingers    = msg["fingers_width"]
    cube_pos   = msg["cube_position"]
    target_pos = msg["target_position"]
    obj_size = next(iter(msg["objects"].values()))["size"][0] if msg.get("objects") else 0.04
    gripper_state_ = gripper_state(fingers, obj_size)

    lines = [
        _LINE,
        f" Ep {msg['episode']:>2} | Step {msg['step']:>3}",
        _LINE,
    ]

    if "current_task" in msg:
        lines.append(f"  Task            : {msg['current_task']}")

    if "action" in msg:
        a = msg["action"]
        lines.append(f"  Action          : [{a[0]:+.3f}, {a[1]:+.3f}, {a[2]:+.3f}, {a[3]:+.3f}]")

    lines += [
        f"  EE posição      : [{ee_pos[0]:+.3f}, {ee_pos[1]:+.3f}, {ee_pos[2]:+.3f}]",
        f"  EE velocidade   : [{ee_vel[0]:+.3f}, {ee_vel[1]:+.3f}, {ee_vel[2]:+.3f}]",
        f"  Garra           : {fingers:.3f} m  ({gripper_state_})  contatos={msg.get('finger_contacts', '?')}",
        f"  Cubo posição    : [{cube_pos[0]:+.3f}, {cube_pos[1]:+.3f}, {cube_pos[2]:+.3f}]",
        f"  Target ({msg.get('active_target_name', 'target')}): [{target_pos[0]:+.3f}, {target_pos[1]:+.3f}, {target_pos[2]:+.3f}]",
        f"  Dist EE→Cubo    : {msg['dist_ee_to_cube']:.4f} m",
        f"  Dist Cubo→{msg.get('active_target_name', 'target')}: {msg['dist_cube_to_target']:.4f} m",
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
