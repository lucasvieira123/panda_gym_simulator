import numpy as np

_LINE = "─" * 44


def print_step(episode: int, step: int, obs: dict, reward: float, info: dict, task=None, robot=None, sim=None) -> None:
    o = obs["observation"]
    # obs layout: [ee_x, ee_y, ee_z, ee_vx, ee_vy, ee_vz, fingers_width, cube_x, cube_y, cube_z]
    ee_pos        = o[0:3]
    ee_vel        = o[3:6]
    fingers       = o[6]
    cube_pos      = o[7:10]
    target_pos    = obs["desired_goal"]
    dist_ee_cube  = float(np.linalg.norm(ee_pos - cube_pos))
    dist_cube_tgt = float(np.linalg.norm(cube_pos - target_pos))
    gripper_state = "ABERTA" if fingers > 0.02 else "FECHADA"

    task_name = type(task).__name__ if task is not None else "?"
    print(_LINE)
    print(f" {task_name} | Ep {episode:>2} | Step {step:>3}")
    print(_LINE)
    print(f"  EE posição      : [{ee_pos[0]:+.3f}, {ee_pos[1]:+.3f}, {ee_pos[2]:+.3f}]")
    print(f"  EE velocidade   : [{ee_vel[0]:+.3f}, {ee_vel[1]:+.3f}, {ee_vel[2]:+.3f}]")
    print(f"  Garra           : {fingers:.3f} m  ({gripper_state})")
    print(f"  Cubo posição    : [{cube_pos[0]:+.3f}, {cube_pos[1]:+.3f}, {cube_pos[2]:+.3f}]")
    print(f"  Target          : [{target_pos[0]:+.3f}, {target_pos[1]:+.3f}, {target_pos[2]:+.3f}]")
    print(f"  Dist EE→Cubo    : {dist_ee_cube:.4f} m")
    print(f"  Dist Cubo→Target: {dist_cube_tgt:.4f} m")
    print(f"  Reward          : {reward:+.4f}")
    print(f"  Sucesso         : {info['is_success']}")

    if robot is not None:
        joint_angles = [robot.get_joint_angle(i) for i in range(7)]
        joint_vels   = [robot.get_joint_velocity(i) for i in range(7)]
        angles_str   = ", ".join(f"{a:+.2f}" for a in joint_angles)
        vels_str     = ", ".join(f"{v:+.2f}" for v in joint_vels)
        print(f"  Juntas ângulos  : [{angles_str}]")
        print(f"  Juntas veloc.   : [{vels_str}]")

    if sim is not None:
        cube_rot     = sim.get_base_rotation("cube_1", type="euler")
        cube_lin_vel = sim.get_base_velocity("cube_1")
        print(f"  Cubo rotação    : [{cube_rot[0]:+.3f}, {cube_rot[1]:+.3f}, {cube_rot[2]:+.3f}]  (roll/pitch/yaw)")
        print(f"  Cubo vel.linear : [{cube_lin_vel[0]:+.3f}, {cube_lin_vel[1]:+.3f}, {cube_lin_vel[2]:+.3f}]")
