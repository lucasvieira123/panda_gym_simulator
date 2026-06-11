import time

import numpy as np
from panda_gym.envs.core import RobotTaskEnv

from config_loader import load_config
from start_simulation import start_simulation
from tasks import ManualTask, PickAndPlaceTask, PushTask, ReachTask


def main():
    sim_cfg, env_cfg, target_goal_cfg = load_config()

    sim_params = sim_cfg["simulation"]
    goal_position = np.array(target_goal_cfg["position"], dtype=np.float32)

    sim, robot = start_simulation(sim_cfg, env_cfg, target_goal_cfg)

    # task = ReachTask(
    #     sim=sim,
    #     get_ee_position=robot.get_ee_position,
    #     goal_position=goal_position,
    # )

    # task = PushTask(
    #     sim=sim,
    #     get_ee_position=robot.get_ee_position,
    #     get_object_position=lambda: sim.get_base_position("cube_1"),
    #     goal_position=goal_position,
    # )

    # Controles: setas=X/Y | Q/E=Z | ESPAÇO=abrir/fechar garra
    task = ManualTask(
        sim=sim,
        get_ee_position=robot.get_ee_position,
        get_object_position=lambda: sim.get_base_position("cube_1"),
        goal_position=goal_position,
    )

    # task = PickAndPlaceTask(
    #     sim=sim,
    #     get_ee_position=robot.get_ee_position,
    #     get_object_position=lambda: sim.get_base_position("cube_1"),
    #     goal_position=goal_position,
    # )

    env = RobotTaskEnv(robot, task)

    for episode in range(sim_params["episodes"]):
        obs, info = env.reset(seed=sim_params["seed"])

        for step in range(sim_params["max_steps"]):
            action = task.compute_action()
            obs, reward, terminated, truncated, info = env.step(action)

            if sim_params["verbose"]:
                print(f"Episode {episode + 1} | Step {step + 1} | reward={reward:.3f} | success={info['is_success']}")

            time.sleep(sim_params["step_delay"])

            if terminated or truncated:
                break

    env.close()


if __name__ == "__main__":
    main()
