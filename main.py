import time

import numpy as np
from panda_gym.envs.core import RobotTaskEnv

from config_loader import load_config
from mapek import Knowledge, MapeKLoop
from start_simulation import start_simulation
from tasks import PushTask
from utils import print_mapek_step


def main():
    sim_cfg, env_cfg, target_goal_cfg, _ = load_config()

    sim_params = sim_cfg["simulation"]
    goal_position = np.array(target_goal_cfg["position"], dtype=np.float32)

    sim, robot = start_simulation(sim_cfg, env_cfg, target_goal_cfg)

    # task base apenas para o RobotTaskEnv calcular reward e is_success
    base_task = PushTask(
        sim=sim,
        get_ee_position=robot.get_ee_position,
        get_object_position=lambda: sim.get_base_position("cube_1"),
        goal_position=goal_position,
    )
    env = RobotTaskEnv(robot, base_task)

    obstacle_names = [o["name"] for o in env_cfg.get("obstacles", [])]
    knowledge = Knowledge(obstacle_names=obstacle_names)
    mape_k = MapeKLoop(sim, robot, goal_position, knowledge)

    for episode in range(sim_params["episodes"]):
        obs, info = env.reset(seed=sim_params["seed"])
        mape_k.reset()

        for step in range(sim_params["max_steps"]):
            action = mape_k.step(obs)
            obs, reward, terminated, truncated, info = env.step(action)

            if sim_params["verbose"]:
                print_mapek_step(episode + 1, step + 1, obs, reward, info,
                                 mapek_state=mape_k.state, robot=robot, sim=sim)

            time.sleep(sim_params["step_delay"])

            if terminated or truncated:
                break

    env.close()


if __name__ == "__main__":
    main()
