import argparse
import time

from panda_gym.envs.core import RobotTaskEnv

import api
from config_loader import load_config
# from manager_bridge import ManagerBridge  # TCP bridge (desativado)
from sensors import SensorPipeline
from environment_manager import EnvironmentManager
from tasks.factory import (
    create_api_task, create_hold, create_manual, create_object_delivery,
    create_pick_and_place, create_push, create_reach, create_retry_grasp,
    create_safe_abort, create_scripted, create_terminal,
)
from utils import build_perception_msg, SimHUD, StepLogger, ts, set_step



def _make_task(strategy: str, sim, robot, configs):
    if strategy == "PUSH":              return create_push(sim, robot, configs)
    if strategy == "PICK_AND_PLACE":    return create_pick_and_place(sim, robot, configs)
    if strategy == "REACH":             return create_reach(sim, robot, configs)
    if strategy == "HOLD":              return create_hold(sim, robot, configs)
    if strategy == "MANUAL":            return create_manual(sim, robot, configs)
    if strategy == "API_TASK":          return create_api_task(sim, robot, configs)
    if strategy == "OBJECT_DELIVERY":   return create_object_delivery(sim, robot, configs)
    if strategy == "RETRY_GRASP":       return create_retry_grasp(sim, robot, configs)
    if strategy == "SAFE_ABORT":        return create_safe_abort(sim, robot, configs)
    if strategy.startswith("SCRIPTED_TASK."):
        script_name = strategy.split(".", 1)[1]
        return create_scripted(sim, robot, configs, script_name=script_name)
    return None


def _handle_command(cmd: dict | None, gym_env, sequence, sim, robot, configs) -> None:
    """Handles manager checkpoint response. Managing knows nothing about ASM."""
    if cmd is None:
        return  # timeout — graceful degradation, continues normally

    action = cmd.get("action", "continue")

    if action == "continue":
        pass  # managing follows its own sequence flow

    elif action == "adapt":
        scenario = cmd.get("to", "")
        adaptive_task = _make_task(scenario, sim, robot, configs)
        if adaptive_task:
            adaptive_task.reset()
            gym_env.task = adaptive_task
            print(f"[{ts()}][Managing] Adaptação iniciada: {scenario}")
        else:
            print(f"[{ts()}][Managing] Adaptação desconhecida: '{scenario}' — ignorada")

    elif action == "transition":
        state_name = cmd.get("to", "")
        if hasattr(sequence, "force_state"):
            sequence.force_state(state_name)
        gym_env.task = sequence  # restaura sequência como task activa
        print(f"[{ts()}][Managing] Sequência retomada em: {state_name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config-dir", default=None)
    args = parser.parse_args()

    configs = load_config(config_dir=args.config_dir)

    api.start()  # uvicorn pronto antes do PyBullet carregar — manager conecta durante o loading

    env        = EnvironmentManager(configs)
    simulation = env.sim
    robot      = env.robot

    api.update_obstacles(env.get_obstacles())
    api.update_objects(env.get_objects())

    pipeline    = SensorPipeline(configs, env, sim=simulation)
    # bridge    = ManagerBridge()  # TCP bridge (desativado)
    hud         = SimHUD(simulation.physics_client)
    traces_dir  = configs["simulation"].get("traces_dir")
    logger      = StepLogger(traces_dir=traces_dir, hud=hud)
    # gym_env = RobotTaskEnv(robot, create_push(simulation, robot, configs))
    # gym_env = RobotTaskEnv(robot, create_hold(simulation, robot, configs))
    # gym_env = RobotTaskEnv(robot, create_pick_and_place(simulation, robot, configs))
    sequence  = create_object_delivery(simulation, robot, configs)
    gym_env   = RobotTaskEnv(robot, sequence)

    current_goal_mode: str | None = None

    api.wait_for_client()

    for episode in range(configs["simulation"]["episodes"]):
        observation, info = gym_env.reset(seed=configs["simulation"]["seed"])

        for step in range(configs["simulation"]["max_steps"]):
            set_step(step + 1)
            env_cmd = api.get_environment_changes()
            if env_cmd:
                env.apply_environment_command(env_cmd)
                api.update_obstacles(env.get_obstacles())
                api.update_objects(env.get_objects())

            goal_cmd = api.get_goal_changes()
            if goal_cmd:
                if goal_cmd.get("action") == "set_goal_mode":
                    current_goal_mode = goal_cmd["mode"]
                    gym_env.task.set_goal_mode(current_goal_mode)
                else:
                    env.apply_goal_command(goal_cmd)
                    gym_env.task.refresh_goal()

            action = gym_env.task.compute_action()
            observation, reward, terminated, truncated, info = gym_env.step(action)
            env.refresh_object_labels()

            perception = pipeline.sense(simulation, robot, gym_env, observation)

            perception_msg = build_perception_msg(
                episode + 1, step + 1, observation, reward, info, perception,
                robot=robot, sim=simulation,
                task=gym_env.task, action=action,
            )

            api.update_perception(perception_msg)
            # bridge.send_perception(perception_msg)  # TCP bridge (desativado)
            logger.log(perception_msg)

            # ── checkpoint: bloqueia até manager responder ────────────────────
            cmd = api.wait_for_command(timeout=5.0)
            _handle_command(cmd, gym_env, sequence, simulation, robot, configs)
            # ─────────────────────────────────────────────────────────────────

            time.sleep(configs["simulation"]["step_delay"])

            if terminated or truncated:
                break

    gym_env.close()


if __name__ == "__main__":
    main()
