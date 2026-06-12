import time

import numpy as np
from panda_gym.envs.core import RobotTaskEnv

from config_loader import load_config
from mapek import Knowledge, MapeKLoop
from setup_environment import setup_environment
from tasks import PushTask
from tasks.pick_and_place_task import PickAndPlaceTask
from utils import DebugOverlay, print_mapek_step


def main():
    sim_cfg, env_cfg, target_goal_cfg, _ = load_config()

    sim_params = sim_cfg["simulation"]
    goal_position = np.array(target_goal_cfg["position"], dtype=np.float32)

    sim, robot = setup_environment(sim_cfg, env_cfg, target_goal_cfg)

    # task base apenas para calcular reward e is_success, mas nao é ele que define a acao. Para o sistema autoadaptativo, o foco é levar o bloco para o target, entao esse task base é o mais adequado.
    base_task = PickAndPlaceTask( # NAO MUDAR
        sim=sim,
        get_ee_position=robot.get_ee_position,
        get_object_position=lambda: sim.get_base_position("cube_1"),
        goal_position=goal_position,
    )

    env = RobotTaskEnv(robot, base_task)

    obstacle_names = [o["name"] for o in env_cfg.get("obstacles", [])]
    knowledge = Knowledge(obstacle_names=obstacle_names)
    mape_k = MapeKLoop(sim, robot, goal_position, knowledge)

    overlay = DebugOverlay(sim.physics_client)
    start_simulation_loop(env, mape_k, sim_params, robot, sim, overlay)

    env.close()


def start_simulation_loop(env, mape_k, sim_params, robot, sim, overlay: DebugOverlay) -> None:
    for episode in range(sim_params["episodes"]):
        observation, info = env.reset(seed=sim_params["seed"])
        mape_k.reset()

        for step in range(sim_params["max_steps"]):
            action = mape_k.step(observation)
            observation, reward, terminated, truncated, info = env.step(action)

            overlay.render(episode + 1, step + 1, observation, reward, info, robot=robot, sim=sim)

            if sim_params["verbose"]:
                print_mapek_step(episode + 1, step + 1, observation, reward, info,
                                 mapek_state=mape_k.state, robot=robot, sim=sim)

            time.sleep(sim_params["step_delay"])

            if terminated or truncated:
                break

if __name__ == "__main__":
    main()
