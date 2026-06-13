import time

from panda_gym.envs.core import RobotTaskEnv

import api
from config_loader import load_config
# from manager_bridge import ManagerBridge  # TCP bridge (desativado)
from sensors import SensorPipeline
from setup_environment import setup_environment
from tasks.factory import create_api_task, create_hold, create_manual, create_pick_and_place, create_push, create_reach, create_scripted, create_terminal
from utils import build_perception_msg, SimHUD, StepLogger


def _make_task(strategy: str, sim, robot, configs):
    if strategy == "PUSH":           return create_push(sim, robot, configs)
    if strategy == "PICK_AND_PLACE": return create_pick_and_place(sim, robot, configs)
    if strategy == "REACH":          return create_reach(sim, robot, configs)
    if strategy == "HOLD":           return create_hold(sim, robot, configs)
    if strategy == "MANUAL":         return create_manual(sim, robot, configs)
    if strategy == "API_TASK":       return create_api_task(sim, robot, configs)
    if strategy.startswith("SCRIPTED_TASK."):
        script_name = strategy.split(".", 1)[1]
        return create_scripted(sim, robot, configs, script_name=script_name)
    return None


def main():
    configs = load_config()

    simulation, robot = setup_environment(configs)

    api.start()
    pipeline    = SensorPipeline(configs)
    # bridge    = ManagerBridge()  # TCP bridge (desativado)
    hud         = SimHUD(simulation.physics_client)
    logger      = StepLogger(hud=hud)
    # environment = RobotTaskEnv(robot, create_push(simulation, robot, configs))
    environment = RobotTaskEnv(robot, create_hold(simulation, robot, configs))
    # environment = RobotTaskEnv(robot, create_pick_and_place(simulation, robot, configs))

    for episode in range(configs["simulation"]["episodes"]):
        observation, info = environment.reset(seed=configs["simulation"]["seed"])

        for step in range(configs["simulation"]["max_steps"]):
            cmd = api.get_command()
            if cmd:
                new_task = _make_task(cmd["strategy"], simulation, robot, configs)
                if new_task:
                    new_task.reset()
                    environment.task = new_task
                    print(f"[Managing] Task trocada: {cmd['strategy']}")

            action = environment.task.compute_action()
            observation, reward, terminated, truncated, info = environment.step(action)

            perception = pipeline.sense(simulation, robot, environment, observation)

            perception_msg = build_perception_msg(
                episode + 1, step + 1, observation, reward, info, perception,
                robot=robot, sim=simulation,
                task=environment.task, action=action,
            )

            api.update_perception(perception_msg)
            # bridge.send_perception(perception_msg)  # TCP bridge (desativado)
            logger.log(perception_msg)

            time.sleep(configs["simulation"]["step_delay"])

            if terminated or truncated:
                break

    environment.close()


if __name__ == "__main__":
    main()
