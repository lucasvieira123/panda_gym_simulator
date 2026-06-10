from __future__ import annotations

from typing import Any, Dict

import numpy as np

import time
from pathlib import Path
import yaml

from .env_factory import make_configurable_env
from .logger import ExperimentLogger
from .policies import SimplePolicy


class ExperimentRunner:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

        self.experiment_config = config.get("experiment", {})
        self.policy_config = config.get("policy", {})
        self.logging_config = config.get("logging", {})

        self.simulation_config = config.get("simulation", {})
        self.step_delay = float(self.simulation_config.get("step_delay", 1.0))

        # NOVO: configuração de runtime
        self.runtime_config = config.get("runtime", {})

        # NOVO: guarda quais comandos já foram aplicados
        self.applied_runtime_commands = set()

        # NOVO: arquivo que o usuário poderá editar enquanto a simulação roda
        command_file = self.runtime_config.get("command_file")

        if command_file:
            config_dir = Path(config.get("_config_dir", "."))
            self.command_file = config_dir / command_file
        else:
            self.command_file = None

        # NOVO: frequência com que o runner vai olhar o arquivo de comandos
        self.poll_every_steps = int(self.runtime_config.get("poll_every_steps", 1))

        self.env = make_configurable_env(config)

        self.policy = SimplePolicy(
            name=self.policy_config.get("name", "random"),
            gain=float(self.policy_config.get("gain", 5.0)),
        )

        self.logger = ExperimentLogger(
            output_dir=self.logging_config.get(
                "output_dir",
                f"results/{self.experiment_config.get('name', 'experiment')}",
            )
        )

    def run(self) -> Dict[str, Any]:
        seed = int(self.experiment_config.get("seed", 42))
        episodes = int(self.experiment_config.get("episodes", 1))
        max_steps = int(self.experiment_config.get("max_steps", 100))

        print(f"[PandaConfigurableLab] Experimento: {self.experiment_config.get('name')}")
        print(f"[PandaConfigurableLab] Episódios: {episodes}")
        print(f"[PandaConfigurableLab] Max steps: {max_steps}")
        print(f"[PandaConfigurableLab] Política: {self.policy.name}")

        for episode in range(episodes):
            self._run_episode(episode=episode, seed=seed + episode, max_steps=max_steps)

        self.logger.flush()
        self.env.close()

        output_dir = self.logger.output_dir.as_posix()

        print(f"[PandaConfigurableLab] Finalizado. Resultados em: {output_dir}")

        return {
            "episodes": episodes,
            "output_dir": output_dir,
        }

    def _run_episode(self, episode: int, seed: int, max_steps: int) -> None:
        observation, info = self.env.reset(seed=seed)

        final_reward = None
        final_success = False
        final_distance = None
        steps_executed = 0

        for step in range(max_steps):
            self._apply_runtime_commands(episode, step)

            # Garante que a política vê o desired_goal atualizado no mesmo step
            # em que o comando foi aplicado (sem esperar o próximo env.step)
            observation = self._refresh_desired_goal(observation)

            action = self.policy.act(self.env, observation)

            next_observation, reward, terminated, truncated, info = self.env.step(action)
            
            if self.step_delay > 0:
                time.sleep(self.step_delay)

            achieved = next_observation.get("achieved_goal")
            desired = next_observation.get("desired_goal")
            distance_to_goal = self._distance(achieved, desired)

            record = {
                "episode": episode,
                "step": step,
                "action": action,
                "reward": float(reward),
                "terminated": bool(terminated),
                "truncated": bool(truncated),
                "achieved_goal": achieved,
                "desired_goal": desired,
                "distance_to_goal": distance_to_goal,
                "is_success": bool(info.get("is_success", False)) if isinstance(info, dict) else False,
                "observation": next_observation.get("observation") if isinstance(next_observation, dict) else next_observation,
                "info": info,
            }

            self.logger.log_step(record)

            final_reward = float(reward)
            final_success = bool(info.get("is_success", False)) if isinstance(info, dict) else False
            final_distance = distance_to_goal
            steps_executed = step + 1

            observation = next_observation

            if terminated or truncated:
                break

        summary = {
            "episode": episode,
            "seed": seed,
            "steps": steps_executed,
            "final_reward": final_reward,
            "final_success": final_success,
            "final_distance_to_goal": final_distance,
        }

        self.logger.add_summary(summary)

        print(
            f"[PandaConfigurableLab] Episódio {episode}: "
            f"steps={steps_executed}, "
            f"reward={final_reward}, "
            f"success={final_success}, "
            f"distance={final_distance}"
        )

    def _refresh_desired_goal(self, observation: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualiza desired_goal na observation com o valor atual de task.goal.

        Necessário porque observation vem do env.step() anterior — sem isso,
        a política só veria o novo goal no step seguinte ao comando.
        """
        if not isinstance(observation, dict):
            return observation

        task = getattr(self.env, "task", None)
        if task is None:
            task = getattr(getattr(self.env, "unwrapped", None), "task", None)
        if task is None:
            return observation

        new_goal = task.get_goal()
        if np.array_equal(observation.get("desired_goal"), new_goal):
            return observation  # nada mudou, evita cópia desnecessária

        return {**observation, "desired_goal": new_goal}

    @staticmethod
    def _distance(achieved: Any, desired: Any) -> float | None:
        if achieved is None or desired is None:
            return None

        achieved_arr = np.asarray(achieved, dtype=float)
        desired_arr = np.asarray(desired, dtype=float)

        if achieved_arr.shape != desired_arr.shape:
            return None

        return float(np.linalg.norm(achieved_arr - desired_arr))
    
    def _apply_runtime_commands(self, episode: int, step: int) -> None:
        """
        Lê comandos de runtime a partir de um YAML externo.

        O usuário pode editar esse arquivo enquanto a simulação está rodando.
        """
        if self.command_file is None:
            return

        if step % self.poll_every_steps != 0:
            return

        if not self.command_file.exists():
            return

        try:
            with self.command_file.open("r", encoding="utf-8") as file:
                data = yaml.safe_load(file) or {}
        except Exception as exc:
            self.logger.log_event(
                {
                    "episode": episode,
                    "step": step,
                    "operation": "read_runtime_commands",
                    "status": "failed",
                    "message": str(exc),
                }
            )
            return

        commands = data.get("commands", []) or []

        for command in commands:
            if not command.get("enabled", False):
                continue

            command_id = str(command.get("id", f"command_{len(self.applied_runtime_commands)}"))

            if command_id in self.applied_runtime_commands:
                continue

            if "at_episode" in command and int(command["at_episode"]) != episode:
                continue

            if "at_step" in command and int(command["at_step"]) != step:
                continue

            operation = command.get("operation")

            event = {
                "episode": episode,
                "step": step,
                "command_id": command_id,
                "operation": operation,
                "status": "pending",
                "command": command,
            }

            try:
                if operation == "change_goal":
                    self._change_goal(command)
                    event["status"] = "applied"

                else:
                    raise ValueError(f"Operação não suportada: {operation}")

            except Exception as exc:
                event["status"] = "failed"
                event["message"] = str(exc)

            self.logger.log_event(event)
            self.applied_runtime_commands.add(command_id)

            print(
                f"[RuntimeCommand] step={step} "
                f"id={command_id} "
                f"operation={operation} "
                f"status={event['status']}"
            )


    def _change_goal(self, command: Dict[str, Any]) -> None:
        """
        Aplica mudança de goal na task atual.
        """
        task = getattr(self.env, "task", None)

        if task is None:
            unwrapped = getattr(self.env, "unwrapped", None)
            task = getattr(unwrapped, "task", None)

        if task is None:
            raise AttributeError("Não foi possível acessar a task atual do ambiente.")

        if not hasattr(task, "set_goal_for_object"):
            raise AttributeError("A task atual não suporta set_goal_for_object().")

        task.set_goal_for_object(
            object_name=command["target_object"],
            position=command["position"],
            tolerance=command.get("tolerance"),
            visual_marker=bool(command.get("visual_marker", True)),
        )
