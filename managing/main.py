import sys
import time

sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
from panda_gym.envs.core import RobotTaskEnv

from config_loader import load_config
from manager_bridge import ManagerBridge
from sensors import SensorPipeline
from setup_environment import setup_environment
from tasks.factory import create_hold, create_manual, create_pick_and_place, create_push, create_reach, create_scripted, create_terminal
from utils import build_perception_msg, StepLogger


def _make_task(strategy: str, sim, robot, configs):
    """Instancia a task correspondente à estratégia recebida do manager."""
    if strategy == "PUSH":
        return create_push(sim, robot, configs)
    if strategy == "PICK_AND_PLACE_OVER":
        return create_pick_and_place(sim, robot, configs)
    if strategy.startswith("SCRIPTED."):
        script_name = strategy.split(".", 1)[1]
        return create_scripted(sim, robot, configs, script_name=script_name)
    return None


def main():
    configs = load_config()

    simulation, robot = setup_environment(configs)

    pipeline = SensorPipeline(configs)
    bridge   = ManagerBridge()
    logger = StepLogger()

    base_task = create_pick_and_place(simulation, robot, configs)
    # base_task = create_push(simulation, robot, configs)
    # base_task = create_manual(simulation, robot, configs)
    # base_task = create_hold(simulation, robot, configs)
    # base_task = create_reach(simulation, robot, configs)
    # base_task = create_scripted(simulation, robot, configs, script_name="left_right")
    # base_task = create_terminal(simulation, robot, configs)

    environment = RobotTaskEnv(robot, base_task)
    

    for episode in range(configs["simulation"]["episodes"]):
        observation, info = environment.reset(seed=configs["simulation"]["seed"])

        for step in range(configs["simulation"]["max_steps"]):
                # cmd = bridge.get_command()
                # if cmd:
                #     new_task = _make_task(cmd["strategy"], simulation, robot, configs)
                #     if new_task:
                #         current_task = new_task
                #         print(f"[Managing] Task trocada: {cmd['strategy']}")

                action = base_task.compute_action()
                observation, reward, terminated, truncated, info = environment.step(action)

                perception = pipeline.sense(simulation, robot, environment, observation)

                perception_msg = build_perception_msg(
                    episode + 1, step + 1, observation, reward, info, perception,
                    robot=robot, sim=simulation,
                )
                
                #bridge.send_perception(perception_msg)

                logger.log(perception_msg)

                time.sleep(configs["simulation"]["step_delay"])

                if terminated or truncated:
                    break

    environment.close()
    
if __name__ == "__main__":
    main()