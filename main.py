import time

import time

import numpy as np
from panda_gym.envs.core import RobotTaskEnv

from config_loader import load_config
from mapek import Knowledge, MapeKLoop
from mapek.knowledge import Situation, Strategy
from setup_environment import setup_environment
from tasks import create_pick_and_place
from tasks.factory import create_hold, create_manual, create_push, create_reach, create_scripted
from tasks.scripted_task import ScriptedTask
from utils import TkOverlay, print_mapek_step


def main():
    configs = load_config()

    simulation, robot = setup_environment(configs)

    base_task = create_pick_and_place(simulation, robot, configs)  # NAO MUDAR
    # base_task = create_push(simulation, robot, configs)  
    # base_task = create_manual(simulation, robot, configs)
    # base_task = create_hold(simulation, robot, configs)
    # base_task = create_reach(simulation, robot, configs)
    base_task = create_scripted(simulation, robot, configs, script_name="left_right") # tem que passar o script_name definido em scripts.yaml

    environment = RobotTaskEnv(robot, base_task)

    sim_cfg = configs["simulation"]
    for episode in range(sim_cfg["episodes"]):
        observation, info = environment.reset(seed=sim_cfg["seed"])

        for step in range(sim_cfg["max_steps"]):
            action = base_task.compute_action()
            observation, reward, terminated, truncated, info = environment.step(action)

            print(f"Ep {episode+1} | Step {step+1} | reward: {reward:+.4f} | success: {info['is_success']}")

            time.sleep(sim_cfg["step_delay"])

            if terminated or truncated:
                break

    environment.close()

    

    # obstacle_names = [o["name"] for o in configs["environment"].get("obstacles", [])]
    # situation_strategy_map = {
    #     Situation(k): Strategy(v)
    #     for k, v in configs["adaptation_options"].items()
    # }
    # knowledge = Knowledge(
    #     obstacle_names=obstacle_names,
    #     scripts=configs["scripts"],
    #     situations=configs["situations"],
    #     situation_strategy_map=situation_strategy_map or None,
    # )
    # mape_k = MapeKLoop(simulation, robot, configs["target_goal"], knowledge)

    # obstacle_meta = {o["name"]: o for o in configs["environment"].get("obstacles", [])}
    # overlay = TkOverlay(obstacle_meta=obstacle_meta)
#     try:
#         start_simulation_loop(environment, mape_k, configs, robot, simulation, overlay, obstacle_meta)
#     finally:
#         overlay.close()
#         environment.close()


# def start_simulation_loop(env, mape_k, configs, robot, simulation, overlay: TkOverlay, obstacle_meta: dict) -> None:
#     sim_cfg = configs["simulation"]
#     for episode in range(sim_cfg["episodes"]):
#         observation, info = env.reset(seed=sim_cfg["seed"])
#         mape_k.reset()

#         for step in range(sim_cfg["max_steps"]):
#             action = mape_k.step(observation)
#             observation, reward, terminated, truncated, info = env.step(action)

#             overlay.render(episode + 1, step + 1, observation, reward, info,
#                            robot=robot, sim=simulation, mapek_state=mape_k.state, action=action)

#             if sim_cfg["verbose"]:
#                 print_mapek_step(episode + 1, step + 1, observation, reward, info,
#                                  mapek_state=mape_k.state, obstacle_meta=obstacle_meta,
#                                  action=action)

#             time.sleep(sim_cfg["step_delay"])

#             if terminated or truncated:
#                 break

if __name__ == "__main__":
    main()