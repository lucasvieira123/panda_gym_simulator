import argparse
import re
import time

import numpy as np

from panda_gym.envs.core import RobotTaskEnv

import api
from config_loader import load_config
# from manager_bridge import ManagerBridge  # TCP bridge (desativado)
from sensors import SensorPipeline
from environment_manager import EnvironmentManager
from tasks.factory import (
    create_api_task, create_hold, create_manual, create_object_delivery,
    create_pick_and_place, create_push, create_reach, create_retry_grasp,
    create_safe_abort, create_scripted, create_terminal, create_vacuum_assist,
    create_heavy_lift, create_adjust_grip_force, create_increase_grip_pressure,
)
from utils import build_perception_msg, SimHUD, StepLogger, VideoRecorder, ts, set_step
from utils.physical_outcome import physical_outcome

_FAIL_SAFE_HOLD_TICKS = 10  # mantém a pose parada por estes ticks antes de encerrar o run



def _make_task(strategy: str, sim, robot, configs):
    if strategy == "PUSH":              return create_push(sim, robot, configs)
    if strategy == "PICK_AND_PLACE":    return create_pick_and_place(sim, robot, configs)
    if strategy == "REACH":             return create_reach(sim, robot, configs)
    if strategy == "HOLD":              return create_hold(sim, robot, configs)
    if strategy == "MANUAL":            return create_manual(sim, robot, configs)
    if strategy == "API_TASK":          return create_api_task(sim, robot, configs)
    if strategy == "OBJECT_DELIVERY":   return create_object_delivery(sim, robot, configs)
    if strategy == "RETRY_GRASP":          return create_retry_grasp(sim, robot, configs)
    if strategy == "SAFE_ABORT":           return create_safe_abort(sim, robot, configs)
    if strategy == "APPLY_VACUUM_ASSIST":      return create_vacuum_assist(sim, robot, configs)
    if strategy == "ADJUST_GRIP_FORCE":        return create_adjust_grip_force(sim, robot, configs)
    if strategy == "INCREASE_GRIP_PRESSURE":   return create_increase_grip_pressure(sim, robot, configs)
    if strategy == "HEAVY_LIFT":               return create_heavy_lift(sim, robot, configs)
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
        # Se uma task adaptativa terminou, restaura a sequência no estado indicado pela task
        if gym_env.task is not sequence and getattr(gym_env.task, "done", False):
            return_to = getattr(gym_env.task, "return_to", None)
            if return_to:
                sequence.force_state(return_to)
                gym_env.task = sequence
                print(f"[{ts()}][Managing] Task adaptativa concluída → retomando {return_to}")

    elif action == "adapt":
        scenario = cmd.get("to", "").replace("()", "").upper().strip()
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


def _run_fail_safe(reason, gym_env, sim, robot, pipeline, logger, configs, episode, step) -> None:
    """Interrompe o braço e a garra na pose atual e registra o motivo. Não abre a garra."""
    print(f"[{ts()}][Managing] FAIL-SAFE acionado: {reason}. Movimentos interrompidos; operador notificado.")
    frozen = np.array([robot.get_joint_angle(joint) for joint in robot.joint_indices])
    for tick in range(1, _FAIL_SAFE_HOLD_TICKS + 1):
        robot.control_joints(frozen)
        sim.step()
        observation = gym_env._get_obs()
        msg = build_perception_msg(
            episode, step + tick, observation, 0.0, {"is_success": False}, pipeline.sense(sim, robot, gym_env, observation),
            robot=robot, sim=sim, task=gym_env.task, action=np.zeros(4),
        )
        msg["current_task"] = "FAIL_SAFE"
        msg["physical_outcome"] = physical_outcome(msg, configs["simulation"]["distance_threshold"])
        logger.log(msg)
    logger.log_episode_end(episode, step + _FAIL_SAFE_HOLD_TICKS, "fail_safe", reason)


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

    # Grava a janela tal como aparece na tela, a partir do início da simulação
    video = VideoRecorder(
        simulation.physics_client,
        re.sub(r"trace_(.+)\.log$", r"video_\1.mp4", logger.trace_path),
        configs["simulation"].get("record_video", False),
        configs["simulation"]["render_mode"],
    )
    try:
        for episode in range(configs["simulation"]["episodes"]):
            observation, info = gym_env.reset(seed=configs["simulation"]["seed"])
            episode_end = "max_steps"

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
                perception_msg["physical_outcome"] = physical_outcome(
                    perception_msg, configs["simulation"]["distance_threshold"]
                )

                api.update_perception(perception_msg)
                # bridge.send_perception(perception_msg)  # TCP bridge (desativado)
                logger.log(perception_msg)

                # ── checkpoint: bloqueia até manager responder ────────────────────
                cmd = api.wait_for_command(timeout=5.0)
                if cmd and cmd.get("action") == "fail_safe":
                    _run_fail_safe(cmd.get("reason"), gym_env, simulation, robot, pipeline, logger, configs, episode + 1, step + 1)
                    return
                _handle_command(cmd, gym_env, sequence, simulation, robot, configs)

                # ── ROLLBACK ──────────────────────────────────────────────────────
                # Comportamento original: a transição acontecia dentro de
                # compute_action() — apaga as 2 linhas abaixo para reverter.
                if gym_env.task is sequence:
                    sequence.advance_if_done()
                # ──────────────────────────────────────────────────────────────────

                time.sleep(configs["simulation"]["step_delay"])

                if terminated or truncated:
                    episode_end = "terminated" if terminated else "truncated"
                    break

            logger.log_episode_end(episode + 1, step + 1, episode_end)
    finally:
        video.stop()  # antes de fechar a janela, para o ffmpeg fechar o arquivo
        gym_env.close()


if __name__ == "__main__":
    main()
